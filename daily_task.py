"""
New Yorker Daily Task Entry
Fetch -> Translate -> Send Email
"""
import os
import glob
import pytz
from datetime import datetime

TZ = pytz.timezone("America/New_York")
today = datetime.now(TZ).strftime("%Y%m%d")

# Step 1: Fetch articles
print("Step 1: Fetch articles...")
import newyorker_rss_reader
newyorker_rss_reader.main()

# Step 2: Translate today's articles
print("Step 2: Translate today's articles...")
import kimi_summarizer
today_file = os.path.join("articles", today + ".md")

if not os.path.exists(today_file):
    print("Today's articles not found, trying latest: " + today_file)
    files = sorted(glob.glob("articles/*.md"))
    if files:
        today_file = files[-1]
        print("Using: " + today_file)
    else:
        print("No article files found")
        today_file = None

if today_file:
    success = kimi_summarizer.translate_file(today_file)
    if success:
        print("Translation successful")
    else:
        print("Translation failed")

# Step 3: Send email
print("Step 3: Send email...")
translate_path = os.path.join("translate", today + ".md")

if not os.path.exists(translate_path):
    t_files = sorted(glob.glob("translate/*.md"))
    if t_files:
        translate_path = t_files[-1]
        print("Using latest translation: " + translate_path)

if os.path.exists(translate_path):
    import send_email
    send_email.main(translate_path)
else:
    print("No translation file, skip email")

print("Daily task completed")
