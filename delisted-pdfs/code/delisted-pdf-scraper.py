import os
import json
import requests
import logging
from datetime import datetime

# --- Dynamic Directory Configuration ---
# This automatically resolves paths based on the script's location inside the "code" folder
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) # Moves up one level to "financials-json"

INPUT_JSON_DIR = os.path.join(PROJECT_ROOT, "json")
OUTPUT_PDF_DIR = os.path.join(PROJECT_ROOT, "pdfs")

# --- Network Configuration ---
BASE_URL = "https://cdn.cse.lk/"

def get_base_ticker(filename):
    """Extracts the base ticker (e.g., ABAN) from formats like ABAN.N0000_financials..."""
    raw_symbol = filename.split('_financials_')[0]
    # Split by '.' or '_' to isolate the primary 4-letter ticker
    base_ticker = raw_symbol.replace('.', '_').split('_')[0]
    return base_ticker

def format_report_date(item):
    """Converts the JSON timestamp into a clean YYYY-MM-DD string."""
    # manualDate usually represents the actual period end date (e.g., March 31)
    # If it's missing, we fall back to the uploadedDate
    target_ms = item.get('manualDate') or item.get('uploadedDate')
    if target_ms:
        return datetime.fromtimestamp(target_ms / 1000).strftime('%Y-%m-%d')
    return "UNKNOWN_DATE"

def download_pdf(path, base_ticker, category, report_date, logger):
    """Download the PDF using the category subfolder structure."""
    if not path:
        return

    pdf_url = BASE_URL + path
    
    # Create the category-specific directory: financials-json/pdfs/[TICKER]/[CATEGORY]/
    category_dir = os.path.join(OUTPUT_PDF_DIR, base_ticker, category)
    if not os.path.exists(category_dir):
        os.makedirs(category_dir)

    # Construct the requested filename: e.g., ABAN_2025-12-31_quarterly.pdf
    filename = f"{base_ticker}_{report_date}_{category}.pdf"
    filepath = os.path.join(category_dir, filename)

    try:
        logger.info(f"  -> Downloading: {filename} into {category}/")
        response = requests.get(pdf_url, stream=True, timeout=15)
        response.raise_for_status() 

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info("     [Success] Saved to disk.")
        
    except requests.exceptions.RequestException as e:
        logger.info(f"     [Error] Failed to download: {e}")

def process_json_file(filepath, logger):
    """Parse JSON metadata arrays and route them to the downloader."""
    filename = os.path.basename(filepath)
    base_ticker = get_base_ticker(filename)

    # Safely load JSON data
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.info(f"Error reading {filename}: {e}")
        return

    # Map the target arrays to their category strings
    report_categories = {
        'infoAnnualData': 'annual',
        'infoQuarterlyData': 'quarterly',
        'infoOtherData': 'other'
    }

    # Iterate through the arrays without any date filtering
    for key, category in report_categories.items():
        for item in data.get(key, []):
            path = item.get('path')
            report_date = format_report_date(item)
            
            download_pdf(path, base_ticker, category, report_date, logger)

def setup_logging():
    """Configure logging to write to both console and a log file."""
    log_file = os.path.join(SCRIPT_DIR, "pdf-scrape-log.txt")
    
    # Create logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    logger.handlers = []
    
    # File handler
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter with timestamp
    formatter = logging.Formatter('%(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def main():
    """Main execution block."""
    logger = setup_logging()
    logger.info(f"Script started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("Starting PDF Downloader Pipeline...")
    
    if not os.path.exists(INPUT_JSON_DIR):
        logger.info(f"Error: Input directory '{INPUT_JSON_DIR}' not found.")
        logger.info("Ensure this script is running from inside the 'code' folder.")
        return

    if not os.path.exists(OUTPUT_PDF_DIR):
        os.makedirs(OUTPUT_PDF_DIR)
        logger.info(f"Created new output directory: '{OUTPUT_PDF_DIR}'")

    json_files = [f for f in os.listdir(INPUT_JSON_DIR) if f.endswith('.json')]
    
    if not json_files:
        logger.info(f"No JSON files found in '{INPUT_JSON_DIR}'.")
        return

    logger.info(f"Found {len(json_files)} JSON files.")
    logger.info("Scanning for all historical reports...")

    for idx, file in enumerate(json_files, 1):
        logger.info(f"\n[{idx}/{len(json_files)}] Evaluating {file}...")
        filepath = os.path.join(INPUT_JSON_DIR, file)
        process_json_file(filepath, logger)
        
    logger.info("\nBatch PDF download process complete.")

if __name__ == "__main__":
    main()