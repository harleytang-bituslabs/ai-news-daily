#!/usr/bin/env bash
# 容器入口：可選啟動回補一次（對齊 crontab.example 的 @reboot --window 24），然後常駐 supercronic
set -euo pipefail
mkdir -p /app/logs /app/reports /app/data

# docker compose run app <指令> 時直接執行該指令（手動跑一次日報用），不啟動排程器
if [[ $# -gt 0 ]]; then
    exec "$@"
fi

# 預設關閉：自動重新部署會頻繁重啟容器，若每次重啟都跑一次會重複耗 API 並刷頻道
if [[ "${RUN_ON_START:-0}" == "1" ]]; then
    echo "[entrypoint] RUN_ON_START=1，先回補 24 小時窗口"
    python -m ai_news --base-dir /app --window 24 || echo "[entrypoint] 回補失敗，不影響排程" >&2
fi

# 必須用絕對路徑：supercronic 當 PID 1 時會用 argv[0] re-exec 自己做僵屍進程收割
exec /usr/local/bin/supercronic /app/docker/crontab
