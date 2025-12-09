import requests
import pandas as pd
import time
from pathlib import Path

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
    for i, symbol in enumerate(symbols):
        data = {'symbol': symbol}
        try:
            resp = requests.post(BASE_URL + ENDPOINT, data=data, headers=headers, timeout=15)
            if resp.status_code != 200:
                print(f"{symbol}: HTTP {resp.status_code}")
                continue
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
            rows.append(row)
            print(f"{i+1}/{len(symbols)}: {symbol} OK")
        except Exception as e:
            print(f"{symbol}: error {e}")
        time.sleep(0.5)
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
