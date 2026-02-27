import os
import json
import csv
import re
import argparse
from datetime import datetime, timezone
import requests
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR_NAME = "financials-json"
OUTPUT_BASE_DIR = r"C:\\Users\\Anuhas\\Documents\\datasets\\CSE company reports"
AUDIT_PREFIX = "rearrange_financial_pdfs_audit_"
AUDIT_SUFFIX = ".csv"

STATUS_DOWNLOADED = "downloaded"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"

MANIFEST_FILE_NAME = "download_manifest.csv"
MANIFEST_FIELDS = [
    "json_path_key",
    "raw_path",
    "symbol",
    "report_type",
    "index",
    "file_text",
    "output_filename",
    "output_path",
    "status",
    "source",
    "timestamp",
    "note",
]

def resolve_input_dir():
    """Resolve financial JSON input directory from common locations."""
    candidate_dirs = [
        os.path.join(os.getcwd(), INPUT_DIR_NAME),
        os.path.join(BASE_DIR, INPUT_DIR_NAME),
    ]

    for candidate in candidate_dirs:
        if os.path.isdir(candidate):
            return candidate

    # Default to cwd location if none exist yet
    return candidate_dirs[0]

def get_json_files(input_dir):
    """Get all JSON files from the financial-reports directory."""
    json_files = []
    for file in os.listdir(input_dir):
        if file.endswith('.json') and '_financials_' in file:
            json_files.append(os.path.join(input_dir, file))
    return json_files

def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def normalize_json_pdf_path(path):
    if not path:
        return None
    cleaned = str(path).strip().replace("\\", "/")
    cleaned = cleaned.split("?", 1)[0].strip()
    if not cleaned:
        return None
    return cleaned.lower()

def get_manifest_path(manifest_path=None):
    if manifest_path:
        return manifest_path
    return os.path.join(BASE_DIR, MANIFEST_FILE_NAME)

