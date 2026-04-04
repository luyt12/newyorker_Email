"""
New Yorker RSS fetcher
Fetch articles from feedx.net/rss/newyorker.xml
"""
import os
import re
import requests
import feedparser
import pytz
from datetime import datetime

RSS_URL = "https://feedx.net/rss/newyorker.xml"
ARTICLES_DIR = "articles"
TZ = pytz.timezone("America/New_York")


def setup():
    if not os.path.exists(ARTICLES_DIR):
        os.makedirs(ARTICLES_DIR)


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
        link = e.get("link", "#")
        pub = e.get("published_parsed") or e.get("updated_parsed")
        if pub:
            try:
                dt = datetime(*pub[:6])
                pub_str = dt.strftime("%Y-%m-%d")
            except Exception:
                pub_str = "unknown"
        else:
            pub_str = "unknown"
        # 鑾峰彇瀹屾暣鎽樿鍐呭锛屼笉鎴柇
        summary = ""
        if hasattr(e, "summary"):
            summary = re.sub(r"<[^>]+>", "", e.summary)
        elif hasattr(e, "description"):
            summary = re.sub(r"<[^>]+>", "", e.description)
        entries.append({
            "title": title.strip(),
            "link": link.strip(),
            "published": pub_str,
            "summary": summary.strip(),
            "today": pub_str == today
        })
    today_list = [x for x in entries if x["today"]]
    print("Total: " + str(len(entries)) + ", Today: " + str(len(today_list)))
    return entries, today_list


def format_single_article(e):
    """鏍煎紡鍖栧崟绡囨枃绔?""
    lines = []
    lines.append("# " + e["title"])
    lines.append("*Published: " + e["published"] + "*")
    lines.append("[Original Link](" + e["link"] + ")")
    lines.append("")
    if e["summary"]:
        lines.append(e["summary"])
    return "\n".join(lines)


def format_entries(entries):
    """鏍煎紡鍖栧绡囨枃绔狅紙鐢ㄤ簬鑱氬悎鏂囦欢锛?""
    today_str = datetime.now(TZ).strftime("%Y-%m-%d")
    lines = ["# The New Yorker Daily - " + today_str, "", "Source: " + RSS_URL, "", "---", ""]
    for i, e in enumerate(entries, 1):
        lines.append("## " + str(i) + ". " + e["title"])
        lines.append("*Published: " + e["published"] + "*")
        lines.append("[Original Link](" + e["link"] + ")")
        if e["summary"]:
            lines.append("")
            lines.append(e["summary"])
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def main():
    setup()
    xml = fetch()
    all_entries, today_entries = parse(xml)

    today_str = datetime.now(TZ).strftime("%Y%m%d")
    date_str = datetime.now(TZ).strftime("%Y-%m-%d")

    # 淇濆瓨鎵€鏈夋枃绔?    all_file = os.path.join(ARTICLES_DIR, "all_" + today_str + ".md")
    with open(all_file, "w", encoding="utf-8") as f:
        f.write("# The New Yorker Daily - " + date_str + "\n\nSource: " + RSS_URL + "\n\n---\n\n")
        f.write(format_entries(all_entries))
    print("Saved all: " + all_file)

    if today_entries:
        # 淇濆瓨浠婃棩鏂囩珷鑱氬悎鏂囦欢
        today_file = os.path.join(ARTICLES_DIR, today_str + ".md")
        with open(today_file, "w", encoding="utf-8") as f:
            f.write(format_entries(today_entries))
        print("Saved today: " + today_file)

        # 鍚屾椂灏嗘瘡绡囦粖鏃ユ枃绔犲崟鐙繚瀛橈紝鏂逛究鐙珛澶勭悊
        for i, e in enumerate(today_entries):
            single_file = os.path.join(ARTICLES_DIR, today_str + "_art" + str(i + 1) + ".md")
            with open(single_file, "w", encoding="utf-8") as f:
                f.write(format_single_article(e))
            print("Saved article: " + single_file)

        return today_file
    else:
        print("No today articles")
        if all_entries:
            fallback = os.path.join(ARTICLES_DIR, "latest.md")
            with open(fallback, "w", encoding="utf-8") as f:
                f.write(format_entries(all_entries[:5]))
            print("Saved latest 5: " + fallback)
            return fallback
    return None


if __name__ == "__main__":
    main()
