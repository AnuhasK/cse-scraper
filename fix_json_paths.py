import os
import json

INPUT_DIR = "financial-reports"

def fix_path(path):
    """Fix path by ensuring it starts with 'cmt/upload_report_file/'"""
    if not path:
        return path
    
    # If path already starts with 'cmt/', return as is
    if path.startswith('cmt/'):
        return path
    
    # If path starts with 'upload_report_file/', add 'cmt/' prefix
    if path.startswith('upload_report_file/'):
        return 'cmt/' + path
    
    # Otherwise return as is (shouldn't happen based on your data)
    return path

def fix_json_file(filepath):
    """Fix all path fields in a JSON file"""
    print(f"Processing: {os.path.basename(filepath)}")
    
    try:
        # Read JSON file
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        changes_made = 0
        
        # Fix paths in infoAnnualData
        if 'infoAnnualData' in data:
            for item in data['infoAnnualData']:
                if 'path' in item:
                    old_path = item['path']
                    new_path = fix_path(old_path)
                    if old_path != new_path:
                        item['path'] = new_path
                        changes_made += 1
        
        # Fix paths in infoQuarterlyData
        if 'infoQuarterlyData' in data:
            for item in data['infoQuarterlyData']:
                if 'path' in item:
                    old_path = item['path']
                    new_path = fix_path(old_path)
                    if old_path != new_path:
                        item['path'] = new_path
                        changes_made += 1
        
        # Fix paths in infoOtherData
        if 'infoOtherData' in data:
            for item in data['infoOtherData']:
                if 'path' in item:
                    old_path = item['path']
                    new_path = fix_path(old_path)
                    if old_path != new_path:
                        item['path'] = new_path
                        changes_made += 1
        
        # Write back to file if changes were made
        if changes_made > 0:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  Fixed {changes_made} paths")
        else:
            print(f"  No changes needed")
        
        return changes_made
        
    except Exception as e:
        print(f"  Error: {e}")
        return 0

def main():
    """Main execution function"""
    print("Starting JSON path fixer...")
    print(f"Directory: {INPUT_DIR}\n")
    
    # Get all JSON files
    json_files = []
    for file in os.listdir(INPUT_DIR):
        if file.endswith('.json') and '_financials_' in file:
            json_files.append(os.path.join(INPUT_DIR, file))
    
    print(f"Found {len(json_files)} JSON files\n")
    
    if not json_files:
        print("No JSON files found.")
        return
    
    # Process each file
    total_changes = 0
    for idx, json_file in enumerate(json_files, 1):
        print(f"[{idx}/{len(json_files)}]")
        changes = fix_json_file(json_file)
        total_changes += changes
        print()
    
    print(f"{'='*50}")
    print(f"Finished! Total paths fixed: {total_changes}")

if __name__ == "__main__":
    main()