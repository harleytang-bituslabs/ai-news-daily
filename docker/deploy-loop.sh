#!/bin/sh
# 自動重新部署：輪詢 origin/<BRANCH>，有新提交就 ff-only 拉取並重建 app 容器。
# 用 --ff-only 而非 reset --hard：本地有未提交改動或分叉時只跳過並報錯，不會清掉你的工作區。
set -u
REPO_DIR="${REPO_DIR:?REPO_DIR must be set}"
BRANCH="${BRANCH:-main}"
POLL_INTERVAL="${POLL_INTERVAL:-60}"

cd "$REPO_DIR"
echo "[deployer] watching origin/${BRANCH} every ${POLL_INTERVAL}s in ${REPO_DIR}"

while true; do
    if git fetch origin "$BRANCH" --quiet; then
        LOCAL=$(git rev-parse HEAD)
        REMOTE=$(git rev-parse "origin/${BRANCH}")
        if [ "$LOCAL" != "$REMOTE" ]; then
            echo "[deployer] $(date -u +%FT%TZ) update detected: ${LOCAL} -> ${REMOTE}"
            if git pull --ff-only origin "$BRANCH" \
               && docker compose -f "${REPO_DIR}/docker-compose.yml" up -d --build app; then
                echo "[deployer] $(date -u +%FT%TZ) redeploy OK"
            else
                echo "[deployer] $(date -u +%FT%TZ) redeploy FAILED（本地分叉/有未提交改動或 build 失敗），下輪重試" >&2
            fi
        fi
    else
        echo "[deployer] $(date -u +%FT%TZ) git fetch failed，下輪重試" >&2
    fi
    sleep "$POLL_INTERVAL"
done
