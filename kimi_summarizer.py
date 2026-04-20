"""
New Yorker article translator
Summarize and translate English articles to Chinese.
"""
import os
import sys
import logging
import requests
import time

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

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


def summarize_and_translate(content):
    if not KIMI_API_KEY:
        logging.error("kimi_API_KEY not set")
        sys.exit(1)

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
            logging.info(f"Submitting (attempt {attempt + 1}/5)...")
            resp = requests.post(
                KIMI_API_URL,
                headers=headers,
                json=payload,
                timeout=300
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("choices") and result["choices"][0]:
                return result["choices"][0]["message"]["content"]
            logging.error(f"API response unexpected: {result}")
            if attempt < 4:
                time.sleep(30 * (2 ** attempt))
        except requests.exceptions.Timeout:
            logging.error(f"Timeout (attempt {attempt + 1}/5)")
            if attempt < 4:
                time.sleep(30 * (2 ** attempt))
        except Exception as e:
            logging.error(f"Request failed: {e}")
            if attempt < 4:
                time.sleep(30 * (2 ** attempt))
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
    result = summarize_and_translate(content)

    if result:
        with open(outpath, "w", encoding="utf-8") as f:
            f.write(result)
        logging.info(f"Done: {outpath} ({len(result)} chars)")
        return True
    else:
        logging.error("Translation failed")
        return False


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
