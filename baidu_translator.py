"""
Baidu AI Translation API fallback.
Sign auth: appid + q + salt + secret_key -> MD5 -> sign

Usage:
  from baidu_translator import translate_text
  result = translate_text("Hello world", from_lang="en", to_lang="zh")
"""
import os
import hashlib
import time
import random
import requests

APPID = os.getenv("BAIDU_APPID", "")
SECRET_KEY = os.getenv("BAIDU_SECRET_KEY", "")
ENDPOINT = "https://fanyi-api.baidu.com/ait/api/aiTextTranslate"

# Fallback endpoint (older API, more stable)
FALLBACK_ENDPOINT = "https://fanyi-api.baidu.com/api/trans/vip/translate"


def make_sign(appid, q, salt, secret_key):
    sign_str = f"{appid}{q}{salt}{secret_key}"
    return hashlib.md5(sign_str.encode("utf-8")).hexdigest()


def translate_text(text, from_lang="en", to_lang="zh", use_llm=True):
    """
    Translate text using Baidu AI Translation API.

    Args:
        text: Source text (max ~3000 chars for safety with sign auth)
        from_lang: Source language code ("en", "auto", etc.)
        to_lang: Target language code ("zh", etc.)
        use_llm: Use LLM translation (True) or NMT (False)

    Returns:
        Translated text string, or None on failure.
    """
    if not APPID or not SECRET_KEY:
        print("[BAIDU] Missing BAIDU_APPID or BAIDU_SECRET_KEY env vars")
        return None

    # Truncate to 3000 chars to stay well within limits
    if len(text) > 3000:
        print(f"[BAIDU] Text too long ({len(text)} chars), truncating to 3000")
        text = text[:3000]

    salt = str(random.randint(10000, 99999))
    sign = make_sign(APPID, text, salt, SECRET_KEY)

    # Use the older (more stable) translate API with sign auth
    # This supports both NMT and has a generous free tier
    url = FALLBACK_ENDPOINT

    params = {
        "q": text,
        "from": from_lang,
        "to": to_lang,
        "appid": APPID,
        "salt": salt,
        "sign": sign,
    }

    try:
        resp = requests.post(url, data=params, timeout=30)
        data = resp.json()

        if data.get("error_code"):
            print(f"[BAIDU] API error: {data.get('error_code')} - {data.get('error_msg', '')}")
            return None

        if "trans_result" in data and len(data["trans_result"]) > 0:
            # Join all translated segments
            result = "\n".join(item["dst"] for item in data["trans_result"])
            print(f"[BAIDU] OK: {len(data['trans_result'])} segments, {len(result)} chars")
            return result
        else:
            print(f"[BAIDU] Unexpected response: {data}")
            return None

    except Exception as e:
        print(f"[BAIDU] Request failed: {e}")
        return None


def translate_file(input_path, output_path=None, from_lang="en", to_lang="zh"):
    """
    Read a markdown file, translate it, write to output_path.
    Returns True on success.
    """
    if output_path is None:
        output_path = input_path.replace(".md", "_translated.md")

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"[BAIDU] Failed to read {input_path}: {e}")
        return False

    # Extract title (first ## heading) and translate it
    lines = content.split("\n")
    title = ""
    body_lines = []
    for i, line in enumerate(lines):
        if line.startswith("## "):
            title = line
        else:
            body_lines.append(line)

    body = "\n".join(body_lines)
    translated_body = translate_text(body, from_lang, to_lang)
    if translated_body is None:
        return False

    # Reconstruct: title + translated body
    result = title + "\n\n" + translated_body
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"[BAIDU] Wrote: {output_path}")
        return True
    except Exception as e:
        print(f"[BAIDU] Failed to write {output_path}: {e}")
        return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python baidu_translator.py <text>")
        sys.exit(1)
    result = translate_text(sys.argv[1])
    if result:
        print(result)
    else:
        print("Translation failed")
        sys.exit(1)
