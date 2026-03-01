#!/bin/bash
# 兼容入口：保留 start.sh，实际逻辑迁移到 ./start

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "${SCRIPT_DIR}/start" "$@"
