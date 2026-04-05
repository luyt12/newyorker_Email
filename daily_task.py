"""
New Yorker daily task entry point
Fetch today articles -> dedup (max 10) -> summarize+translate -> one email
"""
import os, glob, json
from datetime import datetime
import pytz

TZ = pytz.timezone("America/New_York")
today_str = datetime.now(TZ).strftime("%Y%m%d")

SENT_FILE = "sent_articles.json"


def load_sent():
    if os.path.exists(SENT_FILE):
        try:
            with open(SENT_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f).get("sent", []))
        except Exception:
            pass
    return set()


def save_sent(urls):
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        json.dump({"sent": list(urls)}, f, ensure_ascii=False, indent=2)


print("Step 1: fetching today articles...")
import newyorker_rss_reader
saved = newyorker_rss_reader.main()

if not saved:
    print("No new articles today, exit.")
    exit(0)

print("Fetched " + str(len(saved)) + " new articles")

sent_urls = load_sent()
for _, url in saved:
    sent_urls.add(url)

today_files = sorted(glob.glob(os.path.join("articles", today_str + "_art*.md")))
if not today_files:
    print("No today article files found")
    exit(1)

print("Summarizing+translating " + str(len(today_files)) + " articles...")

import kimi_summarizer
translated_contents = []

for filepath in today_files:
    print("  Translating: " + os.path.basename(filepath))
    ok = kimi_summarizer.translate_file(filepath)
    if not ok:
        print("    Translation failed, skip.")
        continue

    basename = os.path.basename(filepath)
    translated_file = os.path.join("translate", basename)

    if os.path.exists(translated_file):
        with open(translated_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content:
            translated_contents.append(content)
        try:
            os.remove(translated_file)
        except Exception:
            pass

if not translated_contents:
    print("No translated content, exit.")
    exit(1)

combined = "\n\n---\n\n".join(translated_contents)
combined_file = os.path.join("translate", today_str + "_combined.md")
with open(combined_file, "w", encoding="utf-8") as f:
    f.write(combined)
print("Combined " + str(len(translated_contents)) + " articles, " + str(len(combined)) + " chars")

print("Sending email...")
import send_email
ok = send_email.main(combined_file)

if ok:
    print("Email sent successfully!")
else:
    print("Email FAILED - check error above")

try:
    os.remove(combined_file)
except Exception:
    pass

save_sent(sent_urls)
print("Done: " + str(len(translated_contents)) + " articles processed")
