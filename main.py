# Add these lines at the VERY TOP of the file
import os
os.environ["PYTHONWARNINGS"] = "ignore::UserWarning"

# Force numpy to load before any other imports
try:
    import numpy as np
    # Check numpy version and force compatibility
    if hasattr(np, '__version__'):
        print(f"Using NumPy version: {np.__version__}")
except ImportError:
    print("NumPy not installed. Please run: pip install numpy==1.24.3")
    exit(1)

# Now suppress warnings
import warnings
warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")
warnings.filterwarnings("ignore", category=UserWarning)

import sys
import pandas as pd
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from interface.user_interface import SereniTruthApp
from scraper import fetch_page_content, enhanced_parse_articles
from data_handler import save_to_excel, load_excel_data, load_csv_data, print_preview

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # URLs to scrape (only NPR now)
    npr_tech_url = "https://www.npr.org/sections/technology/"
    
    # Create a dedicated data directory for the application
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)
    
    # Create separate Excel files for each source
    npr_excel_file = os.path.join(data_dir, "npr_articles.xlsx")
    csv_file_path = os.path.join(data_dir, "WELFake_Dataset.csv")
    excel_files = [npr_excel_file, csv_file_path]
    
    # Load data from both Excel files
    articles_data = []
    
    # Load NPR data from Excel if exists
    try:
        npr_data = load_excel_data(npr_excel_file)
        if npr_data:
            articles_data.extend(npr_data)
            print(f"✅ Loaded {len(npr_data)} articles from NPR Excel file")
    except Exception as e:
        print(f"Error loading NPR Excel file: {e}")
    
    # Load CSV data directly
    try:
        csv_data = load_csv_data(csv_file_path)
        if csv_data:
            articles_data.extend(csv_data)
            print(f"✅ Loaded {len(csv_data)} articles from CSV file")
        else:
            print("❌ No data was loaded from CSV file")
    except Exception as e:
        print(f"Error loading CSV file: {e}")
    
    # If no NPR data was loaded from Excel, scrape fresh data
    npr_count = len([article for article in articles_data if article.get('Source') == 'NPR'])
    if npr_count == 0:
        print("Scraping fresh data from NPR...")
        npr_html = fetch_page_content(npr_tech_url)
        if npr_html:
            npr_articles = enhanced_parse_articles(npr_html, "npr", get_full_content=True)
            if npr_articles:
                articles_data.extend(npr_articles)
                print(f"✅ Scraped {len(npr_articles)} articles from NPR")
                save_to_excel(npr_articles, npr_excel_file)
            else:
                print("❌ No articles were scraped from NPR.")
        else:
            print("❌ Failed to fetch content from NPR.")
    
    # Enhanced filtering: Remove articles with no title or invalid titles
    valid_articles = []
    invalid_count = 0
    
    for article in articles_data:
        title = article.get('Title', '')
        # Check for various invalid title conditions
        if (title and 
            title != 'No title' and 
            title != 'No title found' and 
            title.strip() != '' and
            title != 'Title not found' and
            title != 'Access Denied' and
            title != 'Error retrieving title'):
            valid_articles.append(article)
        else:
            invalid_count += 1
            print(f"⚠️ Skipping article with invalid title: '{title}'")
    
    articles_data = valid_articles
    print(f"✅ Filtered to {len(articles_data)} valid articles (removed {invalid_count} invalid)")
    
    # Run fake news detection on all loaded articles - with enhanced error handling
    try:
        # Import numpy first with error suppression (redundant but safe)
        import numpy as np
        import warnings
        warnings.filterwarnings("ignore", message="numpy.dtype size changed")
        warnings.filterwarnings("ignore", message="numpy.ufunc size changed")
        
        from naive_bayes_classifier import detect_fake_news_with_nb
        articles_data = detect_fake_news_with_nb(articles_data)
        print("✅ Fake news detection completed successfully")
    except ImportError as e:
        print(f"❌ Required packages not installed: {e}")
        print("Please run: pip install numpy scikit-learn pandas joblib")
        for article in articles_data:
            article['Fake_News_Label'] = '❓ PACKAGE_ERROR'
            article['Prediction'] = 'Error'
            article['Fake_Probability'] = 0.5
            article['Real_Probability'] = 0.5
            article['Confidence'] = 0.5
    except Exception as e:
        print(f"❌ Error running fake news detection: {e}")
        import traceback
        traceback.print_exc()
        # Set default status for articles if detection fails
        for article in articles_data:
            article['Fake_News_Label'] = '❓ ANALYSIS_ERROR'
            article['Prediction'] = 'Unknown'
            article['Fake_Probability'] = 0.5
            article['Real_Probability'] = 0.5
            article['Confidence'] = 0.5
    
    # Pass the data to the UI (using only NPR URL since CSV is loaded directly)
    window = SereniTruthApp(articles_data, [npr_tech_url], excel_files)
    window.show()
    
    # Center the window on screen
    screen = app.primaryScreen().availableGeometry()
    window.move(
        (screen.width() - window.width()) // 2,
        (screen.height() - window.height()) // 2
    )
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()