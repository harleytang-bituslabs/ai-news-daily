# -*- coding: utf-8 -*-
"""新聞來源設定。要增減來源直接改這個檔案即可。"""

# RSS / Atom feeds — 這些媒體或官方 blog 本身就是 AI 專區，不需再做關鍵字過濾
# weight 越高，在篩選 top N 時越優先保留（官方發布 > 一線媒體 > 其他）
RSS_FEEDS = [
    # 官方 / 一手消息
    {"name": "OpenAI",            "url": "https://openai.com/news/rss.xml",                                  "weight": 3},
    {"name": "Google DeepMind",   "url": "https://deepmind.google/blog/rss.xml",                             "weight": 3},
    {"name": "Google AI Blog",    "url": "https://blog.google/technology/ai/rss/",                           "weight": 3},
    {"name": "Hugging Face",      "url": "https://huggingface.co/blog/feed.xml",                             "weight": 3},
    {"name": "NVIDIA",            "url": "https://blogs.nvidia.com/blog/category/generative-ai/feed/",       "weight": 2},
    # 註：Meta AI 與 Microsoft 的官方 RSS 已關閉（404/403），其消息由下方媒體與 HN 覆蓋
    # 科技媒體 AI 專區（Anthropic 等沒有公開 RSS 的官方消息，靠這些媒體 + HN 覆蓋）
    {"name": "TechCrunch AI",     "url": "https://techcrunch.com/category/artificial-intelligence/feed/",    "weight": 2},
    {"name": "The Verge AI",      "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml","weight": 2},
    {"name": "VentureBeat AI",    "url": "https://venturebeat.com/category/ai/feed/",                        "weight": 2},
    {"name": "Ars Technica AI",   "url": "https://arstechnica.com/ai/feed/",                                 "weight": 2},
    {"name": "MIT Tech Review AI","url": "https://www.technologyreview.com/topic/artificial-intelligence/feed", "weight": 2},
    # 高品質個人 blog
    {"name": "Simon Willison",    "url": "https://simonwillison.net/atom/everything/",                       "weight": 2},
]

# Hacker News（Algolia API）— 用這些關鍵字撈時間窗內的高分 story
HN_QUERIES = ["AI", "LLM", "OpenAI", "Anthropic", "Claude", "Gemini", "DeepSeek", "open model"]
HN_MIN_POINTS = 30

# Reddit — JSON API 會擋雲端 IP（403），改用 RSS 端點抓各版「過去一天 top」前 N 則
# （RSS 不含分數，靠 top 排序本身當品質門檻）
REDDIT_SUBS = [
    {"sub": "LocalLLaMA",      "limit": 8},
    {"sub": "MachineLearning", "limit": 5},
    {"sub": "artificial",      "limit": 5},
]
