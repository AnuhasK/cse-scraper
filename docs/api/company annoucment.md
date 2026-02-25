# cse-scraper
scraping the data from the cse.lk api

## Setup

```bash
pip install -r requirements.txt
```

## Scrape announcements by company

This script pulls announcements per company symbol from the CSE API endpoint:

`https://www.cse.lk/api/getAnnouncementByCompany?symbol=...&fromDate=YYYY-MM-DD&toDate=YYYY-MM-DD`

Run:

```bash
python scrape_company_announcements.py --csv "company-symbols copy.csv" --from 2020-01-28 --to 2026-01-28
```

Output:

- `company-announcements/<run-date>/<symbol>_<from>_<to>.json`
- `company-announcements/<run-date>/summary_<run-date>.json`
