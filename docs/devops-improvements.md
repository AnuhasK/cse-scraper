# 📈 CSE Daily Data Scraper (DevOps-Enhanced)

## 🚀 Overview

This project is an automated data pipeline that scrapes daily stock market data from the Colombo Stock Exchange (CSE), processes it, and stores it in a structured format for analysis.

The system is designed using DevOps principles to ensure:

* Reliability
* Observability
* Scalability
* Maintainability

---

## ⚙️ Features

### ✅ Automated Data Scraping

* Runs daily using GitHub Actions
* Fetches latest CSE stock data

### ✅ Holiday Awareness

* Skips execution on market holidays
* Prevents unnecessary runs and invalid data

### ✅ Data Pipeline (Raw → Processed)

* **Raw Layer:** Stores daily scraped data
* **Processed Layer:** Maintains a clean, unified dataset for analysis

### ✅ Data Deduplication

* Prevents duplicate entries using unique keys (date + stock symbol)

### ✅ Logging System

* Tracks execution status and errors
* Supports debugging and monitoring

### ✅ Notifications

* Alerts on failures or anomalies
* Can be integrated with email or Slack

---

## 🏗️ Project Structure

```
repo/
 ├── .github/workflows/     # CI/CD pipelines
 ├── src/                   # Scraper and processing logic
 ├── data/
 │    ├── raw/              # Daily scraped data
 │    ├── processed/        # Aggregated dataset
 ├── logs/                  # Application logs
 ├── config/                # Config files (holidays, settings)
 └── tests/                 # Validation and test scripts
```

---

## 🔄 Workflow Pipeline

```
GitHub Actions Trigger
        ↓
Check Holiday
        ↓
Run Scraper
        ↓
Validate Data
        ↓
Store Raw Data
        ↓
Update Master Dataset
        ↓
Log Results
        ↓
Send Alerts (if needed)
```

---

## 📅 Holiday Handling

The scraper uses a predefined holiday list:

Example:

```json
["2026-01-14", "2026-04-13", "2026-04-14"]
```

If the current date matches a holiday:

* The pipeline exits early
* No data is scraped

---

## 📊 Data Storage Strategy

### Raw Data

* Stored daily
* Format: JSON/CSV
* Example:

```
data/raw/2026-04-30.json
```

### Processed Data

* Aggregated dataset for analysis
* Example:

```
data/processed/stocks_master.csv
```

---

## 🧾 Logging

Logs are stored in:

```
logs/scraper.log
```

Log levels:

* INFO → Normal execution
* WARNING → Suspicious data
* ERROR → Failures

---

## 🔔 Notifications

Alerts are triggered when:

* Scraper fails
* Data is missing or invalid
* Pipeline errors occur

---

## 🧪 Data Validation

Before saving:

* Check for empty datasets
* Validate required fields
* Detect abnormal values

---

## 🔐 Configuration

All configurable values are stored in config files:

Example:

```yaml
scraper:
  run_time: "09:00"
  retry_count: 3
  email_alerts: true
```

---

## 🐳 Future Improvements

* Docker containerization
* Database integration (PostgreSQL)
* API layer for data access
* Monitoring (Prometheus + Grafana)
* Event-driven pipeline

---

## 🧠 DevOps Concepts Applied

* CI/CD pipelines
* Idempotent data processing
* Logging and observability
* Configuration management
* Fault tolerance and retries

