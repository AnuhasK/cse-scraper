import argparse
import csv
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DEFAULT_PDF_DIR = r"C:\\Users\\Anuhas\\Documents\\datasets\\CSE company reports"
BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = BASE_DIR.parent
DEFAULT_JSON_DIR_CANDIDATES = [
    WORKSPACE_ROOT / "financials-json",
    BASE_DIR / "financials-json",
]


@dataclass
class ReportRecord:
    symbol: str
    category: str
    date_iso: str
    path_norm: str
    path_base: str
    file_text_norm: str


def normalize_path(value: Optional[str]) -> str:
    if not value:
        return ""

    text = value.strip().replace("\\", "/")
    if text.startswith("upload_report_file/"):
        text = "cmt/" + text
    return text.lower()


def normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value.strip().lower())


def extract_symbol_from_json_filename(name: str) -> str:
    parts = name.split("_financials_")
    return parts[0].strip().upper() if parts else ""


def to_date_iso(timestamp_ms: Optional[int]) -> Optional[str]:
    if not timestamp_ms:
        return None
    try:
        return datetime.fromtimestamp(int(timestamp_ms) / 1000, UTC).strftime("%Y-%m-%d")
    except (ValueError, OSError, OverflowError):
        return None


def resolve_json_dir(user_value: Optional[str]) -> Path:
    if user_value:
        candidate = Path(user_value)
        if candidate.is_dir():
            return candidate
        raise FileNotFoundError(f"JSON directory not found: {candidate}")

    for candidate in DEFAULT_JSON_DIR_CANDIDATES:
        if candidate.is_dir():
            return candidate

    raise FileNotFoundError("Could not find financial JSON directory. Use --json-dir.")


def load_report_records(json_dir: Path) -> List[ReportRecord]:
    records: List[ReportRecord] = []

    for json_file in json_dir.glob("*_financials_*.json"):
        symbol = extract_symbol_from_json_filename(json_file.name)
        if not symbol:
            continue

        try:
            with json_file.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            continue

        for category_key, category_name in (("infoAnnualData", "annual"), ("infoQuarterlyData", "quarterly")):
            for item in data.get(category_key, []):
                date_iso = to_date_iso(item.get("manualDate"))
                if not date_iso:
                    continue

                path_norm = normalize_path(item.get("path"))
                path_base = os.path.basename(path_norm)
                file_text_norm = normalize_text(item.get("fileText"))

                records.append(
                    ReportRecord(
                        symbol=symbol,
                        category=category_name,
                        date_iso=date_iso,
                        path_norm=path_norm,
                        path_base=path_base,
                        file_text_norm=file_text_norm,
                    )
                )

    return records


def build_indexes(records: List[ReportRecord]):
    by_path_base: Dict[str, List[ReportRecord]] = defaultdict(list)
    by_symbol_date_category: Dict[Tuple[str, str, str], List[ReportRecord]] = defaultdict(list)
    by_symbol_date: Dict[Tuple[str, str], List[ReportRecord]] = defaultdict(list)

    for rec in records:
        if rec.path_base:
            by_path_base[rec.path_base].append(rec)

        by_symbol_date_category[(rec.symbol, rec.date_iso, rec.category)].append(rec)
        by_symbol_date[(rec.symbol, rec.date_iso)].append(rec)

    return by_path_base, by_symbol_date_category, by_symbol_date


