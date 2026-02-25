import argparse
import csv
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path

import requests

API_URL = "https://www.cse.lk/api/getAnnouncementByCompany"


def parse_ymd(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def safe_filename(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return value.strip("._-") or "unknown"


def load_symbols_from_csv(csv_path: str) -> list[str]:
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        first_row = next(reader, None)
        if not first_row:
            return []

        header_cells = [(c or "").strip().lower() for c in first_row]
        symbol_idx = None
        for i, cell in enumerate(header_cells):
            if cell == "symbol" or "symbol" in cell:
                symbol_idx = i
                break

        symbols: list[str] = []
        seen: set[str] = set()

        def add_symbol(s: str) -> None:
            s = (s or "").strip()
            if not s or s.lower() == "nan":
                return
            if s in seen:
                return
            seen.add(s)
            symbols.append(s)

        if symbol_idx is None:
            # No header detected; treat first row as data.
            add_symbol(first_row[0] if first_row else "")
            symbol_idx = 0

        for row in reader:
            if not row:
                continue
            if symbol_idx >= len(row):
                continue
            add_symbol(row[symbol_idx])

        return symbols


def load_symbols_from_txt(txt_path: str) -> list[str]:
    symbols: list[str] = []
    seen: set[str] = set()
    with open(txt_path, "r", encoding="utf-8-sig") as f:
        for line in f:
            s = line.strip()
            if not s or s.lower() == "nan":
                continue
            if s in seen:
                continue
            seen.add(s)
            symbols.append(s)
    return symbols


def fetch_and_save(symbol: str, from_date: date, to_date: date, out_dir: Path, timeout_s: int) -> str:
    params = {
        "symbol": symbol,
        "fromDate": from_date.strftime("%Y-%m-%d"),
        "toDate": to_date.strftime("%Y-%m-%d"),
    }
    resp = requests.get(API_URL, params=params, timeout=timeout_s)
    if resp.status_code == 405:
        resp = requests.post(API_URL, params=params, timeout=timeout_s)
    resp.raise_for_status()
    payload = resp.json()

    out_path = out_dir / f"{safe_filename(symbol)}_{params['fromDate']}_{params['toDate']}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return symbol


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape CSE announcements per company symbol (parallel) and save JSON per symbol."
    )
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--txt", default="company-symbols.txt")
    src.add_argument("--csv")
    parser.add_argument("--from", dest="from_date", default="2020-01-28")
    parser.add_argument("--to", dest="to_date", default=date.today().strftime("%Y-%m-%d"))
    parser.add_argument("--out", default="company-announcements")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    from_date = parse_ymd(args.from_date)
    to_date = parse_ymd(args.to_date)
    if from_date > to_date:
        raise SystemExit("--from must be <= --to")

    if args.csv:
        symbols = load_symbols_from_csv(args.csv)
    else:
        symbols = load_symbols_from_txt(args.txt)
    if args.limit and args.limit > 0:
        symbols = symbols[: args.limit]

    out_dir = Path(args.out) / date.today().strftime("%Y-%m-%d")
    print(f"Loaded {len(symbols)} symbols")
    print(f"Saving to {out_dir}")

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futures = {
            ex.submit(fetch_and_save, s, from_date, to_date, out_dir, args.timeout): s
            for s in symbols
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                future.result()
                print(f"{symbol} OK")
            except Exception as e:
                print(f"{symbol} ERROR: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
