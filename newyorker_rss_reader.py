"""
New Yorker RSS fetcher
Fetch articles from feedx.net/rss/newyorker.xml
娴佺▼锛氬姞杞藉凡鍙戣褰?鈫?鍙栧綋澶╁€欓€?鈫?鎴彇鍓峃绡?鈫?鎶撳彇鍐呭 鈫?淇濆瓨鐙珛鏂囦欢
"""
import os
import re
import requests
import feedparser
import pytz
from datetime import datetime

RSS_URL = "https://feedx.net/rss/newyorker.xml"
ARTICLES_DIR = "articles"
SENT_FILE = "sent_articles.json"
MAX_DAILY = 10
TZ = pytz.timezone("America/New_York")


def setup():
    if not os.path.exists(ARTICLES_DIR):
        os.makedirs(ARTICLES_DIR)


def load_sent():
    if os.path.exists(SENT_FILE):
        try:
            import json
            with open(SENT_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f).get("sent", []))
        except Exception:
            pass
    return set()


def fetch():
    print("Fetching RSS: " + RSS_URL)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0)"}
    resp = requests.get(RSS_URL, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse(xml):
    feed = feedparser.parse(xml)
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    entries = []
    for e in feed.entries:
        title = e.get("title", "No title")
        link = e.get("link", "#").strip()
        pub = e.get("published_parsed") or e.get("updated_parsed")
        if pub:
            try:
                dt = datetime(*pub[:6])
                pub_str = dt.strftime("%Y-%m-%d")
            except Exception:
                pub_str = "unknown"
        else:
            pub_str = "unknown"
        summary = ""
        if hasattr(e, "summary"):
            summary = re.sub(r"<[^>]+>", "", e.summary)
        elif hasattr(e, "description"):
            summary = re.sub(r"<[^>]+>", "", e.description)
        entries.append({
            "title": title.strip(),
            "link": link,
            "published": pub_str,
            "summary": summary.strip(),
            "today": pub_str == today
        })
    today_list = [x for x in entries if x["today"]]
    print("Total: " + str(len(entries)) + ", Today: " + str(len(today_list)))
    return today_list


def format_single(article):
    lines = []
    lines.append("# " + article["title"])
    lines.append("*Published: " + article["published"] + "*")
    lines.append("[Original Link](" + article["link"] + ")")
    lines.append("")
    if article.get("full_content"):
        lines.append(article["full_content"])
    elif article.get("summary"):
        lines.append(article["summary"])
    return "\n".join(lines)


def fetch_full_content(url):
    """Fetch full article content (optional, for richer summary)"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return None
        # 绠€鍗曟彁鍙栵細鍘绘帀 HTML 鏍囩
        text = re.sub(r"<script[\s\S]*?</script>", "", resp.text)
        text = re.sub(r"<style[\s\S]*?</style>", "", text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:3000] if len(text) > 3000 else text
    except Exception:
        return None


def main():
    setup()

    sent_urls = load_sent()
    print("Already sent: " + str(len(sent_urls)) + " articles")

    xml = fetch()
    today_entries = parse(xml)

    if not today_entries:
        print("No today articles")
        return None

    # Step 1: Deduplicate against sent URLs
    candidates = [e for e in today_entries if e["link"] not in sent_urls]
    print("After dedup: " + str(len(candidates)) + " candidates")

    if not candidates:
        print("All today articles already sent")
        return None

    # Step 2: Limit article count (newest first)
    print("Limited to " + str(len(top)) + " articles")
    top = candidates[:MAX_DAILY]

    # Step 3: Fetch content (optional full content for each)
    for i, article in enumerate(top):
        full = fetch_full_content(article["link"])
        if full:
            article["full_content"] = full
        else:
            article["full_content"] = article["summary"]

    # Step 4: 淇濆瓨姣忕瘒涓虹嫭绔嬫枃浠?    today_str = datetime.now(TZ).strftime("%Y%m%d")
    saved = []
    for i, article in enumerate(top):
        filename = today_str + "_art" + str(i + 1) + ".md"
        filepath = os.path.join(ARTICLES_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(format_single(article))
        print("Saved: " + filepath)
        saved.append((filepath, article["link"]))

    # 淇濆瓨鑱氬悎鏂囦欢锛堟柟渚胯皟璇曪級
    agg_path = os.path.join(ARTICLES_DIR, today_str + ".md")
    with open(agg_path, "w", encoding="utf-8") as f:
        f.write(f"# The New Yorker Daily - {today_str} ({len(top)} articles)\n\n---\n\n")
        for article in top:
            f.write(format_single(article))
            f.write("\n\n---\n\n")

    print("Done: " + str(len(saved)) + " articles saved")
    return saved


if __name__ == "__main__":
    main()
