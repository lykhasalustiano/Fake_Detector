import pandas as pd
import os

def save_to_excel(data, output_file):
    """Save article data to an Excel file"""
    if data:
        df = pd.DataFrame(data)
        
        # Reorder columns for better readability
        column_order = [
            'Source', 'Title', 'Teaser', 'Published Date', 'Detailed Date', 'Author', 
            'Article URL', 'Paragraph Count', 'Image Count', 
            'Content Paragraphs', 'Full Content', 'Image URLs', 'Label'
        ]
        
        # Only include columns that actually exist in the data
        existing_columns = [col for col in column_order if col in df.columns]
        # Add any remaining columns not in the predefined order
        for col in df.columns:
            if col not in existing_columns:
                existing_columns.append(col)
                
        df = df[existing_columns]
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        df.to_excel(output_file, index=False)
        sources = df['Source'].unique() if 'Source' in df.columns else ['Unknown']
        print(f"\n✅ Success! Scraped {len(data)} articles from {', '.join(sources)}. Saved to '{output_file}'.")
        return True
    else:
        print("❌ No articles were found. The website structure may have changed.")
        return False

def load_csv_data(file_path, max_articles=100):
    """Load data from CSV file (WELFake_Dataset format) with limit"""
    try:
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            print(f"✅ Loaded {len(df)} articles from {os.path.basename(file_path)}")
            
            # Limit to max_articles (random sample to get variety)
            if len(df) > max_articles:
                df = df.sample(n=max_articles, random_state=42)  # random_state for reproducibility
                print(f"📊 Limited to {max_articles} random articles from CSV")
            
            # Convert CSV data to the same format as scraped articles
            articles = []
            for _, row in df.iterrows():
                article = {
                    'Source': 'WELFake_Dataset',
                    'Title': str(row.get('title', 'No title')),
                    'Teaser': str(row.get('text', 'No content'))[:200] + "...",
                    'Published Date': 'N/A',
                    'Author': 'Unknown',
                    'Article URL': 'N/A',
                    'Paragraph Count': 0,
                    'Image Count': 0,
                    'Content Paragraphs': str(row.get('text', 'No content')),
                    'Full Content': str(row.get('text', 'No content')),
                    'Image URLs': '',
                    'Label': row.get('label', 'Unknown')  # 0=Real, 1=Fake
                }
                articles.append(article)
            
            return articles
        else:
            print(f"ℹ️ CSV file '{file_path}' not found.")
            return []
    except Exception as e:
        print(f"❌ Error loading CSV file: {e}")
        return []

def load_excel_data(file_path='news_articles.xlsx'):
    """Load data from Excel file"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        if os.path.exists(file_path):
            df = pd.read_excel(file_path)
            print(f"✅ Loaded {len(df)} articles from {os.path.basename(file_path)}")
            return df.to_dict('records')  # Convert to list of dictionaries
        else:
            print(f"ℹ️ Excel file '{file_path}' not found. Will scrape new data.")
            return []
    except Exception as e:
        print(f"❌ Error loading Excel file: {e}")
        return []

def print_preview(data):
    """Print a preview of the first article"""
    if data:
        print("\n" + "="*80)
        print("PREVIEW OF THE FIRST ARTICLE")
        print("="*80)
        print(f"Source: {data[0].get('Source', 'Unknown')}")
        print(f"Title: {data[0]['Title']}")
        print(f"Date: {data[0].get('Detailed Date', data[0].get('Published Date', 'Date not found'))}")
        print(f"Author: {data[0].get('Author', 'Author not found')}")
        print(f"URL: {data[0]['Article URL']}")
        print(f"Paragraphs: {data[0].get('Paragraph Count', 'N/A')}")
        print(f"Images: {data[0].get('Image Count', 'N/A')}")
        print("\n--- TEASER ---")
        print(f"{data[0]['Teaser'][:200]}...")
        
        if 'Content Paragraphs' in data[0]:
            print("\n--- FIRST TWO PARAGRAPHS ---")
            paragraphs = data[0]['Content Paragraphs'].split('\n\n')
            for i, para in enumerate(paragraphs[:2]):
                print(f"Paragraph {i+1}: {para[:150]}...")
        
        if 'Full Content' in data[0]:
            print(f"\n--- FULL CONTENT PREVIEW ---")
            print(f"{data[0]['Full Content'][:300]}...")
            
        if 'Image URLs' in data[0] and data[0]['Image URLs']:
            print(f"\n--- IMAGES ---")
            images = data[0]['Image URLs'].split(', ')
            for i, img in enumerate(images[:2]):  # Show first two images
                print(f"Image {i+1}: {img}")