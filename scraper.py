import requests
from bs4 import BeautifulSoup

def fetch_page_content(url):
    """Fetch the HTML content of a webpage"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"Fetching news from NPR: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching the webpage: {e}")
        return None

def parse_articles(html_content):
    """Parse HTML content and extract article information"""
    if not html_content:
        return []
        
    soup = BeautifulSoup(html_content, 'html.parser')
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
    
    return data