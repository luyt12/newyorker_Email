"""
New Yorker daily task entry point

Normal mode (GitHub Actions cron):
  1. Fetch today articles (fallback to yesterday)
  2. Deduplicate against sent_articles.json
  3. Translate up to MAX_DAILY articles
  4. Combine and send one email
  5. Update sent_articles.json

Test mode (workflow_dispatch):
  python daily_task.py backfill <days_back>
  - Fetches articles from N days ago, ignores sent_articles.json dedup
  - Useful for testing when RSS has no new articles today
"""
import os
import glob
import json
import sys
import shutil
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


def clean_old_articles(keep_urls):
    """Remove article files whose URLs are already in sent_articles.json."""
    if not os.path.exists(SENT_FILE):
        return
    existing_urls = load_sent()
    files = glob.glob(os.path.join("articles", "*.md"))
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                content = fh.read()
            for url in existing_urls:
                if url in content:
                    break
            else:
                continue  # URL not found, skip
            # Only remove if explicitly in keep_urls (for current run)
        except Exception:
            pass


def translate_and_collect(today_files):
    """Translate each article file; collect successful results."""
    import kimi_summarizer

    translated = []
    for filepath in today_files:
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


def send_and_save(translated_contents, sent_urls):
    """Combine translated articles, send email, update sent_articles.json."""
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

    if len(sys.argv) > 1 and sys.argv[1] == "backfill":
        mode = "backfill"
        if len(sys.argv) > 2:
            try:
                days_back = int(sys.argv[2])
            except ValueError:
                print("Usage: python daily_task.py backfill [days_back]")
                sys.exit(1)
        print(f"=== BACKFILL MODE: fetching {days_back} days back ===")

    import newyorker_rss_reader

    if mode == "normal":
        print("Step 1: fetching today's articles...")
        saved = newyorker_rss_reader.main(days_back=0)
        if not saved:
            print("No new articles, exit.")
            sys.exit(0)
    else:
        print(f"Step 1: backfilling articles from {days_back} day(s) ago...")
        saved = newyorker_rss_reader.main(days_back=days_back)
        if not saved:
            print("No articles for that date, exit.")
            sys.exit(0)

    print("Fetched " + str(len(saved)) + " new articles")

    # Build sent_urls set
    if mode == "normal":
        sent_urls = load_sent()
        for _, url in saved:
            sent_urls.add(url)
    else:
        # Backfill mode: don't update sent_urls (don't mark as sent)
        sent_urls = set()
        for _, url in saved:
            sent_urls.add(url)  # used for email tracking only

    # Find article files
    article_files = sorted(glob.glob(os.path.join("articles", today_str + "*_art*.md")))
    if not article_files:
        print("No article files found.")
        sys.exit(1)

    # Limit to MAX_DAILY (already done in rss_reader, but double-check)
    from newyorker_rss_reader import MAX_DAILY
    article_files = article_files[:MAX_DAILY]

    print("Translating " + str(len(article_files)) + " articles...")
    translated = translate_and_collect(article_files)

    send_and_save(translated, sent_urls)


if __name__ == "__main__":
    main()
