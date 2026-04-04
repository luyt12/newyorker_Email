"""
New Yorker 姣忔棩浠诲姟鍏ュ彛
鎶撳彇 -> 鍘婚噸杩囨护 -> 缈昏瘧姣忕瘒 -> 姣忕瘒鐙珛鍙戦偖浠?"""
import os
import glob
import json
import pytz
from datetime import datetime

tz_est = pytz.timezone("America/New_York")
today = datetime.now(tz_est).strftime("%Y%m%d")

SENT_FILE = "sent_articles.json"


def load_sent():
    """浠?sent_articles.json 鍔犺浇宸插彂閫佽褰?""
    if os.path.exists(SENT_FILE):
        try:
            with open(SENT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"sent": {}}


def save_sent(data):
    """淇濆瓨宸插彂閫佽褰曞埌 sent_articles.json"""
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_article_url(filepath):
    """浠庢枃绔犳枃浠朵腑鎻愬彇 URL"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        # 鎵?[Original Link](url) 琛?        import re
        m = re.search(r'\[Original Link\]\((https?://[^\)]+)\)', content)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


# Step 1: 鎶撳彇鏂囩珷
print("Step 1: 鎶撳彇鏂囩珷...")
import newyorker_rss_reader
newyorker_rss_reader.main()

# Step 2: 鍔犺浇宸插彂閫佽褰?print("Step 2: 鍘婚噸杩囨护...")
sent_data = load_sent()
sent_urls = sent_data.get("sent", {})
print("Already sent: " + str(len(sent_urls)) + " articles")

# Step 3: 鎵句粖鏃ユ枃绔狅紝杩囨护宸插彂閫佺殑
import kimi_summarizer
import send_email

today_articles = sorted(glob.glob(os.path.join("articles", today + "_art*.md")))
print("Found today's articles: " + str(len(today_articles))))

# 濡傛灉娌℃湁鐙珛鏂囦欢锛宖allback
if not today_articles:
    agg_file = os.path.join("articles", today + ".md")
    if os.path.exists(agg_file):
        today_articles = [agg_file]
    else:
        files = sorted(glob.glob("articles/*.md"))
        if files:
            today_articles = [files[-1]]

new_articles = []
for filepath in today_articles:
    url = get_article_url(filepath)
    if url and url in sent_urls:
        print("Already sent, skipping: " + url)
        continue
    new_articles.append((filepath, url))
    if url:
        sent_urls[url] = today  # 鏍囪涓轰粖澶╁彂閫?
print("New articles to send: " + str(len(new_articles)))

# Step 4: 缈昏瘧骞跺彂閫佹瘡绡囨柊鏂囩珷
success_count = 0
for filepath, url in new_articles:
    print("Processing: " + filepath)

    ok = kimi_summarizer.translate_file(filepath)
    if not ok:
        print("Translation failed: " + filepath)
        continue

    basename = os.path.basename(filepath)
    translated_file = os.path.join("translate", basename)

    if not os.path.exists(translated_file):
        print("Translated file not found: " + translated_file)
        continue

    try:
        send_email.main(translated_file)
        print("Email sent: " + translated_file)
        success_count += 1
    except Exception as e:
        print("Email error: " + str(e))

# Step 5: 淇濆瓨宸插彂閫佽褰?if new_articles:
    save_sent(sent_data)
    print("Saved sent_articles.json")

print("Successfully sent " + str(success_count) + "/" + str(len(new_articles)) + " emails")
print("Done!")
