"""
New Yorker daily task entry point

Normal mode (GitHub Actions cron):
  python daily_task.py
  → Fetch today articles (fallback yesterday)
  → Deduplicate against sent_articles.json
  → Translate up to MAX_DAILY articles
  → Combine and send one email
  → Update sent_articles.json

Backfill mode (workflow_dispatch):
  python daily_task.py backfill N
  → Fetch articles from N days ago
  → Does NOT update sent_articles.json (can be re-sent later)

Latest mode (test):
  python daily_task.py latest
  → Fetch the latest MAX_DAILY articles from RSS regardless of date
  → Useful for testing when RSS has no new articles
"""
import os
import glob
import json
import sys
import pytz
from datetime import datetime

TZ = pytz.timezone("America/New_York")
today_str = datetime.now(TZ).strftime("%Y%m%d")
SENT_FILE = "sent_articles.json"
TRANSLATE_DIR = "translate"


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


def translate_and_collect(article_files):
    import kimi_summarizer
    translated = []
    for filepath in article_files:
        print("  Translating: " + os.path.basename(filepath))
        ok = kimi_summarizer.translate_file(filepath)
        if not ok:
            print("    Translation failed, skip.")
            continue
        basename = os.path.basename(filepath)
        tfile = os.path.join(TRANSLATE_DIR, basename)
        if os.path.exists(tfile):
            try:
                with open(tfile, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    translated.append(content)
                os.remove(tfile)
            except Exception as e:
                print("    Failed to read translated file: " + str(e))
    return translated


def send_email_and_save(translated_contents, sent_urls):
    if not translated_contents:
        print("No translated content to send.")
        return False

    combined = "\n\n---\n\n".join(translated_contents)
    combined_file = os.path.join(TRANSLATE_DIR, today_str + "_combined.md")
    with open(combined_file, "w", encoding="utf-8") as f:
        f.write(combined)
    print("Combined " + str(len(translated_contents)) + " articles, " +
          str(len(combined)) + " chars")

    print("Sending email...")
    import send_email
    ok = send_email.main(combined_file)

    if ok:
        print("Email sent successfully!")
        save_sent(sent_urls)
    else:
        print("Email FAILED — sent_articles.json NOT updated (will retry tomorrow)")

    try:
        os.remove(combined_file)
    except Exception:
        pass
    return ok


def main():
    mode = "normal"
    days_back = 0
    latest = False

    if len(sys.argv) > 1:
        if sys.argv[1] == "backfill":
            mode = "backfill"
            if len(sys.argv) > 2:
                try:
                    days_back = int(sys.argv[2])
                except ValueError:
                    print("Usage: python daily_task.py backfill [days_back]")
                    sys.exit(1)
            print(f"=== BACKFILL MODE: {days_back} days back ===")
        elif sys.argv[1] == "latest":
            mode = "latest"
            latest = True
            print("=== LATEST MODE: fetching latest articles from RSS ===")
        else:
            print("Usage: python daily_task.py [backfill N | latest]")
            sys.exit(1)

    import newyorker_rss_reader

    if mode == "normal":
        print("Step 1: fetching today's articles (fallback to yesterday)...")
        saved = newyorker_rss_reader.main(days_back=0)
        if not saved:
            print("No new articles, exit.")
            sys.exit(0)
    elif mode == "backfill":
        print(f"Step 1: backfilling from {days_back} day(s) ago...")
        saved = newyorker_rss_reader.main(days_back=days_back)
        if not saved:
            print("No articles for that date, exit.")
            sys.exit(0)
    else:  # latest
        print("Step 1: fetching latest articles from RSS...")
        saved = newyorker_rss_reader.main(latest=True)
        if not saved:
            print("No articles found, exit.")
            sys.exit(0)

    print("Fetched " + str(len(saved)) + " articles")

    # Build sent_urls set
    sent_urls = load_sent()
    for _, url in saved:
        sent_urls.add(url)

    # Find article files matching today's date prefix
    article_files = sorted(glob.glob(
        os.path.join("articles", today_str + "*_art*.md")))
    if not article_files:
        print("No article files found.")
        sys.exit(1)

    article_files = article_files[:newyorker_rss_reader.MAX_DAILY]
    print("Translating " + str(len(article_files)) + " articles...")
    translated = translate_and_collect(article_files)

    # Backfill mode: don't update sent_urls (allow re-send)
    if mode == "backfill":
        print("[backfill] sent_articles.json will NOT be updated")

    send_ok = send_email_and_save(
        translated,
        sent_urls if mode != "backfill" else set()
    )

    if send_ok:
        print("Done: " + str(len(translated)) + " articles processed")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
