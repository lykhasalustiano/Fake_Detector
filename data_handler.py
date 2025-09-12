import pandas as pd

def save_to_excel(data, output_file):
    """Save article data to an Excel file"""
    if data:
        df = pd.DataFrame(data)
        df.to_excel(output_file, index=False)
        print(f"\n✅ Success! Scraped {len(data)} articles from NPR. Saved to '{output_file}'.")
        return True
    else:
        print("❌ No articles were found. The website structure may have changed.")
        return False

def print_preview(data):
    """Print a preview of the first article"""
    if data:
        print("\n--- Preview of the first article ---")
        print(f"Title: {data[0]['Title']}")
        print(f"Date: {data[0]['Published Date']}")
        print(f"Teaser: {data[0]['Teaser'][:100]}...")  # First 100 chars
        print(f"URL: {data[0]['Article URL']}")