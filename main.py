import sys
import os
from PyQt5.QtWidgets import QApplication

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from interface.user_interface import SereniTruthApp
from scraper import fetch_page_content, parse_articles
from data_handler import save_to_excel, print_preview

def scrape_npr_tech_news(url, output_file='npr_tech_news.xlsx'):
    """Main function to scrape NPR tech news"""
    try:
        html_content = fetch_page_content(url)
        if not html_content:
            return
            
        articles_data = parse_articles(html_content)
        
        if save_to_excel(articles_data, output_file):
            print_preview(articles_data)
            
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = SereniTruthApp()
    window.show()
    
    # Center the window on screen
    screen = app.primaryScreen().availableGeometry()
    window.move(
        (screen.width() - window.width()) // 2,
        (screen.height() - window.height()) // 2
    )
    
    sys.exit(app.exec_())

# Run the function 
if __name__ == "__main__":
    npr_tech_url = "https://www.npr.org/sections/technology/"
    scrape_npr_tech_news(npr_tech_url, "npr_technology_news.xlsx")
    main()