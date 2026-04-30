import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# Read API endpoints from the txt file
API_FILE = 'api_endpoint_urls.txt'
OUTPUT_DIR = 'data'
REQUEST_TIMEOUT = (5, 30)
MAX_ATTEMPTS = 3
BACKOFF_SECS = 1.5
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / 'logs'

logger = logging.getLogger(__name__)

def post_with_retries(url, *, data=None, headers=None):
    last_exc = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.post(url, data=data, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < MAX_ATTEMPTS:
                sleep_for = BACKOFF_SECS * attempt
                logger.warning(
                    "Request failed (%s/%s) %s: %s; retrying in %.1fs",
                    attempt,
                    MAX_ATTEMPTS,
                    url,
                    exc,
                    sleep_for,
                )
                time.sleep(sleep_for)
            else:
                raise
    raise last_exc

def get_api_endpoints(file_path):
    endpoints = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and line.startswith('http'):
                url = line.split()[0]
                endpoints.append(url)
    return endpoints

def fetch_and_save_all(endpoints, output_dir):
    if not endpoints:
        logger.error("No API endpoints found in %s", API_FILE)
        return 0, 1
    date_str = datetime.now().strftime('%Y-%m-%d')
    dated_dir = os.path.join(output_dir, date_str)
    os.makedirs(dated_dir, exist_ok=True)
    saved = 0
    errors = 0
    for url in endpoints:
        try:
            response = post_with_retries(url)
            data = response.json()
        except Exception as e:
            errors += 1
            data = {'error': str(e)}
            logger.error("Failed to fetch %s: %s", url, e)
        # Create a safe filename from the endpoint
        endpoint_name = url.split('/')[-1] or url.split('/')[-2]
        filename = f'{endpoint_name}_{date_str}.json'
        filepath = os.path.join(dated_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        saved += 1
        logger.info("Saved: %s", filepath)
    logger.info("Saved %d files (%d errors)", saved, errors)
    return saved, errors

def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime('%Y-%m-%d')
    log_file = LOG_DIR / f'scraper_{date_str}.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding='utf-8'),
        ],
    )
    try:
        endpoints = get_api_endpoints(API_FILE)
        saved, errors = fetch_and_save_all(endpoints, OUTPUT_DIR)
        if saved == 0 or errors:
            return 1
        return 0
    except Exception:
        logger.exception("Fatal error")
        return 1

if __name__ == '__main__':
    sys.exit(main())
