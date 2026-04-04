"""
New Yorker 姣忔棩浠诲姟鍏ュ彛
鎶撳彇 -> 缈昏瘧姣忕瘒鏂囩珷 -> 姣忕瘒鐙珛鍙戦偖浠?"""
import os
import glob
import pytz
from datetime import datetime

tz_est = pytz.timezone("America/New_York")
today = datetime.now(tz_est).strftime("%Y%m%d")
today_display = datetime.now(tz_est).strftime("%Y-%m-%d")

# Step 1: 鎶撳彇鏂囩珷
print("Step 1: 鎶撳彇鏂囩珷...")
import newyorker_rss_reader
newyorker_rss_reader.main()

# Step 2: 鎵惧埌浠婃棩鏂囩珷锛岀炕璇戞瘡绡囷紝鍒嗗埆鍙戦偖浠?print("Step 2: 缈昏瘧骞跺彂閫佹瘡绡囨枃绔?..")

import kimi_summarizer
import send_email

# 鏌ユ壘浠婃棩鏂囩珷鐙珛鏂囦欢
today_articles = sorted(glob.glob(os.path.join("articles", today + "_art*.md")))
print("Found " + str(len(today_articles)) + " today's articles")

# 濡傛灉娌℃湁鐙珛鏂囦欢锛堝巻鍙叉暟鎹級锛宖all back 鍒拌仛鍚堟枃浠?if not today_articles:
    agg_file = os.path.join("articles", today + ".md")
    if os.path.exists(agg_file):
        print("No individual article files, using aggregated: " + agg_file)
        today_articles = [agg_file]
    else:
        files = sorted(glob.glob("articles/*.md"))
        if files:
            today_articles = [files[-1]]
            print("Using latest: " + files[-1])

success_count = 0
for filepath in today_articles:
    print("Processing: " + filepath)

    # 缈昏瘧
    ok = kimi_summarizer.translate_file(filepath)
    if not ok:
        print("Translation failed: " + filepath)
        continue

    # 缈昏瘧缁撴灉璺緞
    basename = os.path.basename(filepath)
    translated_file = os.path.join("translate", basename)

    if not os.path.exists(translated_file):
        print("Translated file not found: " + translated_file)
        continue

    # 鍙戦€侀偖浠?    try:
        send_email.main(translated_file)
        print("Email sent: " + translated_file)
        success_count += 1
    except Exception as e:
        print("Email error: " + str(e))

print("Successfully sent " + str(success_count) + "/" + str(len(today_articles)) + " emails")
print("Done!")
