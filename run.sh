#!/usr/bin/env bash
# cron 入口：以專案目錄為工作目錄執行日報產生器
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p logs
exec .venv/bin/python -m ai_news --base-dir "$PWD" "$@"
