import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import requests

API_URL = "https://www.cse.lk/api/companyInfoSummery"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) cse-scraper/1.0",
    "Accept": "application/json, text/plain, */*",
}


def load_symbols(txt_path: str) -> list[str]:
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


def fetch_name(symbol: str, timeout_s: int) -> tuple[str, str | None, str | None]:
    try:
        resp = requests.post(
            API_URL,
            data={"symbol": symbol},
            headers=HEADERS,
            timeout=timeout_s,
        )
        resp.raise_for_status()
        payload = resp.json()

        info = payload.get("reqSymbolInfo") if isinstance(payload, dict) else None
        name = info.get("name") if isinstance(info, dict) else None
        if isinstance(name, str):
            name = name.strip() or None

        return symbol, name, None
    except Exception as e:
        return symbol, None, str(e)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape company names for all symbols in a TXT file (parallel)."
    )
    parser.add_argument("--txt", default="company-symbols.txt")
    parser.add_argument("--out", default="company-names")
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    symbols = load_symbols(args.txt)
    if args.limit and args.limit > 0:
        symbols = symbols[: args.limit]

    run_date = date.today().strftime("%Y-%m-%d")
    out_dir = Path(args.out) / run_date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / f"company_names_{run_date}.csv"

    print(f"Loaded {len(symbols)} symbols")
    print(f"Writing {out_csv}")

    results: list[tuple[str, str | None, str | None]] = []

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futures = {ex.submit(fetch_name, s, args.timeout): s for s in symbols}
        for future in as_completed(futures):
            symbol, name, error = future.result()
            results.append((symbol, name, error))
            if error:
                print(f"{symbol} ERROR: {error}")
            else:
                print(f"{symbol} OK")

    results.sort(key=lambda t: t[0])

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "name", "error"])
        w.writerows(results)

    ok = sum(1 for _, name, err in results if name and not err)
    print(f"Done. OK={ok} total={len(results)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
