"""
New Yorker News Email Sender - beautified version
Merge multiple article summaries into one HTML email
"""
import os
import sys
import re
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

EMAIL_TO = os.getenv("EMAIL_TO") or ""
EMAIL_FROM = os.getenv("EMAIL_FROM") or ""
SMTP_HOST = os.getenv("SMTP_HOST") or ""
SMTP_PORT = int(os.getenv("SMTP_PORT") or "465")
SMTP_USER = os.getenv("SMTP_USER") or ""
SMTP_PASS = os.getenv("SMTP_PASS") or ""

_missing = [k for k, v in {
    "EMAIL_TO": EMAIL_TO, "EMAIL_FROM": EMAIL_FROM,
    "SMTP_HOST": SMTP_HOST, "SMTP_USER": SMTP_USER, "SMTP_PASS": SMTP_PASS
}.items() if not v]
if _missing:
    print("ERROR: Missing env vars: " + ", ".join(_missing))
    sys.exit(1)


def extract_date(filepath):
    m = re.search(r"(\d{8})", filepath)
    return m.group(1) if m else datetime.now().strftime("%Y%m%d")


def make_html(combined_content, date_str):
    import markdown

    date_fmt = datetime.strptime(date_str, "%Y%m%d").strftime("%Y年%m月%d日")

    # 分割每篇文章（以 ## 开头即为新文章）
    sections = re.split(r"\n(?=## )", combined_content.strip())

    articles_html = ""
    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue

        article_html = markdown.markdown(
            section,
            extensions=['fenced_code', 'tables'],
            output_format='html'
        )

        articles_html += f"""
        <div class="article{' odd' if i % 2 == 0 else ''}">
            {article_html}
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The New Yorker 日报 - {date_fmt}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #f0f2f5;
    font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;
    color: #1a1a1a;
    padding: 20px 0;
  }}
  .wrapper {{
    max-width: 680px;
    margin: 0 auto;
    background: #ffffff;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 24px rgba(0,0,0,0.08);
  }}
  /* 报头 */
  .header {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    color: #fff;
    padding: 32px 40px;
    position: relative;
  }}
  .header::after {{
    content: '';
    position: absolute;
    bottom: -20px;
    left: 0; right: 0;
    height: 20px;
    background: linear-gradient(to bottom right, #16213e 0%, #16213e 50%, transparent 50%);
  }}
  .header-inner {{
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}
  .header h1 {{
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 1px;
    color: #fff;
  }}
  .header .subtitle {{
    font-size: 14px;
    opacity: 0.75;
    margin-top: 4px;
    color: #c0c0c0;
  }}
  .header .date-badge {{
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.25);
    border-radius: 20px;
    padding: 6px 16px;
    font-size: 13px;
    text-align: center;
    color: #fff;
  }}
  .header .date-badge span {{
    display: block;
    font-size: 11px;
    opacity: 0.65;
    margin-bottom: 2px;
  }}
  /* 文章计数 */
  .meta-bar {{
    background: #fafafa;
    border-bottom: 1px solid #eee;
    padding: 12px 40px;
    font-size: 13px;
    color: #888;
  }}
  /* 文章列表 */
  .articles {{
    padding: 32px 40px 40px;
  }}
  .article {{
    margin-bottom: 36px;
    padding-bottom: 36px;
    border-bottom: 1px solid #f0f0f0;
  }}
  .article:last-child {{
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
  }}
  /* 文章标题 */
  .article h2 {{
    font-size: 17px;
    font-weight: 600;
    color: #1a1a2e;
    line-height: 1.5;
    margin-bottom: 12px;
    padding-left: 14px;
    border-left: 4px solid #1a1a2e;
  }}
  /* 文章正文 */
  .article p {{
    font-size: 15px;
    line-height: 1.85;
    color: #3a3a3a;
    margin-bottom: 10px;
  }}
  /* 链接 */
  .article a {{
    color: #1a1a2e;
    text-decoration: none;
    font-weight: 500;
  }}
  .article a:hover {{
    text-decoration: underline;
  }}
  /* 原文链接 */
  .article em {{
    display: block;
    margin-top: 12px;
    font-size: 12px;
    color: #aaa;
    font-style: normal;
  }}
  /* 列表 */
  .article ul, .article ol {{
    padding-left: 24px;
    margin: 8px 0;
  }}
  .article li {{
    font-size: 15px;
    line-height: 1.85;
    color: #3a3a3a;
    margin-bottom: 4px;
  }}
  .article strong {{
    color: #1a1a2e;
    font-weight: 600;
  }}
  /* 页脚 */
  .footer {{
    background: #fafafa;
    border-top: 1px solid #eee;
    padding: 20px 40px;
    text-align: center;
  }}
  .footer p {{
    font-size: 11px;
    color: #bbb;
    line-height: 1.8;
  }}
  .footer a {{
    color: #1a1a2e;
    text-decoration: none;
  }}
  @media (max-width: 480px) {{
    body {{ padding: 10px 0; }}
    .header {{ padding: 24px 20px; }}
    .articles {{ padding: 24px 20px 32px; }}
    .meta-bar {{ padding: 10px 20px; }}
    .footer {{ padding: 16px 20px; }}
  }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <div class="header-inner">
      <div>
        <h1>The New Yorker 日报</h1>
        <div class="subtitle">美国深度报道精选 · AI 摘要翻译</div>
      </div>
      <div class="date-badge">
        <span>日期</span>
        {date_fmt}
      </div>
    </div>
  </div>
  <div class="meta-bar">今日共收录 {len(sections)} 篇精选文章</div>
  <div class="articles">{articles_html}</div>
  <div class="footer">
    <p>由 OpenClaw Agent 自动生成 · 每日定时推送</p>
    <p>原文来源：The New Yorker (feedx.net)</p>
  </div>
</div>
</body>
</html>"""
    return html


def send_email(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.strip():
        print("File is empty: " + filepath)
        return False

    date_str = extract_date(filepath)
    date_fmt = datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")

    html = make_html(content, date_str)

    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = f"The New Yorker 日报 · {date_fmt}"
    msg.attach(MIMEText(html, "html", "utf-8"))

    print(f"SMTP: {SMTP_HOST}:{SMTP_PORT} -> {EMAIL_TO}")
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())
        print("Email sent: " + EMAIL_TO)
        return True
    except Exception as e:
        print("Error: " + str(e))
        return False


def main(filepath=None):
    if filepath is None and len(sys.argv) > 1:
        filepath = sys.argv[1]
    if not filepath:
        print("No filepath provided")
        return
    send_email(filepath)


if __name__ == "__main__":
    main()
