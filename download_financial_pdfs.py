import os
import json
import requests
import time
import random
from pathlib import Path

INPUT_DIR = "financial-reports"
OUTPUT_BASE_DIR = r"C:\\Users\\Anuhas\\Documents\\datasets\\CSE company reports"

def get_json_files():
    """Get all JSON files from the financial-reports directory."""
    json_files = []
    for file in os.listdir(INPUT_DIR):
        if file.endswith('.json') and '_financials_' in file:
            json_files.append(os.path.join(INPUT_DIR, file))
    return json_files

def extract_symbol_from_filename(filename):
    """Extract company symbol from JSON filename."""
    # Format: SYMBOL_financials_DATE.json
    basename = os.path.basename(filename)
    parts = basename.split('_financials_')
    if len(parts) > 0:
        return parts[0]
    return "UNKNOWN"

def download_pdf(path, symbol, report_type, index, file_text=None):
    """Download PDF file from CSE server."""
    if not path:
        return False
    
    base_url = "https://cdn.cse.lk/"
    pdf_url = base_url + path
    
    # Create directory structure
    pdf_dir = os.path.join(OUTPUT_BASE_DIR, symbol)
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)
    
    # Create filename from fileText or fallback to default naming
    # Extract base symbol (e.g., ABAN from ABAN.N0000 or ABAN_N0000)
    base_symbol = symbol.split('.')[0].split('_')[0]
    
    if file_text:
        # Sanitize fileText to create a valid filename
        safe_filename = "".join(c if c.isalnum() or c in (' ', '-', '_', '.') else '_' for c in file_text)
        safe_filename = safe_filename.strip().replace('  ', ' ')
        filename = f"{base_symbol} {safe_filename}.pdf"
    else:
        filename = f"{base_symbol} {report_type}_{index}_{os.path.basename(path)}"
    
    filepath = os.path.join(pdf_dir, filename)
    
    # Skip if already downloaded
    if os.path.exists(filepath):
        print(f"  Already exists: {filename}")
        return True
    
    try:
        print(f"  Downloading: {filename}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        response = requests.get(pdf_url, headers=headers)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        print(f"  Saved: {filepath}")
        return True
    except Exception as e:
        print(f"  Error downloading {filename}: {e}")
        return False

def process_json_file(json_filepath):
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
    
    download_count = 0
    
    # Download annual reports
    annual_data = data.get('infoAnnualData', [])
    if annual_data:
        print(f"  Annual reports: {len(annual_data)}")
        for idx, item in enumerate(annual_data, 1):
            if download_pdf(item.get('path'), symbol, 'annual', idx, item.get('fileText')):
                download_count += 1

    # Download quarterly reports
    quarterly_data = data.get('infoQuarterlyData', [])
    if quarterly_data:
        print(f"  Quarterly reports: {len(quarterly_data)}")
        for idx, item in enumerate(quarterly_data, 1):
            if download_pdf(item.get('path'), symbol, 'quarterly', idx, item.get('fileText')):
                download_count += 1

    # Download other documents
    other_data = data.get('infoOtherData', [])
    if other_data:
        print(f"  Other documents: {len(other_data)}")
        for idx, item in enumerate(other_data, 1):
            if download_pdf(item.get('path'), symbol, 'other', idx, item.get('fileText')):
                download_count += 1
    
    print(f"  Downloaded: {download_count} files")
    return download_count

def main():
    """Main execution function."""
    print("Starting PDF downloader...")
    print(f"Input directory: {INPUT_DIR}")
    print(f"Output directory: {OUTPUT_BASE_DIR}")
    
    # Get all JSON files
    json_files = get_json_files()
    print(f"\nFound {len(json_files)} JSON files")
    
    if not json_files:
        print("No JSON files found. Run scrape_financial_json.py first.")
        return
    
    # Process each JSON file
    total_downloads = 0
    for idx, json_file in enumerate(json_files, 1):
        print(f"\n[{idx}/{len(json_files)}]")
        count = process_json_file(json_file)
        if count:
            total_downloads += count
    
    print(f"\n{'='*50}")
    print(f"Finished! Total PDFs downloaded: {total_downloads}")

if __name__ == "__main__":
    main()


    