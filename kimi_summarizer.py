"""
New Yorker Kimi 翻译器
使用 Kimi K2.5 将英文文章翻译为中文综述
"""
import os
import sys
import logging
import requests
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

KIMI_API_KEY = os.getenv("kimi_API_KEY")
KIMI_MODEL = os.getenv("KIMI_MODEL", "moonshotai/kimi-k2.5")
KIMI_API_URL = os.getenv("KIMI_API_URL", "https://integrate.api.nvidia.com/v1/chat/completions")

PROMPT = """请直接用中文撰写以下英文文章的摘要，要求：

1. 不需要翻译全文，直接从英文提炼中文摘要
2. 信息密度高，覆盖主要观点、背景、意义
3. 关键细节（人名、机构名、数据）要保留
4. 字数控制：如果原文超过 2000 英文单词，摘要中文控制在 1000 字左右（约原文的 50%）；2000 字以内的文章可直接完整翻译
5. 风格简洁，不要"本文讨论了"这类废话
6. 争议话题保持中立

直接输出中文摘要，不要加入任何无关内容"""


def translate(content):
    if not KIMI_API_KEY:
        logging.error("kimi_API_KEY not set")
        sys.exit(1)

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + KIMI_API_KEY
    }
    data = {
        "model": KIMI_MODEL,
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": content}
        ],
        "temperature": 0.7,
        "max_tokens": 16000
    }

    for attempt in range(5):
        try:
            logging.info("Translation request (attempt " + str(attempt + 1) + "/5)...")
            resp = requests.post(KIMI_API_URL, headers=headers, json=data, timeout=300)
            resp.raise_for_status()
            result = resp.json()
            if result.get("choices") and result["choices"][0]:
                return result["choices"][0]["message"]["content"]
            else:
                logging.error("API response error: " + str(result))
                if attempt < 4:
                    wait = 30 * (2 ** attempt)
                    logging.info("Retry in " + str(wait) + "s...")
                    time.sleep(wait)
        except Exception as e:
            logging.error("Request failed: " + str(e))
            if attempt < 4:
                time.sleep(30 * (2 ** attempt))
    return None


def translate_file(filepath):
    if not os.path.exists(filepath):
        logging.error("File not found: " + filepath)
        return False

    os.makedirs("translate", exist_ok=True)
    outpath = os.path.join("translate", os.path.basename(filepath))

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    logging.info("Start translation: " + filepath + " (" + str(len(content)) + " chars)")
    result = translate(content)

    if result:
        with open(outpath, 'w', encoding='utf-8') as f:
            f.write(result)
        logging.info("Translation saved: " + outpath)
        return True
    else:
        logging.error("Translation failed")
        return False


if __name__ == "__main__":
    import glob
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        translate_file(filepath)
    else:
        files = glob.glob("articles/*.md")
        if files:
            latest = max(files, key=os.path.getmtime)
            translate_file(latest)
        else:
            logging.error("No article files found")
