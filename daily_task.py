"""
New Yorker 每日任务入口
抓取 -> 翻译 -> 发邮件
"""
import os
import pytz
from datetime import datetime

tz_est = pytz.timezone("America/New_York")
today = datetime.now(tz_est).strftime("%Y%m%d")
today_display = datetime.now(tz_est).strftime("%Y-%m-%d")

# Step 1: 抓取文章
print("Step 1: 抓取文章...")
import newyorker_rss_reader
newyorker_rss_reader.main()

# Step 2: 翻译今日文章
print("Step 2: 翻译今日文章...")
import kimi_summarizer
today_file = os.path.join("articles", today + ".md")

if not os.path.exists(today_file):
    print("今日文章不存在，尝试最新文章: " + today_file)
    import glob
    files = sorted(glob.glob("articles/*.md"))
    if files:
        today_file = files[-1]
        print("使用: " + today_file)
    else:
        print("没有找到文章文件")
        today_file = None

if today_file:
    success = kimi_summarizer.translate_file(today_file)
    if success:
        print("翻译成功")
    else:
        print("翻译失败")

# Step 3: 发送邮件
print("Step 3: 发送邮件...")
translate_path = os.path.join("translate", today + ".md")

if not os.path.exists(translate_path):
    import glob as _g
    t_files = sorted(_g.glob("translate/*.md"))
    if t_files:
        translate_path = t_files[-1]
        print("使用最新翻译: " + translate_path)

if os.path.exists(translate_path):
    import send_email
    send_email.main(translate_path)
else:
    print("没有翻译文件，跳过邮件")

print("每日任务完成")
