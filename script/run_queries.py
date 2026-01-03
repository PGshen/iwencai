import csv
import json
import random
import time
import logging
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


BASE_URL = "http://localhost:8000/api/scrape/simple"
TEMP_DIR = Path("/Users/peng/Me/Ai/iwencai/temp/stock1")
CSV_PATH = TEMP_DIR / "stock1.csv"
REQUEST_TIMEOUT_SECONDS = 60.0
MAX_RETRIES = 5

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("run_queries")


def post_json(url: str, payload: dict, timeout: float = 60.0) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            body = resp.read().decode(charset)
            return json.loads(body)
    except (HTTPError, URLError) as e:
        raise RuntimeError(f"HTTP error: {e}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON response: {e}") from e


def ensure_json_filename(name: str) -> str:
    return name if name.lower().endswith(".json") else f"{name}.json"


def sleep_random():
    secs = random.randint(5, 15)
    logger.info(f"休眠 {secs} 秒")
    time.sleep(secs)


def preview(text: str, n: int = 120) -> str:
    t = (text or "").replace("\n", " ")
    return t[:n] + ("..." if len(t) > n else "")


def process_row(output_name: str, question: str):
    logger.info(f"开始处理 {ensure_json_filename(output_name)}")
    logger.info(f"问题 {preview(question)}")
    out_path = TEMP_DIR / ensure_json_filename(output_name)
    if out_path.exists():
        logger.info(f"已处理过 {out_path}，跳过")
        return
    payload1 = {
        "template_name": "get-robot-data",
        "params": {"question": question},
    }
    condition = None
    token = None
    for attempt in range(1, MAX_RETRIES + 1):
        logger.info(f"调用接口一 get-robot-data 尝试 {attempt}/{MAX_RETRIES}")
        try:
            resp1 = post_json(BASE_URL, payload1, timeout=REQUEST_TIMEOUT_SECONDS)
            data1 = resp1.get("data")
            if isinstance(data1, dict):
                condition = data1.get("condition")
                token = data1.get("token")
            if condition:
                logger.info(f"获得 condition {preview(str(condition), 200)}")
                sleep_random()
                break
            else:
                logger.warning("未获取到 condition，准备重试")
                sleep_random()
        except RuntimeError as e:
            logger.warning(f"接口一调用失败: {e}，准备重试")
            sleep_random()
    if not condition:
        logger.error("多次重试后仍未获取到 condition，跳过该行")
        return
    random_token = str(random.randint(1000000000, 9999999999))
    payload2 = {
        "template_name": "iwencai_export",
        "params": {"query": question, "condition": condition, "iwc_token": token, "randomStr": random_token},
    }
    out_data = None
    for attempt in range(1, MAX_RETRIES + 1):
        logger.info(f"调用接口二 iwencai_export 尝试 {attempt}/{MAX_RETRIES}")
        try:
            resp2 = post_json(BASE_URL, payload2, timeout=REQUEST_TIMEOUT_SECONDS)
            out_data = resp2.get("data")
            sleep_random()
            if out_data:
                break
            else:
                logger.warning("接口二返回的 data 为空，准备重试")
        except RuntimeError as e:
            logger.warning(f"接口二调用失败: {e}，准备重试")
            sleep_random()
    if not out_data:
        logger.error("多次重试后仍未获取到有效 data，跳过该行")
        return
    out_path = TEMP_DIR / ensure_json_filename(output_name)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out_data, f, ensure_ascii=False, indent=2)
    logger.info(f"已保存到 {out_path}")


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")
    logger.info(f"读取 CSV {CSV_PATH}")
    with CSV_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            output_name = (row.get("output_name") or "").strip()
            question = (row.get("question") or "").strip()
            if not output_name or not question:
                continue
            process_row(output_name, question)


if __name__ == "__main__":
    main()
