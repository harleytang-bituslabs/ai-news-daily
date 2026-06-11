#!/usr/bin/env bash
# cron 入口：啟動 venv 並執行日報產生器
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p logs
exec .venv/bin/python main.py "$@"
