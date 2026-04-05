"""
Email sender with HTML formatting
"""
import os, sys, re, smtplib, ssl, markdown
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

EMAIL_TO = os.getenv("EMAIL_TO") or ""
EMAIL_FROM = os.getenv("EMAIL_FROM") or ""
SMTP_HOST = os.getenv("SMTP_HOST") or ""
SMTP_PORT = int(os.getenv("SMTP_PORT") or "465")
SMTP_USER = os.getenv("SMTP_USER") or ""
SMTP_PASS = os.getenv("SMTP_PASS") or ""

if not all([EMAIL_TO, EMAIL_FROM, SMTP_HOST, SMTP_USER, SMTP_PASS]):
    print("ERROR: Missing env vars"); sys.exit(1)

HTML_TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DIAMOND</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#f0f2f5;font-family:-apple-system,PingFang SC,Microsoft YaHei,sans-serif;color:#1a1a1a;padding:20px 0}
.wrapper{max-width:680px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08)}
.header{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:32px 40px;position:relative}
.header::after{content:'';position:absolute;bottom:-20px;left:0;right:0;height:20px;background:linear-gradient(to bottom right,#8b0000 0%,#8b0000 50%,transparent 50%)}
.hi{display:flex;align-items:center;justify-content:space-between}
.hi h1{font-size:22px;font-weight:700;color:#fff}
.hi .sub{font-size:14px;opacity:0.85;margin-top:4px;color:#c0c0c0}
.db{background:rgba(255,255,255,0.2);border:1px solid rgba(255,255,255,0.4);border-radius:20px;padding:6px 16px;font-size:13px;text-align:center}
.db span{display:block;font-size:11px;opacity:0.7;margin-bottom:2px}
.mb{background:#fafafa;border-bottom:1px solid #eee;padding:12px 40px;font-size:13px;color:#888}
.arts{padding:32px 40px 40px}
.art{margin-bottom:36px;padding-bottom:36px;border-bottom:1px solid #f0f0f0}
.art:last-child{border-bottom:none;margin-bottom:0;padding-bottom:0}
.art h2{font-size:17px;font-weight:600;color:#1a1a1a;line-height:1.5;margin-bottom:12px;padding-left:14px;border-left:4px solid #1a1a2e}
.art p{font-size:15px;line-height:1.85;color:#3a3a3a;margin-bottom:10px}
.art a{color:#1a1a2e;text-decoration:none;font-weight:500}
.art em{display:block;margin-top:12px;font-size:12px;color:#aaa;font-style:normal}
.art ul,.art ol{padding-left:24px;margin:8px 0}
.art li{font-size:15px;line-height:1.85;color:#3a3a3a;margin-bottom:4px}
.art strong{color:#1a1a1a;font-weight:600}
.ft{background:#fafafa;border-top:1px solid #eee;padding:20px 40px;text-align:center}
.ft p{font-size:11px;color:#bbb;line-height:1.8}
.ft a{color:#1a1a2e;text-decoration:none}
@media(max-width:480px){body{padding:10px 0}.header,.arts,.mb,.ft{padding:24px 20px 20px}.arts{padding:24px 20px 32px}}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <div class="hi">
      <div><h1>The New Yorker 日报</h1><div class="sub">美国深度报道精选 · AI 摘要翻译</div></div>
      <div class="db"><span>日期</span>{{DATE}}</div>
    </div>
  </div>
  <div class="mb">今日共收录 {{COUNT}} 篇精选文章</div>
  <div class="arts">{{ARTICLES}}</div>
  <div class="ft"><p>由 OpenClaw Agent 自动生成 · 每日定时推送</p><p>原文来源：The New Yorker (feedx.net)</p></div>
</div>
</body>
</html>"""


def extract_date(path):
    m = re.search(r"(\d{8})", path)
    return m.group(1) if m else datetime.now().strftime("%Y%m%d")


def make_html(content, date_str):
    df = datetime.strptime(date_str, "%Y%m%d").strftime("%Y年%m月%d日")
    secs = re.split(r"\n(?=## )", content.strip())
    arts_html = ""
    for i, s in enumerate(secs):
        s = s.strip()
        if not s:
            continue
        ah = markdown.markdown(s, extensions=["fenced_code", "tables"], output_format="html")
        arts_html += '<div class="art%s">%s</div>' % ("" if i % 2 == 0 else " odd", ah)
    return HTML_TPL.replace("{{DATE}}", df).replace("{{COUNT}}", str(len(secs))).replace("{{ARTICLES}}", arts_html)


def send_email(path):
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()
    if not c.strip():
        print("Empty file:", path)
        return False
    ds = extract_date(path)
    df = datetime.strptime(ds, "%Y%m%d").strftime("%Y-%m-%d")
    html = make_html(c, ds)
    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = "The New Yorker 日报 · " + df
    msg.attach(MIMEText(html, "html", "utf-8"))
    print("SMTP: %s:%s -> %s" % (SMTP_HOST, SMTP_PORT, EMAIL_TO))
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as s:
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())
        print("Email sent:", EMAIL_TO)
        return True
    except Exception as e:
        print("Error:", e)
        return False


def main(path=None):
    if path is None and len(sys.argv) > 1:
        path = sys.argv[1]
    if not path:
        print("No filepath")
        return
    send_email(path)


if __name__ == "__main__":
    main()
