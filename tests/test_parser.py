import os
import glob
import json
from ingest.parser import Parser

def test_parser_scraped_files():
    # Find the latest raw folder
    raw_dirs = sorted(glob.glob("data/raw/20*"))
    if not raw_dirs:
        print("No raw scraped directories found.")
        return
        
    latest_dir = raw_dirs[-1]
    print(f"\nVerifying parsing on directory: {latest_dir}")
    
    parser = Parser()
    html_files = glob.glob(os.path.join(latest_dir, "*.html"))
    
    assert len(html_files) > 0, "No HTML files found to parse!"
    
    for file_path in html_files:
        scheme_id = os.path.basename(file_path).replace(".html", "")
        with open(file_path, "r", encoding="utf-8") as f:
            html = f.read()
            
        data, text = parser.parse_html(html, url=f"https://groww.in/mutual-funds/{scheme_id}")
        
        print(f"\n--- Results for {scheme_id} ---")
        print(json.dumps(data, indent=2))
        print(f"Clean text length: {len(text)}")
        
        # Verify required keys exist
        assert "nav" in data
        assert "minimum_sip" in data
        assert "fund_size_aum" in data
        assert "expense_ratio" in data
        assert "riskometer" in data
        assert "benchmark" in data
        assert "fund_managers" in data
        assert isinstance(data["fund_managers"], list)

if __name__ == "__main__":
    test_parser_scraped_files()
