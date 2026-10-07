#!/usr/bin/env bash
# 力扣刷题看板 · macOS / Linux 启动脚本
# 用法：./start.sh   或   bash start.sh
cd "$(dirname "$0")" || exit 1

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "没有找到 Python，请先安装 Python 3.8+"
  exit 1
fi

exec "$PY" start.py