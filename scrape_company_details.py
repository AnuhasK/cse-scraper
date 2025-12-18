import requests
import pandas as pd
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = 'https://www.cse.lk/api/'
ENDPOINT = 'companyInfoSummery'
TXT_FILE = 'company-symbols.txt'

def get_company_symbols(txt_path):
    symbols = []
    with open(txt_path, 'r') as f:
        for line in f:
            symbol = line.strip()
            if symbol:
                symbols.append(symbol)
    return symbols

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
            resp = requests.post(BASE_URL + ENDPOINT, data=data, headers=headers)
            if resp.status_code != 200:
                print(f"{symbol}: HTTP {resp.status_code}")
                return None
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
            print(f"{symbol} OK")
            return row
        except Exception as e:
            print(f"{symbol}: error {e}")
            return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_symbol = {executor.submit(fetch_symbol, symbol): symbol for symbol in symbols}
        for i, future in enumerate(as_completed(future_to_symbol)):
            result = future.result()
            if result:
                rows.append(result)

    if rows:
        from datetime import datetime
        date_str = datetime.now().strftime('%Y-%m-%d')
        dated_dir = Path(__file__).parent / 'data' / date_str
        dated_dir.mkdir(parents=True, exist_ok=True)
        out_csv = dated_dir / f'all_company_info_{date_str}.csv'
        df = pd.DataFrame(rows)
        df.to_csv(out_csv, index=False)
        print(f"Wrote {len(df)} rows to {out_csv}")
    else:
        print("No data fetched.")

def main():
    symbols = get_company_symbols(TXT_FILE)
    fetch_and_save_company_details(symbols, None)

if __name__ == '__main__':
    main()
