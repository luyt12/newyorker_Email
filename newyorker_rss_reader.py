#!/usr/bin/env python3
"""
New Yorker full-content fetcher + RSS reader hybrid.
Strategy:
  1. Try to get full article text via direct fetch
  2. Fall back to RSS summary (always available)
  3. Label each article so we know if full text was obtained
"""
import os, re, time
import requests
import feedparser
import pytz
import json as _json
from datetime import datetime, timedelta

RSS_URL = "https://www.newyorker.com/feed/fiction"
FALLBACK_RSS = "https://feedx.net/rss/newyorker.xml"
ARTICLES_DIR = "articles"
SENT_FILE = "sent_articles.json"
MAX_DAILY = 5
TZ = pytz.timezone("America/New_York")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; bot/1.0)"}


def fetch_direct_text(url):
    """Direct fetch + HTML tag stripping."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return None
        html = resp.text
        html = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html)
        html = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", html)
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"&[a-z#][^;]*;", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:4000] if len(text) > 100 else None
    except Exception:
        return None


def get_article_content(url, rss_summary):
    """Get best available content. Returns (content, source_tag, is_full)."""
    # Try direct fetch
    full_text = fetch_direct_text(url)
    if full_text and len(full_text) > 500:
        # Trim to article-relevant section (first 3500 chars usually covers intro)
        return full_text[:3500], "📄 *(网页正文)*", True

    # Fallback to RSS summary
    return rss_summary if rss_summary else "[内容获取失败]", "📋 *(RSS摘要)*", False


def fetch_rss_entries():
    """Fetch and parse RSS, return entries with summaries."""
    for rss in [FALLBACK_RSS, RSS_URL]:
        try:
            resp = requests.get(rss, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.text)
            entries = []
            for e in feed.entries:
                title = e.get("title", "No title")
                link = e.get("link", "#").strip()
                pub = e.get("published_parsed") or e.get("updated_parsed")
                pub_str = "unknown"
                pub_dt = None
                if pub:
                    try:
                        dt = datetime(*pub[:6], tzinfo=TZ)
                        pub_str = dt.strftime("%Y-%m-%d")
                        pub_dt = dt
                    except Exception:
                        pass
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
                    "pub_dt": pub_dt,
                })
            if entries:
                return entries
        except Exception as ex:
            print(f"RSS fetch error ({rss}): {ex}")
            continue
    return []


def load_sent():
    if os.path.exists(SENT_FILE):
        try:
            with open(SENT_FILE, "r", encoding="utf-8") as f:
                return set(_json.load(f).get("sent", []))
        except Exception:
            pass
    return set()


def filter_by_date(entries, days_back):
    now = datetime.now(TZ)
    target = (now - timedelta(days=days_back)).strftime("%Y-%m-%d") if days_back > 0 else now.strftime("%Y-%m-%d")
    matched = [e for e in entries if e["published"] == target]
    label = "today" if days_back == 0 else f"{days_back} day(s) back"
    print(f"Total RSS entries: {len(entries)} | {label}: {len(matched)}")
    return matched


def format_single(article):
    lines = []
    lines.append("## " + article["title"])
    lines.append("")
    lines.append(f"📅 *Published: {article['published']}*")
    lines.append(f"[🔗 Read on New Yorker]({article['link']})")
    if article.get("_source_tag"):
        lines.append(article["_source_tag"])
    lines.append("")
    lines.append(article.get("_content", article.get("summary", "")))
    return "\n".join(lines)


def main(days_back=0, latest=False):
    if not os.path.exists(ARTICLES_DIR):
        os.makedirs(ARTICLES_DIR)

    sent_urls = load_sent()
    print("Already sent: " + str(len(sent_urls)) + " articles in sent_articles.json")

    entries = fetch_rss_entries()
    print(f"Fetched {len(entries)} RSS entries")

    if latest:
        print(f"LATEST mode: taking latest {MAX_DAILY} articles from RSS")
        remaining = [e for e in entries if e["link"] not in sent_urls]
        top = remaining[:MAX_DAILY]
    else:
        matched = filter_by_date(entries, days_back)
        if not matched and days_back == 0:
            matched = filter_by_date(entries, days_back=1)
            if matched:
                print("No today articles — using yesterday's")
        if not matched:
            print("No articles found for target date.")
            return None

        candidates = [e for e in matched if e["link"] not in sent_urls]
        print(f"After dedup: {len(candidates)} candidates")
        if not candidates:
            print("All target-date articles already sent.")
            return None
        candidates.sort(key=lambda x: x["pub_dt"] or "", reverse=True)
        top = candidates[:MAX_DAILY]

    print(f"Selected {len(top)} articles")

    today_str = datetime.now(TZ).strftime("%Y%m%d")
    suffix = "_latest" if latest else (f"_d{days_back}" if days_back > 0 else "")
    saved = []

    for i, article in enumerate(top):
        title_short = article["title"][:50]
        print(f"  Fetching content: {title_short}")
        content, source_tag, is_full = get_article_content(article["link"], article.get("summary", ""))
        article["_content"] = content
        article["_source_tag"] = source_tag
        print(f"    → {source_tag} ({len(content)} chars)")

        filename = today_str + suffix + "_art" + str(i + 1) + ".md"
        filepath = os.path.join(ARTICLES_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(format_single(article))
        print(f"  Saved: {filepath}")
        saved.append((filepath, article["link"]))

    print(f"Done: {len(saved)} articles saved")
    return saved


if __name__ == "__main__":
    import sys
    days_back = 0
    latest = False
    if len(sys.argv) > 1:
        if sys.argv[1] == "latest":
            latest = True
        else:
            try:
                days_back = int(sys.argv[1])
            except ValueError:
                print("Usage: python newyorker_rss_reader.py [days_back|latest]")
                sys.exit(1)
    main(days_back=days_back, latest=latest)