def ensure_manifest_file(manifest_path):
    if os.path.exists(manifest_path):
        return
    with open(manifest_path, "w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()

def load_manifest_index(manifest_path):
    index = set()
    if not os.path.exists(manifest_path):
        return index

    try:
        with open(manifest_path, "r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                key = normalize_json_pdf_path(row.get("json_path_key"))
                if key:
                    index.add(key)
    except Exception as e:
        print(f"Warning: unable to read manifest CSV {manifest_path}: {e}")

    return index

def append_manifest_row(
    manifest_path,
    manifest_index,
    path,
    symbol,
    report_type,
    index,
    file_text,
    output_filename,
    output_path,
    status,
    source,
    note="",
):
    key = normalize_json_pdf_path(path)
    if not key:
        return False

    if key in manifest_index:
        return False

    ensure_manifest_file(manifest_path)
    row = {
        "json_path_key": key,
        "raw_path": str(path or ""),
        "symbol": str(symbol or ""),
        "report_type": str(report_type or ""),
        "index": str(index or ""),
        "file_text": str(file_text or ""),
        "output_filename": str(output_filename or ""),
        "output_path": str(output_path or ""),
        "status": str(status or ""),
        "source": str(source or ""),
        "timestamp": utc_now_iso(),
        "note": str(note or ""),
    }

    with open(manifest_path, "a", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=MANIFEST_FIELDS)
        writer.writerow(row)

    manifest_index.add(key)
    return True

def extract_audit_timestamp(audit_path: Path):
    """Extract sortable timestamp from audit filename if present."""
    match = re.search(r"(\d{8}_\d{6})", audit_path.name)
    if not match:
        return None
    return match.group(1)

def find_latest_audit_csv():
    """Find latest rearrange audit CSV, preferring timestamp in filename."""
    audit_files = [
        path for path in Path(BASE_DIR).glob(f"{AUDIT_PREFIX}*{AUDIT_SUFFIX}")
        if path.is_file()
    ]
    if not audit_files:
        return None

    with_ts = [(extract_audit_timestamp(path), path) for path in audit_files]
    with_valid_ts = [(ts, path) for ts, path in with_ts if ts is not None]

    if with_valid_ts:
        return max(with_valid_ts, key=lambda item: item[0])[1]

    return max(audit_files, key=lambda path: path.stat().st_mtime)

def _candidate_names_from_value(value):
    """Build normalized PDF basename candidates from a CSV cell value."""
    if not value:
        return set()

    cleaned = str(value).strip().strip('"').replace("\\", "/")
    if not cleaned:
        return set()

    cleaned = cleaned.split("?", 1)[0].strip()
    if not cleaned.lower().endswith(".pdf"):
        return set()

    basename = os.path.basename(cleaned).strip()
    if not basename:
        return set()

    return {basename.lower()}

def load_downloaded_pdf_index_from_latest_audit():
    """
    Load normalized PDF basenames from latest audit CSV.
    Returns: (set_of_pdf_basenames, latest_audit_path_or_none)
    """
    latest_audit = find_latest_audit_csv()
    if latest_audit is None:
        return set(), None

    known_pdfs = set()
    try:
        with open(latest_audit, "r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            if reader.fieldnames:
                row_has_known_columns = {name.strip().lower() for name in reader.fieldnames}
            else:
                row_has_known_columns = set()

            preferred_columns = [name for name in ["old_path", "new_path"] if name in row_has_known_columns]

            for row in reader:
                if preferred_columns:
                    for column_name in preferred_columns:
                        for name in _candidate_names_from_value(row.get(column_name, "")):
                            known_pdfs.add(name)
                else:
                    for value in row.values():
                        for name in _candidate_names_from_value(value):
                            known_pdfs.add(name)
    except Exception as e:
        print(f"Warning: unable to read audit CSV {latest_audit}: {e}")
        return set(), str(latest_audit)

    return known_pdfs, str(latest_audit)

def load_downloaded_pdf_index_from_output_dir():
    """
    Load normalized PDF basenames from existing output directory.
    Returns a set of lowercase pdf basenames.
    """
    output_dir = Path(OUTPUT_BASE_DIR)
    if not output_dir.exists() or not output_dir.is_dir():
        return set()

    known_pdfs = set()
    for path in output_dir.rglob("*.pdf"):
        if path.is_file():
            known_pdfs.add(path.name.lower())
    return known_pdfs

def bootstrap_manifest_from_existing_files(json_files, manifest_path, manifest_index):
    added = 0
    total_entries = 0

    for json_filepath in json_files:
        symbol = extract_symbol_from_filename(json_filepath)
        try:
            with open(json_filepath, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except Exception:
            continue

        for report_key, report_type in [
            ('infoAnnualData', 'annual'),
            ('infoQuarterlyData', 'quarterly'),
            ('infoOtherData', 'other'),
        ]:
            records = data.get(report_key, []) or []
            for idx, item in enumerate(records, 1):
                total_entries += 1
                path = item.get('path')
                if not path:
                    continue

                path_key = normalize_json_pdf_path(path)
                if not path_key or path_key in manifest_index:
                    continue

                filename = build_output_filename(symbol, report_type, idx, path, item.get('fileText'))
                output_path = os.path.join(OUTPUT_BASE_DIR, symbol, filename)
                if os.path.exists(output_path):
                    wrote = append_manifest_row(
                        manifest_path=manifest_path,
                        manifest_index=manifest_index,
                        path=path,
                        symbol=symbol,
                        report_type=report_type,
                        index=idx,
                        file_text=item.get('fileText'),
                        output_filename=filename,
                        output_path=output_path,
                        status='bootstrapped',
                        source='existing_output_file',
                        note='Expected output file already existed',
                    )
                    if wrote:
                        added += 1

    return added, total_entries

def build_output_filename(symbol, report_type, index, path, file_text=None):
    """Build output PDF filename from JSON metadata."""
    base_symbol = symbol.split('.')[0].split('_')[0]

    if file_text:
        safe_filename = "".join(c if c.isalnum() or c in (' ', '-', '_', '.') else '_' for c in file_text)
        safe_filename = safe_filename.strip()
        safe_filename = " ".join(safe_filename.split())
        return f"{base_symbol} {safe_filename}.pdf"

    source_basename = os.path.basename(str(path).replace("\\", "/").split("?", 1)[0])
    return f"{base_symbol} {report_type}_{index}_{source_basename}"

def extract_symbol_from_filename(filename):
    """Extract company symbol from JSON filename."""
    # Format: SYMBOL_financials_DATE.json
    basename = os.path.basename(filename)
    parts = basename.split('_financials_')
    if len(parts) > 0:
        return parts[0]
    return "UNKNOWN"

def download_pdf(
    path,
    symbol,
    report_type,
    index,
    file_text=None,
    audit_pdf_index=None,
    manifest_path=None,
    manifest_index=None,
):
    """Download PDF file from CSE server."""
    if not path:
        return STATUS_SKIPPED

    path_key = normalize_json_pdf_path(path)
    if manifest_index is not None and path_key and path_key in manifest_index:
        print("  Skipping (already in manifest)")
        return STATUS_SKIPPED
    
    base_url = "https://cdn.cse.lk/"
    pdf_url = base_url + path
    
    # Create directory structure
    pdf_dir = os.path.join(OUTPUT_BASE_DIR, symbol)
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)

    filename = build_output_filename(symbol, report_type, index, path, file_text)
    
    filepath = os.path.join(pdf_dir, filename)

    source_pdf_name = os.path.basename(str(path).replace("\\", "/").split("?", 1)[0]).lower()
    target_pdf_name = filename.lower()

    # Skip if tracked in latest audit (prevents re-downloading even if local file moved/renamed)
    if audit_pdf_index and (source_pdf_name in audit_pdf_index or target_pdf_name in audit_pdf_index):
        print(f"  Skipping (in latest audit): {filename}")
        if manifest_path and manifest_index is not None:
            append_manifest_row(
                manifest_path=manifest_path,
                manifest_index=manifest_index,
                path=path,
                symbol=symbol,
                report_type=report_type,
                index=index,
                file_text=file_text,
                output_filename=filename,
                output_path=filepath,
                status='bootstrapped',
                source='latest_audit_index',
                note='Skipped due to audit/output index match',
            )
        return STATUS_SKIPPED
    
    # Skip if already downloaded
    if os.path.exists(filepath):
        print(f"  Already exists: {filename}")
        if manifest_path and manifest_index is not None:
            append_manifest_row(
                manifest_path=manifest_path,
                manifest_index=manifest_index,
                path=path,
                symbol=symbol,
                report_type=report_type,
                index=index,
                file_text=file_text,
                output_filename=filename,
                output_path=filepath,
                status='bootstrapped',
                source='existing_output_file',
                note='Skipped because expected file existed',
            )
        return STATUS_SKIPPED
    
    try:
        print(f"  Downloading: {filename}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        response = requests.get(pdf_url, headers=headers, timeout=60)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        print(f"  Saved: {filepath}")
        if manifest_path and manifest_index is not None:
            append_manifest_row(
                manifest_path=manifest_path,
                manifest_index=manifest_index,
                path=path,
                symbol=symbol,
                report_type=report_type,
                index=index,
                file_text=file_text,
                output_filename=filename,
                output_path=filepath,
                status=STATUS_DOWNLOADED,
                source='download',
                note='Downloaded successfully',
            )
        return STATUS_DOWNLOADED
    except Exception as e:
        print(f"  Error downloading {filename}: {e}")
        return STATUS_FAILED

def process_json_file(json_filepath, audit_pdf_index=None, manifest_path=None, manifest_index=None):
    """Process a single JSON file and download its PDFs."""
    print(f"\nProcessing: {os.path.basename(json_filepath)}")
    
    # Extract symbol from filename
    symbol = extract_symbol_from_filename(json_filepath)
    print(f"Symbol: {symbol}")
    
    # Load JSON data
    try:
        with open(json_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return
    
    downloaded_count = 0
    skipped_count = 0
    failed_count = 0
    
    # Download annual reports
    annual_data = data.get('infoAnnualData', [])
    if annual_data:
        print(f"  Annual reports: {len(annual_data)}")
        for idx, item in enumerate(annual_data, 1):
            status = download_pdf(
                item.get('path'),
                symbol,
                'annual',
                idx,
                item.get('fileText'),
                audit_pdf_index,
                manifest_path,
                manifest_index,
            )
            if status == STATUS_DOWNLOADED:
                downloaded_count += 1
            elif status == STATUS_SKIPPED:
                skipped_count += 1
            else:
                failed_count += 1

    # Download quarterly reports
    quarterly_data = data.get('infoQuarterlyData', [])
    if quarterly_data:
        print(f"  Quarterly reports: {len(quarterly_data)}")
        for idx, item in enumerate(quarterly_data, 1):
            status = download_pdf(
                item.get('path'),
                symbol,
                'quarterly',
                idx,
                item.get('fileText'),
                audit_pdf_index,
                manifest_path,
                manifest_index,
            )
            if status == STATUS_DOWNLOADED:
                downloaded_count += 1
            elif status == STATUS_SKIPPED:
                skipped_count += 1
            else:
                failed_count += 1

    # Download other documents
    other_data = data.get('infoOtherData', [])
    if other_data:
        print(f"  Other documents: {len(other_data)}")
        for idx, item in enumerate(other_data, 1):
            status = download_pdf(
                item.get('path'),
                symbol,
                'other',
                idx,
                item.get('fileText'),
                audit_pdf_index,
                manifest_path,
                manifest_index,
            )
            if status == STATUS_DOWNLOADED:
                downloaded_count += 1
            elif status == STATUS_SKIPPED:
                skipped_count += 1
            else:
                failed_count += 1
    
    print(f"  Downloaded: {downloaded_count} files")
    print(f"  Skipped: {skipped_count} files")
    if failed_count:
        print(f"  Failed: {failed_count} files")

    return downloaded_count, skipped_count, failed_count

def parse_args():
    parser = argparse.ArgumentParser(description="Download financial PDFs from financial JSON files")
    parser.add_argument(
        "--manifest-path",
        default=None,
        help="Path to persistent manifest CSV (default: financial data/download_manifest.csv)",
    )
    parser.add_argument(
        "--bootstrap-manifest-only",
        action="store_true",
        help="Only seed manifest from already existing expected output files and exit",
    )
    return parser.parse_args()

def main():
    """Main execution function."""
    args = parse_args()

    input_dir = resolve_input_dir()
    audit_pdf_index, latest_audit = load_downloaded_pdf_index_from_latest_audit()
    output_pdf_index = load_downloaded_pdf_index_from_output_dir()
    combined_skip_index = set(audit_pdf_index)
    combined_skip_index.update(output_pdf_index)
    manifest_path = get_manifest_path(args.manifest_path)
    manifest_index = load_manifest_index(manifest_path)

    print("Starting PDF downloader...")
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {OUTPUT_BASE_DIR}")
    print(f"Manifest CSV: {manifest_path}")
    print(f"Manifest index entries: {len(manifest_index)}")
    if latest_audit:
        print(f"Latest audit CSV: {latest_audit}")
        print(f"Audit index entries: {len(audit_pdf_index)}")
    else:
        print("Latest audit CSV: not found")
    print(f"Output-dir index entries: {len(output_pdf_index)}")
    print(f"Combined skip index entries: {len(combined_skip_index)}")

    if not os.path.isdir(input_dir):
        print(f"Input directory does not exist: {input_dir}")
        return
    
    # Get all JSON files
    json_files = get_json_files(input_dir)
    print(f"\nFound {len(json_files)} JSON files")
    
    if not json_files:
        print("No JSON files found. Run scrape_financial_json.py first.")
        return

    bootstrap_added, bootstrap_scanned = bootstrap_manifest_from_existing_files(
        json_files=json_files,
        manifest_path=manifest_path,
        manifest_index=manifest_index,
    )
    print(f"Bootstrapped manifest entries: {bootstrap_added} (scanned {bootstrap_scanned} JSON entries)")

    if args.bootstrap_manifest_only:
        print("Bootstrap-only mode completed.")
        return
    
    # Process each JSON file
    total_downloads = 0
    total_skipped = 0
    total_failed = 0
    for idx, json_file in enumerate(json_files, 1):
        print(f"\n[{idx}/{len(json_files)}]")
        downloaded, skipped, failed = process_json_file(
            json_file,
            combined_skip_index,
            manifest_path,
            manifest_index,
        )
        total_downloads += downloaded
        total_skipped += skipped
        total_failed += failed
    
    print(f"\n{'='*50}")
    print(f"Finished! Total PDFs downloaded: {total_downloads}")
    print(f"Total PDFs skipped: {total_skipped}")
    if total_failed:
        print(f"Total PDFs failed: {total_failed}")
    print(f"Manifest index entries (final): {len(manifest_index)}")

if __name__ == "__main__":
    main()


    