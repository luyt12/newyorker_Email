"""
New Yorker RSS Reader
抓取 feedx.net RSS 源，保存当日文章。
新特性：当日无文章时，自动回退到历史未处理文章。
"""
import os
import json
import feedparser
import pytz
from datetime import datetime

RSS_URL = "https://feedx.net/rss/newyorker.xml"
ARTICLES_DIR = "articles"
PROCESSED_FILE = "processed_urls.json"
MAX_DAILY = 10

TZ = pytz.timezone("America/New_York")


def load_processed():
    if os.path.exists(PROCESSED_FILE):
        try:
            with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f).get("processed", []))
        except Exception:
            pass
    return set()


def save_processed(urls):
    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        json.dump({"processed": list(urls)}, f, ensure_ascii=False, indent=2)


def fetch_rss():
    print("Fetching RSS: " + RSS_URL)
    feed = feedparser.parse(RSS_URL)
    print("Total: " + str(len(feed.entries)))
    return feed


def get_pub_date(entry):
    try:
        pub = entry.get("published_parsed") or entry.get("updated_parsed")
        if not pub:
            return None
        return datetime(*pub[:6], tzinfo=pytz.UTC)
    except Exception:
        return None


def is_today(entry):
    pub_dt = get_pub_date(entry)
    if not pub_dt:
        return False
    today = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    return pub_dt.date() == today.date()


def extract_content(entry):
    title = entry.get("title", "")
    link = entry.get("link", "")
    summary = entry.get("summary", "")
    content = entry.get("content", [{}])[0].get("value", summary)
    return title, link, content


def save_articles(feed):
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    processed = load_processed()
    today = datetime.now(TZ).strftime("%Y%m%d")
    today_file = os.path.join(ARTICLES_DIR, today + ".md")

    # 解析所有文章
    all_articles = []
    for entry in feed.entries:
        title, link, content = extract_content(entry)
        pub_dt = get_pub_date(entry)
        all_articles.append({
            "title": title,
            "link": link,
            "content": content,
            "pub_dt": pub_dt,
            "is_today": is_today(entry)
        })

    print(f"RSS 共 {len(all_articles)} 篇文章")

    # 优先今日文章，无则回退到历史未处理
    today_articles = [a for a in all_articles if a["is_today"] and a["link"] not in processed]
    print(f"今日新文章: {len(today_articles)} 篇")

    if today_articles:
        selected = today_articles[:MAX_DAILY]
        print(f"→ 使用今日文章: {len(selected)} 篇")
    else:
        # 回退到历史未处理文章
        historical = [a for a in all_articles if a["link"] not in processed]
        # 按发布时间倒序
        historical.sort(key=lambda x: x["pub_dt"] if x["pub_dt"] else datetime.min, reverse=True)
        print(f"→ 今日无文章，回退到历史未处理: {len(historical)} 篇")
        selected = historical[:MAX_DAILY]

    if not selected:
        print("无新文章")
        return 0

    # 保存今日文章
    article_mds = []
    new_links = []
    for article in selected:
        article_md = "## " + article["title"] + "\n\n"
        article_md += "链接：" + article["link"] + "\n\n"
        article_md += article["content"] + "\n\n---\n\n"
        article_mds.append(article_md)
        new_links.append(article["link"])

    with open(today_file, "w", encoding="utf-8") as f:
        f.write("# New Yorker Articles - " + today + "\n\n")
        f.write("".join(article_mds))
    print(f"Saved: {today_file} ({len(selected)} articles)")

    # 更新 processed
    processed.update(new_links)
    save_processed(processed)
    print(f"已标记 {len(new_links)} 篇为已处理")

    return len(selected)


def main():
    feed = fetch_rss()
    count = save_articles(feed)
    print("Processed: " + str(count))
    return count


if __name__ == "__main__":
    main()
