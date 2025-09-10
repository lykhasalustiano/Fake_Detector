import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
from pathlib import Path
from datetime import datetime, timedelta

def scrape_npr_tech_news(url, output_file='npr_tech_news.xlsx'):
    # Check if we've exceeded the daily limit (5 times per day)
    last_run_file = "scrape_log.txt"
    today = datetime.now().date()
    
    # Read existing log or create new one
    if os.path.exists(last_run_file):
        with open(last_run_file, 'r') as f:
            lines = f.readlines()
            # Count how many times we've run today
            today_count = 0
            for line in lines:
                if line.strip():  # Skip empty lines
                    run_date = datetime.fromisoformat(line.strip()).date()
                    if run_date == today:
                        today_count += 1
            
            if today_count >= 5:
                print("❌ DAILY LIMIT REACHED: This script has been run 5 times today.")
                print("   To respect NPR's servers, please wait until tomorrow.")
                print("   Aborting scrape to maintain ethical standards.")
                return
    else:
        # Create the file if it doesn't exist
        with open(last_run_file, 'w') as f:
            pass
    
    # Record this run time
    with open(last_run_file, 'a') as f:
        f.write(datetime.now().isoformat() + '\n')
    
    # Display ethical warning
    print("=" * 70)
    print("ETHICAL WEB SCRAPING REMINDER:")
    print("=" * 70)
    print("• This script is limited to 5 runs per day")
    print("• Respect NPR's servers and bandwidth")
    print("• Check robots.txt: https://www.npr.org/robots.txt")
    print("• Consider using NPR's official API if available")
    print("=" * 70)
    
    # Verify user wants to proceed after ethical warning
    response = input("Do you understand and accept these ethical considerations? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Scraping cancelled. Thank you for being an ethical web citizen!")
        return
    
    try:
        headers = {
            'User-Agent': 'Educational-Web-Scraper/1.0 (Contact: your-email@example.com)'
        }
        
        print(f"\nFetching news from NPR: {url}")
        
        # Add a significant delay before request (ethical scraping practice)
        print("Waiting 5 seconds before request to respect server load...")
        time.sleep(5)
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        # Check if we're being rate limited or blocked
        if response.status_code == 429:
            print("❌ Rate limited by NPR. Please wait several hours before trying again.")
            return
            
        soup = BeautifulSoup(response.content, 'html.parser')
        print("Page fetched successfully. Parsing content...")
        
        articles = soup.find_all('article', class_='item')
        # If the class isn't found, try a more general approach
        if not articles:
            articles = soup.find_all('div', class_='story-wrap') or soup.find_all('div', class_=lambda c: c and 'story' in c)
            
        print(f"Found {len(articles)} article containers.")
        
        # Limit the number of articles scraped (reduce server impact)
        max_articles = 15  # Conservative limit to minimize impact
        if len(articles) > max_articles:
            print(f"Limiting output to {max_articles} articles to reduce server impact.")
            articles = articles[:max_articles]
        
        data = []
        
        for i, article in enumerate(articles):
            try:
                # Add small delay between processing articles
                if i > 0:
                    time.sleep(1)  # 1-second delay between articles
                
                # Find the title - usually in an <h2> or <h3> tag with an <a>
                title_elem = article.find('h2', class_='title') or article.find('h3') or article.find('a', class_='title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    # Get the URL for the article
                    link_elem = title_elem.find('a') if title_elem.name != 'a' else title_elem
                    article_url = link_elem.get('href', '')
                    if article_url and not article_url.startswith('http'):
                        article_url = 'https://www.npr.org' + article_url
                else:
                    continue  # Skip if no title is found
                
                # Find the teaser/description text
                teaser_elem = article.find('p', class_='teaser') or article.find('p', class_='summary') or article.find('div', class_='story-description')
                teaser = teaser_elem.get_text(strip=True) if teaser_elem else "No description available."
                
                # Find the date
                date_elem = article.find('time')
                date = date_elem.get('datetime') if date_elem and date_elem.has_attr('datetime') else (date_elem.get_text(strip=True) if date_elem else "Date not found")
                
                data.append({
                    'Title': title,
                    'Teaser': teaser,
                    'Published Date': date,
                    'Article URL': article_url
                })
                
            except Exception as e:
                print(f"  Error processing an article: {e}")
                continue
        
        # Create a DataFrame and save to Excel
        if data:
            df = pd.DataFrame(data)
            
            # Try to save to the requested location first
            try:
                df.to_excel(output_file, index=False)
                print(f"\n✅ Success! Scraped {len(data)} articles from NPR. Saved to '{output_file}'.")
                
            except PermissionError:
                # If permission denied, try saving to user's Documents folder
                documents_path = Path.home() / "Documents" / output_file
                try:
                    df.to_excel(documents_path, index=False)
                    print(f"\n✅ Success! Scraped {len(data)} articles from NPR.")
                    print(f"Saved to '{documents_path}' (original location had permission issues).")
                    output_file = str(documents_path)
                except Exception as e:
                    print(f"❌ Could not save to Documents folder either: {e}")
                    # As a last resort, save to current directory with a different name
                    alt_file = "npr_news_backup.xlsx"
                    df.to_excel(alt_file, index=False)
                    print(f"Saved to '{alt_file}' in current directory as fallback.")
                    output_file = alt_file
            
            # Print a preview
            print("\n--- Preview of the first article ---")
            print(f"Title: {data[0]['Title']}")
            print(f"Date: {data[0]['Published Date']}")
            print(f"Teaser: {data[0]['Teaser'][:100]}...") # First 100 chars
            print(f"URL: {data[0]['Article URL']}")
            
        else:
            print("❌ No articles were found. The website structure may have changed.")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching the webpage: {e}")
        print("This could be due to too many requests. Please wait before trying again.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
    
    # Final ethical reminder with usage count
    # Count how many times we've run today for the message
    with open(last_run_file, 'r') as f:
        lines = f.readlines()
        today_count = 0
        for line in lines:
            if line.strip():
                run_date = datetime.fromisoformat(line.strip()).date()
                if run_date == today:
                    today_count += 1
    
    remaining = 5 - today_count
    print("\n" + "=" * 70)
    print("ETHICAL SCRAPING FOLLOW-UP:")
    print("=" * 70)
    print(f"• You have {remaining} run{'s' if remaining != 1 else ''} remaining today")
    print("• Please space out your requests throughout the day")
    print("• Consider using NPR's official API for regular data needs")
    print("=" * 70)

# Run the function
if __name__ == "__main__":
    npr_tech_url = "https://www.npr.org/sections/technology/"
    
    # Try to save to a location with likely write permissions
    output_file = "npr_technology_news.xlsx"
    
    # Check if we have write permission in current directory
    if not os.access(".", os.W_OK):
        # Save to Documents folder if current directory isn't writable
        documents_path = Path.home() / "Documents" / output_file
        output_file = str(documents_path)
        print(f"Current directory not writable. Will save to: {output_file}")
    
    scrape_npr_tech_news(npr_tech_url, output_file)