def parse_date_from_filename(filename: str) -> Optional[str]:
    name = Path(filename).stem

    numeric_patterns = [
        r"(?<!\d)(\d{4})[-_.](\d{2})[-_.](\d{2})(?!\d)",
        r"(?<!\d)(\d{2})[-_.](\d{2})[-_.](\d{4})(?!\d)",
        r"(?<!\d)(\d{8})(?!\d)",
    ]

    for pattern in numeric_patterns:
        for match in re.finditer(pattern, name):
            try:
                if len(match.groups()) == 3:
                    a, b, c = match.groups()
                    if len(a) == 4:
                        dt = datetime(int(a), int(b), int(c))
                    else:
                        dt = datetime(int(c), int(b), int(a))
                    return dt.strftime("%Y-%m-%d")
                if len(match.groups()) == 1:
                    compact = match.group(1)
                    dt = datetime.strptime(compact, "%Y%m%d")
                    return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

    month_name_pattern = re.compile(
        r"(?<!\d)(\d{1,2})(?:st|nd|rd|th)?\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{4})(?!\d)",
        re.IGNORECASE,
    )
    match = month_name_pattern.search(name)
    if match:
        day, month_name, year = match.groups()
        month_key = month_name[:3].lower()
        month_lookup = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }
        try:
            dt = datetime(int(year), month_lookup[month_key], int(day))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None

    return None


def infer_category_from_filename(filename: str) -> Optional[str]:
    text = filename.lower()

    annual_keywords = ["annual", "audited", "year ended", "annual report"]
    quarterly_keywords = [
        "quarterly",
        "quarter",
        "quartely",
        "quaterly",
        "interim",
        "3 months",
        "6 months",
        "9 months",
    ]

    if any(token in text for token in annual_keywords):
        return "annual"
    if any(token in text for token in quarterly_keywords):
        return "quarterly"
    return None


def infer_symbol_from_filename(filename: str) -> Optional[str]:
    stem = Path(filename).stem
    m = re.match(r"^([A-Za-z]{2,10})(?:[\s_.\-]|$)", stem)
    if m:
        return m.group(1).upper()
    return None


def sanitize_symbol(symbol: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9]", "", symbol.upper())
    return safe or "UNKNOWN"


def unique_destination(base_path: Path) -> Path:
    if not base_path.exists():
        return base_path

    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent

    counter = 2
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def choose_record_for_file(
    pdf_path: Path,
    by_path_base: Dict[str, List[ReportRecord]],
    by_symbol_date_category: Dict[Tuple[str, str, str], List[ReportRecord]],
    by_symbol_date: Dict[Tuple[str, str], List[ReportRecord]],
) -> Tuple[Optional[ReportRecord], str]:
    path_base = pdf_path.name.lower()
    matches = by_path_base.get(path_base, [])
    if len(matches) == 1:
        return matches[0], "json_path_basename"

    inferred_symbol = infer_symbol_from_filename(pdf_path.name)
    inferred_date = parse_date_from_filename(pdf_path.name)
    inferred_category = infer_category_from_filename(pdf_path.name)

    if inferred_symbol and inferred_date and inferred_category:
        key = (inferred_symbol, inferred_date, inferred_category)
        matches = by_symbol_date_category.get(key, [])
        if len(matches) == 1:
            return matches[0], "json_symbol_date_category"

    if inferred_symbol and inferred_date:
        matches = by_symbol_date.get((inferred_symbol, inferred_date), [])
        if len(matches) == 1:
            return matches[0], "json_symbol_date"

    if inferred_symbol and inferred_date and inferred_category:
        return ReportRecord(
            symbol=inferred_symbol,
            category=inferred_category,
            date_iso=inferred_date,
            path_norm="",
            path_base="",
            file_text_norm="",
        ), "filename_fallback"

    return None, "unmatched"


def collect_pdfs(pdf_root: Path, include_organized: bool = False) -> List[Path]:
    all_pdfs = [p for p in pdf_root.rglob("*.pdf") if p.is_file()]
    if include_organized:
        return all_pdfs

    filtered = []
    for path in all_pdfs:
        rel_parts = [part.lower() for part in path.relative_to(pdf_root).parts]
        if any(part in {"annual", "quarterly"} for part in rel_parts):
            continue
        filtered.append(path)
    return filtered


