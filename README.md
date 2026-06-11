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
2. **存檔**：原始素材寫入 `data/raw/YYYY-MM-DD-{am,pm}.jsonl`（之後打標／embedding／建向量庫的資料底座）
3. **去重排序**：URL 去重，依「官方來源 > 媒體/GitHub/論文 > 社群」取前 40 則
4. **摘要**：呼叫 Claude（`claude-opus-4-8`）產出分類好的繁體中文日報
5. **輸出**：`reports/YYYY-MM-DD-{am,pm}.md`，並更新 `reports/latest.md`；有設 Slack webhook 就順便推送

> Anthropic、Meta、Microsoft 官方都沒有可用的公開 RSS，但其發布幾乎必上 HN 與 TechCrunch/The Verge，已被覆蓋。
> 想加減來源，改 `sources.py` 即可。
> crontab 內含 `@reboot` 條目：機器（服務）拉起來那一刻會先跑一次、並用 24 小時窗回補停機缺口。

## EC2 部署

```bash
# 1. 把整個資料夾放到 EC2（git clone 或 scp）
scp -r ai-news-daily ec2-user@<your-ec2>:~/

# 2. 安裝（需要 Python 3.9+）
cd ~/ai-news-daily
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
chmod +x run.sh

# 3. 設定金鑰
cp .env.example .env
vi .env   # 填入 ANTHROPIC_API_KEY

# 4. 測試
.venv/bin/python main.py --dry-run   # 只測試抓取，不花 API 錢
.venv/bin/python main.py             # 完整跑一次，看 reports/latest.md

# 5. 排程（洛杉磯時間每天 06:00 / 18:00）
crontab -e   # 貼上 crontab.example 的內容，路徑改成實際位置
```

## 成本估算

每次執行約 20-30K input tokens、3-6K output tokens，以 Opus 4.8（$5/$25 per MTok）計算
約 **$0.2-0.3／次，一天兩次 ≈ $12-18／月**。若想壓成本可把 `summarizer.py` 的 `MODEL`
改成 `claude-sonnet-4-6`（約 6 折）或 `claude-haiku-4-5`（約 2 折），摘要品質會略降。

## 常用操作

| 需求 | 做法 |
|---|---|
| 改抓取來源 | 編輯 `sources.py` |
| 改時間窗 / 則數上限 | `main.py --window 24 --max-items 60` 或改 cron 指令 |
| 改日報格式 / 分類 | 編輯 `summarizer.py` 的 `SYSTEM_PROMPT` |
| 推送到 Slack | `.env` 填 `SLACK_WEBHOOK_URL` |
| 查看歷史日報 | `reports/` 目錄，一天兩份（am/pm） |
| 查 cron 執行紀錄 | `logs/cron.log` |
