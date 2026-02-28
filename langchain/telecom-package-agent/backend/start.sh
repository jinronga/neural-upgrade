#!/bin/bash
# 后端进程管理脚本
# 用法:
#   ./start.sh start|stop|restart|status
#   ./start.sh                # 默认等同 start
#
# 使用前请确保:
# 1) 已创建数据库并授权
# 2) 已执行 alembic upgrade head

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UVICORN_BIN="${SCRIPT_DIR}/.venv/bin/uvicorn"
APP_MODULE="app.main:app"
HOST="0.0.0.0"
PORT="8005"
PID_FILE="${SCRIPT_DIR}/.backend.pid"
LOG_FILE="${SCRIPT_DIR}/backend.log"

is_running() {
  if [[ ! -f "${PID_FILE}" ]]; then
    return 1
  fi

  local pid
  pid="$(cat "${PID_FILE}" 2>/dev/null)"
  if [[ -z "${pid}" ]]; then
    return 1
  fi

  kill -0 "${pid}" 2>/dev/null
}

start_server() {
  if is_running; then
    echo "后端已在运行 (PID: $(cat "${PID_FILE}"))"
    return 0
  fi

  if [[ -f "${PID_FILE}" ]]; then
    echo "检测到无效 PID 文件，已清理: ${PID_FILE}"
    rm -f "${PID_FILE}"
  fi

  if [[ ! -x "${UVICORN_BIN}" ]]; then
    echo "未找到可执行文件: ${UVICORN_BIN}"
    echo "请先在 backend 目录创建虚拟环境并安装依赖。"
    return 1
  fi

  cd "${SCRIPT_DIR}" || return 1
  export PYTHONPATH=.

  # 后台启动，日志写入 backend.log
  nohup "${UVICORN_BIN}" "${APP_MODULE}" --host "${HOST}" --port "${PORT}" >"${LOG_FILE}" 2>&1 &
  local pid=$!
  echo "${pid}" >"${PID_FILE}"

  sleep 1
  if kill -0 "${pid}" 2>/dev/null; then
    echo "后端启动成功 (PID: ${pid})"
    echo "日志文件: ${LOG_FILE}"
    return 0
  fi

  echo "后端启动失败，请查看日志: ${LOG_FILE}"
  rm -f "${PID_FILE}"
  return 1
}

stop_server() {
  if ! is_running; then
    echo "后端未运行"
    [[ -f "${PID_FILE}" ]] && rm -f "${PID_FILE}"
    return 0
  fi

  local pid
  pid="$(cat "${PID_FILE}")"
  echo "正在停止后端进程 (PID: ${pid})..."
  kill "${pid}" 2>/dev/null || true

  for _ in {1..10}; do
    if ! kill -0 "${pid}" 2>/dev/null; then
      rm -f "${PID_FILE}"
      echo "后端已停止"
      return 0
    fi
    sleep 1
  done

  echo "进程未在预期时间内退出，执行强制停止 (PID: ${pid})"
  kill -9 "${pid}" 2>/dev/null || true
  rm -f "${PID_FILE}"
  echo "后端已强制停止"
}

status_server() {
  if is_running; then
    echo "后端运行中 (PID: $(cat "${PID_FILE}"))"
  else
    echo "后端未运行"
  fi
}

restart_server() {
  stop_server
  start_server
}

ACTION="${1:-start}"

case "${ACTION}" in
start)
  start_server
  ;;
stop)
  stop_server
  ;;
restart)
  restart_server
  ;;
status)
  status_server
  ;;
*)
  echo "未知参数: ${ACTION}"
  echo "用法: ./start.sh {start|stop|restart|status}"
  exit 1
  ;;
esac
