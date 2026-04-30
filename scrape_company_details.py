import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from holiday_utils import is_holiday, today_str

BASE_URL = 'https://www.cse.lk/api/'
ENDPOINT = 'companyInfoSummery'
TXT_FILE = 'company-symbols.txt'
REQUEST_TIMEOUT = (5, 30)
MAX_ATTEMPTS = 3
BACKOFF_SECS = 1.5
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / 'logs'

logger = logging.getLogger(__name__)

def get_company_symbols(txt_path):
    symbols = []
    with open(txt_path, 'r') as f:
        for line in f:
            symbol = line.strip()
            if symbol:
                symbols.append(symbol)
    return symbols

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

def fetch_and_save_company_details(symbols, output_dir):
    rows = []
    headers = {
        'User-Agent': 'PostmanRuntime/7.49.1',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }

    def fetch_symbol(symbol):
        data = {'symbol': symbol}
        try:
            resp = post_with_retries(BASE_URL + ENDPOINT, data=data, headers=headers)
            info = resp.json()
            row = {'symbol': symbol}
            if 'reqSymbolInfo' in info and isinstance(info['reqSymbolInfo'], dict):
                row.update(info['reqSymbolInfo'])
            if 'reqLogo' in info and isinstance(info['reqLogo'], dict):
                for k, v in info['reqLogo'].items():
                    row['logo_' + k] = v
            if 'reqSymbolBetaInfo' in info and isinstance(info['reqSymbolBetaInfo'], dict):
                for k, v in info['reqSymbolBetaInfo'].items():
                    row['beta_' + k] = v
            logger.info("%s OK", symbol)
            return row
        except Exception as e:
            logger.error("%s: error %s", symbol, e)
            return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_symbol = {executor.submit(fetch_symbol, symbol): symbol for symbol in symbols}
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                result = future.result()
            except Exception as exc:
                logger.error("%s: unhandled error %s", symbol, exc)
                continue
            if result:
                rows.append(result)

    total = len(symbols)
    success = len(rows)
    failures = total - success

    if rows:
        date_str = datetime.now().strftime('%Y-%m-%d')
        dated_dir = Path(__file__).parent / 'data' / date_str
        dated_dir.mkdir(parents=True, exist_ok=True)
        out_csv = dated_dir / f'all_company_info_{date_str}.csv'
        df = pd.DataFrame(rows)
        df.to_csv(out_csv, index=False)
        logger.info("Wrote %d rows to %s", len(df), out_csv)
    else:
        logger.error("No data fetched.")

    logger.info("Symbols: %d, success: %d, failures: %d", total, success, failures)
    return success, failures

def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    date_str = today_str()
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
        if is_holiday(date_str):
            logger.info("Holiday skip: %s", date_str)
            return 0
        symbols = get_company_symbols(TXT_FILE)
        if not symbols:
            logger.error("No symbols found in %s", TXT_FILE)
            return 1
        success, failures = fetch_and_save_company_details(symbols, None)
        if success == 0 or failures:
            return 1
        return 0
    except Exception:
        logger.exception("Fatal error")
        return 1

if __name__ == '__main__':
    sys.exit(main())
