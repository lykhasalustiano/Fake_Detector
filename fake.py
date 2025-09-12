import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_npr_tech_news(url, output_file='npr_tech_news.xlsx'):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"Fetching news from NPR: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        print("Page fetched successfully. Parsing content...")
        
        # NPR uses article tags with specific classes. This is a common pattern.
        articles = soup.find_all('article', class_='item')
        # If the class isn't found, try a more general approach
        if not articles:
            articles = soup.find_all('div', class_='story-wrap') or soup.find_all('div', class_=lambda c: c and 'story' in c)
            
        print(f"Found {len(articles)} article containers.")
        
        data = []
        
        for article in articles:
            try:
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
            df.to_excel(output_file, index=False)
            print(f"\n✅ Success! Scraped {len(data)} articles from NPR. Saved to '{output_file}'.")
            
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
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

# Run the function 
if __name__ == "__main__":
    npr_tech_url = "https://www.npr.org/sections/technology/"
    scrape_npr_tech_news(npr_tech_url, "npr_technology_news.xlsx")