def write_audit_log(rows: List[Dict[str, str]], audit_file: Path) -> None:
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    with audit_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["old_path", "new_path", "status", "reason", "match_method"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def run_rearrangement(pdf_dir: Path, json_dir: Path, apply_changes: bool, include_organized: bool) -> int:
    records = load_report_records(json_dir)
    by_path_base, by_symbol_date_category, by_symbol_date = build_indexes(records)

    pdf_files = collect_pdfs(pdf_dir, include_organized=include_organized)
    if not pdf_files:
        print("No PDF files found to process.")
        return 0

    audit_rows: List[Dict[str, str]] = []
    renamed_count = 0
    unchanged_unknown = 0
    already_target = 0

    for pdf_path in pdf_files:
        record, match_method = choose_record_for_file(
            pdf_path,
            by_path_base,
            by_symbol_date_category,
            by_symbol_date,
        )

        if not record:
            unchanged_unknown += 1
            audit_rows.append(
                {
                    "old_path": str(pdf_path),
                    "new_path": "",
                    "status": "UNCHANGED_UNKNOWN",
                    "reason": "Could not classify using JSON or filename",
                    "match_method": match_method,
                }
            )
            continue

        safe_symbol = sanitize_symbol(record.symbol)
        target_root = pdf_dir / safe_symbol / record.category
        target_root.mkdir(parents=True, exist_ok=True)

        target_name = f"{safe_symbol}_{record.date_iso}_{record.category}.pdf"
        desired_path = target_root / target_name

        if pdf_path.resolve() == desired_path.resolve():
            already_target += 1
            audit_rows.append(
                {
                    "old_path": str(pdf_path),
                    "new_path": str(desired_path),
                    "status": "ALREADY_OK",
                    "reason": "Already in target location with target name",
                    "match_method": match_method,
                }
            )
            continue

        final_path = unique_destination(desired_path)

        if apply_changes:
            final_path.parent.mkdir(parents=True, exist_ok=True)
            pdf_path.rename(final_path)

        renamed_count += 1
        audit_rows.append(
            {
                "old_path": str(pdf_path),
                "new_path": str(final_path),
                "status": "RENAMED" if apply_changes else "WOULD_RENAME",
                "reason": "",
                "match_method": match_method,
            }
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audit_file = BASE_DIR / f"rearrange_financial_pdfs_audit_{timestamp}.csv"
    write_audit_log(audit_rows, audit_file)

    print("=" * 70)
    print(f"Mode: {'APPLY' if apply_changes else 'DRY-RUN'}")
    print(f"Include already organized files: {include_organized}")
    print(f"PDF directory: {pdf_dir}")
    print(f"JSON directory: {json_dir}")
    print(f"Total PDFs scanned: {len(pdf_files)}")
    print(f"Renamed/moved: {renamed_count}")
    print(f"Already OK: {already_target}")
    print(f"Unchanged unknown: {unchanged_unknown}")
    print(f"Audit log: {audit_file}")
    print("=" * 70)

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="One-time rearrangement of financial report PDFs into SYMBOL/annual or SYMBOL/quarterly folders with SYMBOL_DATE_TYPE names."
    )
    parser.add_argument(
        "--pdf-dir",
        default=DEFAULT_PDF_DIR,
        help="Root directory that currently contains downloaded PDFs.",
    )
    parser.add_argument(
        "--json-dir",
        default=None,
        help="Directory containing *_financials_*.json files. Defaults to detected financials-json.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply filesystem changes. If omitted, runs in dry-run mode.",
    )
    parser.add_argument(
        "--include-organized",
        action="store_true",
        help="Also process PDFs already under annual/quarterly folders (useful for migrating layout).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    pdf_dir = Path(args.pdf_dir)
    if not pdf_dir.is_dir():
        raise FileNotFoundError(f"PDF directory not found: {pdf_dir}")

    json_dir = resolve_json_dir(args.json_dir)
    return run_rearrangement(
        pdf_dir=pdf_dir,
        json_dir=json_dir,
        apply_changes=args.apply,
        include_organized=args.include_organized,
    )


if __name__ == "__main__":
    raise SystemExit(main())
