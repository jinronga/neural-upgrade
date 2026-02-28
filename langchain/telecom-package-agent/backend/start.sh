#!/bin/bash
# 启动后端服务
# 使用前请确保：1) 已创建数据库并授权  2) 已执行 alembic upgrade head

cd "$(dirname "$0")"
export PYTHONPATH=.
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
