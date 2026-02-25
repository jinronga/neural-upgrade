"""High-level functions that encapsulate business logic for the LangChain agent.

These functions are thin, agent-friendly wrappers around the service layer.
They are designed to:
- Accept simple primitives (str/int) from tools
- Return JSON-serializable dict/list structures
"""

from .package_functions import (
    compare_packages,
    get_available_packages,
    get_current_package,
    get_package_detail,
    recommend_package,
)

__all__ = [
    "get_current_package",
    "get_available_packages",
    "recommend_package",
    "get_package_detail",
    "compare_packages",
]

