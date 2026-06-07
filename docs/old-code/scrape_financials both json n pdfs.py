import requests
import os
import json
from datetime import datetime

API_URL = "https://www.cse.lk/api/financials"
OUTPUT_DIR = "financial-reports"
SYMBOLS_FILE = "company-symbols.txt"

def load_symbols():
    """Load company symbols from file."""
    with open(SYMBOLS_FILE, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def fetch_financials(symbol):
    """Fetch financial data for a given company symbol."""
    params = {"symbol": symbol}
    print(f"Fetching financials for: {symbol}")
    
    try:
        response = requests.post(API_URL, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

def save_json(data, symbol):
    """Save financial data to JSON file."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # Create a sanitized filename from symbol
    safe_symbol = symbol.replace('.', '_')
    timestamp = datetime.now().strftime("%Y-%m-%d")
    filename = f"{safe_symbol}_financials_{timestamp}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Saved: {filepath}")
    return filepath

def download_pdf(path, symbol, report_type, index):
    """Download PDF file from CSE server."""
    if not path:
        return
    
    base_url = "https://cdn.cse.lk/"
    pdf_url = base_url + path
    
    # Create directory structure
    pdf_dir = os.path.join(OUTPUT_DIR, "pdfs", symbol.replace('.', '_'))
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)
    
    # Extract filename or create one
    filename = f"{report_type}_{index}_{os.path.basename(path)}"
    filepath = os.path.join(pdf_dir, filename)
    
    try:
        print(f"  Downloading: {filename}")
        response = requests.get(pdf_url)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        print(f"  Saved: {filepath}")
    except Exception as e:
        print(f"  Error downloading {filename}: {e}")

def process_symbol(symbol, download_pdfs=False):
    """Process a single company symbol."""
    data = fetch_financials(symbol)
    
    if not data:
        return
    
    # Save JSON response
    save_json(data, symbol)
    
    # Optionally download PDFs
    if download_pdfs:
        print(f"Downloading PDFs for {symbol}...")
        
        # Download annual reports
        for idx, item in enumerate(data.get('infoAnnualData', []), 1):
            download_pdf(item.get('path'), symbol, 'annual', idx)
        
        # Download quarterly reports
        for idx, item in enumerate(data.get('infoQuarterlyData', []), 1):
            download_pdf(item.get('path'), symbol, 'quarterly', idx)
        
        # Download other documents (press releases, etc.)
        for idx, item in enumerate(data.get('infoOtherData', []), 1):
            download_pdf(item.get('path'), symbol, 'other', idx)

def main():
    """Main execution function."""
    print("Starting financial data scraper...")
    print(f"Output directory: {OUTPUT_DIR}")
    
    # Load symbols
    symbols = load_symbols()
    print(f"Loaded {len(symbols)} company symbols")
    
    # Ask user if they want to download PDFs
    download_pdfs = input("\nDownload PDF files? (y/n): ").lower().strip() == 'y'
    
    # Process each symbol
    for idx, symbol in enumerate(symbols, 1):
        print(f"\n[{idx}/{len(symbols)}] Processing {symbol}")
        process_symbol(symbol, download_pdfs)
    
    print("\nFinished processing all symbols!")

if __name__ == "__main__":
    main()
