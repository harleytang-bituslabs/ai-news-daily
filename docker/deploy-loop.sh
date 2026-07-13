#!/bin/sh
# 自動重新部署：輪詢 origin/<BRANCH>，有新提交就 ff-only 拉取並重建 app 容器。
# 用 --ff-only 而非 reset --hard：本地有未提交改動或分叉時只跳過並報錯，不會清掉你的工作區。
set -u
REPO_DIR="${REPO_DIR:?REPO_DIR must be set}"
BRANCH="${BRANCH:-main}"
POLL_INTERVAL="${POLL_INTERVAL:-60}"

cd "$REPO_DIR"
echo "[deployer] watching origin/${BRANCH} every ${POLL_INTERVAL}s in ${REPO_DIR}"

STATE="synced"
while true; do
    if git fetch origin "$BRANCH" --quiet; then
        LOCAL=$(git rev-parse HEAD)
        REMOTE=$(git rev-parse "origin/${BRANCH}")
        if [ "$LOCAL" = "$REMOTE" ]; then
            STATE="synced"
        elif git merge-base --is-ancestor "$LOCAL" "$REMOTE"; then
            # 遠端嚴格領先（本地可快進）才算有更新。不能只比不相等：
            # 本地領先時 pull 會成功空轉，接著空 rebuild 也會因 BuildKit
            # attestation 產生新鏡像摘要而重啟 app，把跑到一半的日報殺掉。
            echo "[deployer] $(date -u +%FT%TZ) update detected: ${LOCAL} -> ${REMOTE}"
            if git pull --ff-only origin "$BRANCH" \
               && docker compose -f "${REPO_DIR}/docker-compose.yml" up -d --build app; then
                echo "[deployer] $(date -u +%FT%TZ) redeploy OK"
            else
                echo "[deployer] $(date -u +%FT%TZ) redeploy FAILED，下輪重試" >&2
            fi
            STATE="synced"
        else
            # 本地領先（未推送的提交）或與遠端分叉：無法自動部署，告警一次後安靜等待
            if [ "$STATE" != "out-of-sync" ]; then
                echo "[deployer] $(date -u +%FT%TZ) 本地 ${LOCAL} 領先或分叉於 origin/${BRANCH}（${REMOTE}），暫停自動部署（push 或同步後自動恢復）" >&2
            fi
            STATE="out-of-sync"
        fi
    else
        echo "[deployer] $(date -u +%FT%TZ) git fetch failed，下輪重試" >&2
    fi
    sleep "$POLL_INTERVAL"
done
