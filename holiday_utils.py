import json
import logging
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
HOLIDAY_DIR = BASE_DIR / 'holidays'
HOLIDAY_FILE = HOLIDAY_DIR / '2026-holidays.js'

logger = logging.getLogger(__name__)


def load_holidays(file_path=HOLIDAY_FILE):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error("Holiday file not found: %s", file_path)
        raise
    except json.JSONDecodeError as exc:
        logger.error("Holiday file is not valid JSON: %s", exc)
        raise

    if not isinstance(data, list):
        raise ValueError("Holiday file must contain a JSON array")

    holidays = set()
    for item in data:
        if isinstance(item, str):
            holidays.add(item)
        elif isinstance(item, dict) and 'date' in item:
            holidays.add(str(item['date']))
        else:
            raise ValueError("Holiday entries must be strings or objects with a 'date' field")

    return holidays


def today_str():
    return datetime.now().strftime('%Y-%m-%d')


def is_holiday(date_str, holidays=None):
    if holidays is None:
        holidays = load_holidays()
    return date_str in holidays
