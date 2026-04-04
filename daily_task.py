"""
New Yorker 姣忔棩浠诲姟鍏ュ彛
鎶撳彇褰撳ぉ鏂囩珷 鈫?鍘婚噸锛堟渶澶?0绡囷級鈫?鎻愮偧瑕佺偣+缈昏瘧 鈫?鍚堝苟涓轰竴灏侀偖浠跺彂閫?"""
import os
import glob
import json
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


# Step 1: 鎶撳彇褰撳ぉ鏂囩珷锛堝凡鍘婚噸锛屾渶澶?0绡囷級
print("Step 1: 鎶撳彇褰撳ぉ鏂囩珷...")
import newyorker_rss_reader
saved = newyorker_rss_reader.main()

if not saved:
    print("浠婃棩鏃犳柊鏂囩珷锛岄€€鍑?)
    exit(0)

print(f"鎶撳彇鍒?{len(saved)} 绡囨柊鏂囩珷")

# Step 2: 璁板綍浠婃棩 URL 鍒板凡鍙戦€佸垪琛?sent_urls = load_sent()
for _, url in saved:
    sent_urls.add(url)

# Step 3: 鎵惧埌浠婃棩鏂囩珷鏂囦欢
today_files = sorted(glob.glob(os.path.join("articles", today_str + "_art*.md")))
if not today_files:
    print("鏈壘鍒颁粖鏃ユ枃绔犳枃浠?)
    exit(1)

print(f"寮€濮嬫彁鐐?缈昏瘧 {len(today_files)} 绡囨枃绔?..")

# Step 4: 鎻愮偧+缈昏瘧
import kimi_summarizer
translated_contents = []

for filepath in today_files:
    print(f"  缈昏瘧: {os.path.basename(filepath)}")
    ok = kimi_summarizer.translate_file(filepath)
    if not ok:
        print(f"    缈昏瘧澶辫触锛岃烦杩?)
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
    print("鏃犵炕璇戝唴瀹癸紝閫€鍑?)
    exit(1)

# Step 5: 鍚堝苟鎵€鏈夋憳瑕佷负涓€灏侀偖浠?combined = "\n\n---\n\n".join(translated_contents)
combined_file = os.path.join("translate", today_str + "_combined.md")
with open(combined_file, "w", encoding="utf-8") as f:
    f.write(combined)
print(f"\n鍚堝苟鎽樿宸蹭繚瀛? {combined_file} ({len(combined)} 瀛?")

# Step 6: 鍙戦€佷竴灏侀偖浠?print("鍙戦€侀偖浠?..")
import send_email
try:
    send_email.main(combined_file)
    print(f"閭欢鍙戦€佹垚鍔燂紝鍏?{len(translated_contents)} 绡囨枃绔?)
except Exception as e:
    print(f"閭欢鍙戦€佸け璐? {e}")

try:
    os.remove(combined_file)
except Exception:
    pass

# Step 7: 淇濆瓨宸插彂閫佽褰?save_sent(sent_urls)
print(f"瀹屾垚锛歿len(translated_contents)} 绡囨憳瑕佸凡鍙戦€?)
