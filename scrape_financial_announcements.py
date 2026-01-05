import requests
import os
import json
from datetime import datetime, timedelta

API_URL = "https://www.cse.lk/api/getFinancialAnnouncement"
OUTPUT_DIR = "financial-reports"

def daterange(start_date, end_date):
    """Yield (from_date, to_date) tuples for each year in the range."""
    current = start_date
    while current < end_date:
        year_end = datetime(current.year, 12, 31)
        to_date = min(year_end, end_date)
        yield current, to_date
        current = to_date + timedelta(days=1)

def fetch_announcements(from_date, to_date):
    params = {
        "fromDate": from_date.strftime("%Y-%m-%d"),
        "toDate": to_date.strftime("%Y-%m-%d")
    }
    print(f"Fetching: {params['fromDate']} to {params['toDate']}")
    response = requests.post(API_URL, params=params)
    response.raise_for_status()
    return response.json()

def save_json(data, from_date, to_date):
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    filename = f"announcements_{from_date.strftime('%Y')}_{to_date.strftime('%Y')}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved: {filepath}")

def main():
    start_date = datetime(2000, 1, 1)
    end_date = datetime(2010, 1, 2)
    for from_date, to_date in daterange(start_date, end_date):
        try:
            data = fetch_announcements(from_date, to_date)
            save_json(data, from_date, to_date)
        except Exception as e:
            print(f"Error for {from_date} to {to_date}: {e}")

if __name__ == "__main__":
    main()