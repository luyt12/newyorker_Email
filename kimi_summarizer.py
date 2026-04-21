"""
New Yorker article translator.
Primary: Kimi LLM (summarize + translate + style).
Fallback: Baidu AI Translation (translate only, on Kimi failure).
"""
import os
import sys
import logging
import requests
import time

logging.basicConfig(level=logging.INFO,
                    format=''%(asctime)s - %(levelname)s - %(message)s'')

KIMI_API_KEY  = os.getenv("kimi_API_KEY")
KIMI_MODEL    = os.getenv("KIMI_MODEL", "moonshotai/kimi-k2.5")
KIMI_API_URL  = os.getenv("KIMI_API_URL",
                           "https://integrate.api.nvidia.com/v1/chat/completions")

INPUT_DIR  = "articles"
OUTPUT_DIR = "translate"

PROMPT = """You are a professional English media editor. Please complete two tasks on the The New Yorker article below:

## Task 1: Extract Key Points
Read the original text carefully and extract the most important information:
- What is the core topic or argument?
- What key quotes, data, or figures are mentioned?
- What are the main conclusions?
- What is the most important takeaway for readers?

## Task 2: Translate and Summarize
Translate the extracted key points into Simplified Chinese with these requirements:
1. Output 300-500 characters in Chinese summary
2. Use Markdown format, second-level heading for article title
3. Include original article link below the title
4. Accuracy: faithful to original, preserve key quotes and data
5. Fluency: natural modern Chinese, avoid translationese
6. Conciseness: break long sentences, use precise language
7. Include at least one memorable quote from the original

## Output Format
Output the Chinese summary directly, no introductions or meta-comments."""


def kimi_translate(content):
    """Primary: translate via Kimi LLM (summarizes + translates + styles)."""
    if not KIMI_API_KEY:
        logging.error("kimi_API_KEY not set")
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {KIMI_API_KEY}"
    }
    payload = {
        "model": KIMI_MODEL,
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user",   "content": content}
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }

    for attempt in range(5):
        try:
            logging.info(f"[KIMI] Submitting (attempt {attempt + 1}/5)...")
            resp = requests.post(
                KIMI_API_URL,
                headers=headers,
                json=payload,
                timeout=300
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("choices") and result["choices"][0]:
                text = result["choices"][0]["message"]["content"]
                logging.info(f"[KIMI] OK: {len(text)} chars")
                return text
            else:
                logging.error(f"[KIMI] API response unexpected: {result}")
            if attempt < 4:
                time.sleep(30 * (2 ** attempt))
        except requests.exceptions.Timeout:
            logging.error(f"[KIMI] Timeout (attempt {attempt + 1}/5)")
            if attempt < 4:
                time.sleep(30 * (2 ** attempt))
        except Exception as e:
            logging.error(f"[KIMI] Request failed: {e}")
            if attempt < 4:
                time.sleep(30 * (2 ** attempt))
    return None


def baidu_fallback(text):
    """
    Fallback: translate via Baidu AI Translation API (Bearer Token auth).
    Only does translation (no summarization/styling).
    Returns None on failure.
    """
    api_key = os.getenv("BAIDU_API_KEY", "")
    if not api_key:
        logging.error("[BAIDU] Missing BAIDU_API_KEY env var")
        return None

    # Truncate to 2800 chars to stay well within limit
    if len(text) > 2800:
        text = text[:2800]

    endpoint = "https://fanyi-api.baidu.com/ait/api/aiTextTranslate"
    for attempt in range(3):
        try:
            logging.info(f"[BAIDU] Translating (attempt {attempt + 1}/3)...")
            resp = requests.post(
                endpoint,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                json={"q": text, "from": "en", "to": "zh"},
                timeout=30
            )
            data = resp.json()

            if data.get("error_code"):
                logging.error(f"[BAIDU] API error: {data.get(''error_code'')} - {data.get(''error_msg'', '''')}")
                if attempt < 2:
                    time.sleep(5)
                continue

            if "data" in data and data["data"]:
                result = data["data"].get("trans_result", "")
                if result:
                    logging.info(f"[BAIDU] OK: {len(result)} chars")
                    return result

            logging.error(f"[BAIDU] Unexpected response: {data}")
            return None
        except Exception as e:
            logging.error(f"[BAIDU] Request failed: {e}")
            if attempt < 2:
                time.sleep(5)
    return None


def translate_file(filepath):
    if not os.path.exists(filepath):
        logging.error(f"File not found: {filepath}")
        return False

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    outpath = os.path.join(OUTPUT_DIR, os.path.basename(filepath))

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    logging.info(f"Starting: {filepath} ({len(content)} chars)")

    # Step 1: Try Kimi (primary) — summarize + translate + style
    result = kimi_translate(content)

    if result is None:
        # Step 2: Kimi failed — try Baidu fallback (translate only)
        logging.warning("[FALLBACK] Kimi failed — switching to Baidu translation...")
        lines = content.split("\n")
        title_line = ""
        body_lines = []
        for line in lines:
            if line.startswith("## "):
                title_line = line
            else:
                body_lines.append(line)
        body = "\n".join(body_lines)
        translated_body = baidu_fallback(body)
        if translated_body is None:
            logging.error("[FALLBACK] Baidu also failed — translation skipped")
            return False
        result = (title_line + "\n\n" + translated_body) if title_line else translated_body

    with open(outpath, "w", encoding="utf-8") as f:
        f.write(result)
    logging.info(f"Done: {outpath} ({len(result)} chars)")
    return True


if __name__ == "__main__":
    import glob as _glob
    if len(sys.argv) > 1:
        if os.path.isfile(sys.argv[1]):
            translate_file(sys.argv[1])
        else:
            for f in sorted(_glob.glob(os.path.join(INPUT_DIR, sys.argv[1]))):
                translate_file(f)
    else:
        files = sorted(_glob.glob(os.path.join(INPUT_DIR, "*.md")))
        if files:
            for f in files:
                translate_file(f)
        else:
            logging.error("No article files found")