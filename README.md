# 每日 AI 新聞日報（ai-news-daily）

每 12 小時自動彙整 AI 圈最新消息，用 Claude 產出**繁體中文摘要 + 原文連結**的 Markdown 日報。

## 運作方式

1. **抓取**（不爬 Twitter 本體，多源交叉覆蓋避免遺漏）：
   - 官方 blog RSS：OpenAI、Google DeepMind、Google AI、Hugging Face、NVIDIA
   - 媒體 AI 專區 RSS：TechCrunch、The Verge、VentureBeat、Ars Technica、MIT Tech Review、Simon Willison
   - Hacker News（Algolia API，AI 關鍵字 + 分數門檻）
   - Reddit（RSS 端點）：r/LocalLLaMA、r/MachineLearning、r/artificial
   - **GitHub Trending**（每日熱榜前 15 個 repo，非 AI 項目由 Claude 過濾）
   - **Hugging Face Daily Papers**（社群票選的每日熱門論文前 10 篇 → 日報「📄 今日論文」章節）
   - **AI Builders 推文**（Karpathy、sama、swyx 等 26 位 builder 的 X/Twitter，按讚數取前 20 →
     日報「🧑‍💻 Builders 動態」章節）
   - **Podcast**（Latent Space、No Priors 等 6 檔節目，含 transcript 摘錄，依內容歸入對應章節）
   - **Anthropic Engineering / Claude Blog**（官方 blog，補上 Anthropic 無公開 RSS 的缺口）

   後三類不自己抓：直接消費 [follow-builders](https://github.com/zarazhangrui/follow-builders)
   的 GitHub Actions 每天預生成的 feed JSON（公開 raw URL、零金鑰；X API 與 pod2txt 轉錄由上游代勞）。
   上游一天生成一次，以 feed 的 generatedAt 做整包門控，內容每天恰好隨一班日報出現（正常為早班）。
2. **存檔**：原始素材寫入 `data/raw/YYYY-MM-DD-{am,pm}.jsonl`（之後打標／embedding／建向量庫的資料底座）
3. **去重排序**：URL 去重，依「官方來源 > 媒體/GitHub/論文/推文 > 社群」取前 55 則
4. **摘要**：呼叫 Claude（`claude-opus-4-8`）產出分類好的繁體中文日報
5. **輸出**：`reports/YYYY-MM-DD-{am,pm}.md`，並更新 `reports/latest.md`；有設 Slack webhook 就順便推送

> Meta、Microsoft 官方沒有可用的公開 RSS，但其發布幾乎必上 HN 與 TechCrunch/The Verge，已被覆蓋；
> Anthropic 官方內容已由 follow-builders feed（Anthropic Engineering / Claude Blog）直接補上。
> 想加減來源，改 `sources.py` 即可。
> crontab 內含 `@reboot` 條目：機器（服務）拉起來那一刻會先跑一次、並用 24 小時窗回補停機缺口。

## EC2 部署

```bash
# 1. 把整個資料夾放到 EC2（git clone 或 scp）
scp -r ai-news-daily ec2-user@<your-ec2>:~/

# 2. 安裝（需要 Python 3.9+）
cd ~/ai-news-daily
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -e .
chmod +x run.sh

# 3. 設定金鑰
cp .env.example .env
vi .env   # 填入 SUMMARIZER_MODEL 對應供應商的 API key

# 4. 測試
./run.sh --dry-run   # 只測試抓取，不花 API 錢
./run.sh             # 完整跑一次，看 reports/latest.md

# 5. 排程（洛杉磯時間每天 06:00 / 18:00）
crontab -e   # 貼上 crontab.example 的內容，路徑改成實際位置
```

## Docker 部署（含 GitHub 自動重新部署）

不想管 venv 和 crontab 的話，用 Docker 一鍵拉起兩個常駐容器：

- **app**：內建 supercronic 排程，LA 時間每天 06:00 / 18:00 各跑一次日報
- **deployer**：每 60 秒輪詢 GitHub `origin/main`，有新提交就自動 `git pull --ff-only` 並重建 app 容器（push 到 GitHub ≈ 自動部署）

```bash
cd ~/ai-news-daily

# 1. 設定金鑰（.env 已建好佔位，填 API key 與 Slack webhook）
vi .env

# 2. 先建好產物目錄（避免 compose 以 root 建立導致權限問題）
mkdir -p reports data logs

# 3. 測試（不花 API 錢、不發 Slack）
docker compose run --rm app python -m ai_news --base-dir /app --dry-run

# 4. 正式拉起
docker compose up -d --build
docker compose ps                  # 兩個容器都應為 Up
docker compose logs -f app        # 排程與日報執行日誌
docker compose logs -f deployer   # 自動部署日誌
```

注意事項：

- deployer 用 `git pull --ff-only`：伺服器上若有未提交的本地改動且與遠端分叉，自動部署會跳過並在日誌報錯，不會清掉你的工作區。
- `docker-compose.yml` 裡 deployer 的掛載路徑寫死為 `/home/ubuntu/release/ai-news-daily`，換機器部署要同步改。
- app 的 `RUN_ON_START` 環境變數設為 `"1"` 時，容器每次啟動會先用 24 小時窗回補一次（對齊 crontab 的 `@reboot` 行為）。預設關閉——自動部署會頻繁重啟容器，開著會重複耗 API 並重複推送。
- 容器以 uid 1000（ubuntu）執行，`reports/`、`data/`、`logs/` 產物落在宿主機且所有權不變。

## 模型與成本

摘要模型在 `.env` 的 `SUMMARIZER_MODEL` 一行切換（`provider:model_id`），三家都已接好並驗證過。
每次執行約 25K input / 5K output tokens，各家頂規的成本：

| 模型 | 定價（in/out per MTok） | 每次 | 每月（一天兩次） |
|---|---|---|---|
| `google:gemini-3.1-pro-preview` | $2 / $18 | ~$0.14 | **~$8（最便宜）** |
| `anthropic:claude-opus-4-8` | $5 / $25 | ~$0.25 | ~$15 |
| `openai:gpt-5.5` | $5 / $30 | ~$0.28 | ~$17 |

更省的選項：`anthropic:claude-sonnet-4-6`（$3/$15）、`openai:gpt-5.2`（$1.75/$14）、
`google:gemini-3.5-flash`（$1.5/$9）。Codex 系列（最新為 `gpt-5.3-codex`）是 coding
特化模型，不建議用於日報摘要。

## 專案結構

```
src/ai_news/
├── cli.py              # 命令列入口（ai-news / python -m ai_news）
├── config.py           # Settings、ModelSpec（provider:model_id）
├── models.py           # NewsItem、去重與排序
├── pipeline.py         # 主流程：抓取 → 去重排序 → 存檔 → 摘要 → 輸出
├── storage.py          # JSONL 原始素材存檔 + Markdown 日報輸出
├── notify.py           # Slack 推送（要加 Telegram/Email 在這裡擴充）
├── sources/            # 新聞來源（實作 Source 協定即可新增）
│   ├── base.py         #   Source 協定 + 共用 HTTP / 文字工具
│   ├── rss.py          #   官方 blog 與媒體 feed 清單
│   ├── hackernews.py   #   HN Algolia API
│   ├── reddit.py       #   Reddit RSS
│   ├── github_trending.py
│   ├── hf_papers.py    #   HF Daily Papers
│   └── follow_builders.py  # Builders 推文 / Podcast / Anthropic&Claude blog（上游預生成 feed）
└── summarize/
    ├── prompt.py       # 日報的 system prompt（改格式/分類/語氣在這裡）
    └── providers.py    # anthropic / openai / google 介接
tests/                  # pytest 單元測試（CI 會跑 ruff + pytest）
```

## 常用操作

| 需求 | 做法 |
|---|---|
| 改抓取來源 | `src/ai_news/sources/rss.py`（feed 清單）或對應來源模組 |
| 新增來源 | 實作 `Source` 協定，註冊到 `sources/__init__.py` 的 `default_sources()` |
| 改時間窗 / 則數上限 | `./run.sh --window 24 --max-items 60` 或改 cron 指令 |
| 改日報格式 / 分類 | `src/ai_news/summarize/prompt.py` |
| 換摘要模型 | `.env` 的 `SUMMARIZER_MODEL` |
| 推送到 Slack（可多頻道） | `.env` 填 `SLACK_WEBHOOK_URLS`，多個 webhook 逗號分隔 |
| 查看歷史日報 | `reports/` 目錄，一天兩份（am/pm） |
| 查 cron 執行紀錄 | `logs/cron.log` |
| 跑測試 / lint | `.venv/bin/pytest`、`.venv/bin/ruff check src tests` |
