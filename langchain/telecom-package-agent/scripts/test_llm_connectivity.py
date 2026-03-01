#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from openai import APIConnectionError, APIStatusError, OpenAI

# Reuse backend configuration loading logic so this script uses the same
# OPENAI_BASE_URL / OPENAI_API_KEY as the application.
ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402


def mask_secret(value: str | None) -> str:
    if not value:
        return "<empty>"
    if len(value) <= 10:
        return "*" * len(value)
    return f"{value[:6]}...{value[-4:]}"


def print_api_error(error: Exception) -> None:
    print(f"ERROR: {type(error).__name__}: {error}")
    if isinstance(error, APIStatusError):
        print(f"HTTP status: {error.status_code}")
        request_id = getattr(error, "request_id", None)
        if request_id:
            print(f"Request ID: {request_id}")
        body = getattr(error, "body", None)
        if body is not None:
            print(f"Response body: {body}")
    elif isinstance(error, APIConnectionError):
        print("Connection failed. Check OPENAI_BASE_URL and network reachability.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test whether configured LLM base_url and API key are usable."
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="Model name used for chat completion test.",
    )
    parser.add_argument(
        "--prompt",
        default="Reply with exactly: pong",
        help="Prompt for chat completion test.",
    )
    parser.add_argument(
        "--skip-models",
        action="store_true",
        help="Skip models.list probe.",
    )
    parser.add_argument(
        "--skip-chat",
        action="store_true",
        help="Skip chat completion probe.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="Request timeout in seconds.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    base_url = settings.OPENAI_BASE_URL or "https://api.openai.com/v1"
    api_key = settings.OPENAI_API_KEY

    print("=== LLM Config ===")
    print(f"base_url: {base_url}")
    print(f"api_key : {mask_secret(api_key)}")
    print(f"model   : {args.model}")
    print()

    if not api_key:
        print("FAIL: OPENAI_API_KEY is empty.")
        return 2

    client_kwargs: dict[str, Any] = {
        "api_key": api_key,
        "timeout": args.timeout,
    }
    if settings.OPENAI_BASE_URL:
        client_kwargs["base_url"] = settings.OPENAI_BASE_URL
    client = OpenAI(**client_kwargs)

    models_ok = False
    chat_ok = False

    if not args.skip_models:
        print("=== Probe 1: models.list ===")
        try:
            models = client.models.list()
            model_ids = [m.id for m in getattr(models, "data", [])[:5]]
            print("PASS: models.list succeeded.")
            print(
                "sample models:",
                ", ".join(model_ids) if model_ids else "<no model ids returned>",
            )
            models_ok = True
        except Exception as error:  # noqa: BLE001
            print_api_error(error)
        print()

    if not args.skip_chat:
        print("=== Probe 2: chat.completions ===")
        try:
            response = client.chat.completions.create(
                model=args.model,
                messages=[{"role": "user", "content": args.prompt}],
                temperature=0,
                max_tokens=32,
            )
            content = response.choices[0].message.content if response.choices else ""
            print("PASS: chat.completions succeeded.")
            print(f"response: {content!r}")
            chat_ok = True
        except Exception as error:  # noqa: BLE001
            print_api_error(error)
        print()

    if args.skip_models and args.skip_chat:
        print("No probes executed. Remove --skip-* flags to run tests.")
        return 3

    if chat_ok or models_ok:
        print("RESULT: reachable (at least one probe succeeded).")
        return 0

    print("RESULT: failed (both probes failed).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
