import requests
import json
import os
from datetime import datetime

# Read API endpoints from the txt file
API_FILE = 'api_endpoint_urls.txt'
OUTPUT_DIR = 'data'

def get_api_endpoints(file_path):
    endpoints = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and line.startswith('http'):
                url = line.split()[0]
                endpoints.append(url)
    return endpoints

def fetch_and_save_all(endpoints, output_dir):
    date_str = datetime.now().strftime('%Y-%m-%d')
    dated_dir = os.path.join(output_dir, date_str)
    if not os.path.exists(dated_dir):
        os.makedirs(dated_dir)
    for url in endpoints:
        try:
            response = requests.post(url)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            data = {'error': str(e)}
        # Create a safe filename from the endpoint
        endpoint_name = url.split('/')[-1] or url.split('/')[-2]
        filename = f'{endpoint_name}_{date_str}.json'
        filepath = os.path.join(dated_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'Saved: {filepath}')

def main():
    endpoints = get_api_endpoints(API_FILE)
    fetch_and_save_all(endpoints, OUTPUT_DIR)

if __name__ == '__main__':
    main()
