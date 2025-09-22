import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin
import random

def fetch_page_content(url, max_retries=3):
    """Fetch the HTML content of a webpage with retry mechanism"""
    for attempt in range(max_retries):
        try:
            # Rotate user agents to avoid detection
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
            ]
            
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            print(f"Fetching news from: {url} (Attempt {attempt + 1}/{max_retries})")
            # Increase timeout to 30 seconds
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Check if we got a valid HTML response (not a blocked page)
            if "access denied" in response.text.lower() or "blocked" in response.text.lower():
                print(f"❌ Access denied by {url}. They might be blocking scrapers.")
                return None
                
            return response.content
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching the webpage (Attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4 seconds
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Failed after {max_retries} attempts")
                return None

# In scraper.py, modify the parse_npr_articles function
def parse_npr_articles(html_content, base_url="https://www.npr.org"):
    """Parse NPR HTML content and extract article information"""
    if not html_content:
        return []
        
    soup = BeautifulSoup(html_content, 'html.parser')
    print("NPR page fetched successfully. Parsing content...")
    
    # Find all article containers on NPR
    article_containers = soup.find_all('div', class_='story-wrap') or soup.find_all('article')
    
    if not article_containers:
        # Alternative selectors if the primary ones don't work
        article_containers = soup.select('.item, .story, [data-story], .has-image')
    
    print(f"Found {len(article_containers)} article containers on NPR")
    
    data = []
    
    for container in article_containers:
        try:
            # Extract title
            title_elem = container.find('h2', class_='title') or container.find('h3', class_='title') or \
                        container.find('h2') or container.find('h3') or container.find('h1')
            title = title_elem.get_text(strip=True) if title_elem else None
            
            # Skip articles with no title or invalid titles
            if not title or title == "No title found" or title.strip() == '':
                print(f"⚠️ Skipping article with no title")
                continue
            
            # Extract article URL
            link_elem = container.find('a', href=True)
            if link_elem:
                link = link_elem['href']
                if not link.startswith('http'):
                    link = urljoin(base_url, link)
            else:
                link = "URL not found"
            
            # Extract teaser/description
            teaser_elem = container.find('p', class_='teaser') or container.find('p', class_='summary') or \
                         container.find('div', class_='story-description') or container.find('p')
            teaser = teaser_elem.get_text(strip=True) if teaser_elem else "No description available"
            
            # Extract date
            date_elem = container.find('time') or container.find('span', class_='date')
            date = date_elem.get_text(strip=True) if date_elem else "Date not found"
            
            # Extract author
            author_elem = container.find('p', class_='byline') or container.find('span', class_='byline')
            author = author_elem.get_text(strip=True) if author_elem else "Author not found"
            
            data.append({
                'Source': 'NPR',
                'Title': title,
                'Teaser': teaser,
                'Published Date': date,
                'Author': author,
                'Article URL': link
            })
            
        except Exception as e:
            print(f"  Error processing an NPR article: {e}")
            continue
    
    print(f"✅ Successfully parsed {len(data)} valid articles from NPR")
    return data

def parse_articles(html_content, source, base_url=None):
    """Parse HTML content based on the source"""
    if source == "npr":
        return parse_npr_articles(html_content, base_url or "https://www.npr.org")
    else:
        print(f"Unknown source: {source}")
        return []

def get_article_full_content(url, source, max_retries=2):
    """Fetch full article content from individual article pages with retry mechanism"""
    for attempt in range(max_retries):
        try:
            # Rotate user agents
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
            ]
            
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            print(f"Fetching full article from {source}: {url} (Attempt {attempt + 1}/{max_retries})")
            response = requests.get(url, headers=headers, timeout=25)
            response.raise_for_status()
            
            # Check if we got blocked
            if "access denied" in response.text.lower() or "blocked" in response.text.lower():
                print(f"❌ Access denied when trying to fetch full article from {url}")
                return {
                    'title': "Access Denied",
                    'full_content': "Could not retrieve full content due to access restrictions.",
                    'paragraphs': [],
                    'images': [],
                    'article_date': "Date not available"
                }
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract the article title
            title_elem = (soup.find('h1') or soup.find('h2', class_='title') or
                         soup.find('h1', attrs={'data-qa': 'headline'}) or
                         soup.find('h1', class_=re.compile(r'headline|title', re.I)))
            article_title = title_elem.get_text(strip=True) if title_elem else "Title not found"
            
            # Extract full article content - different selectors for different sources
            if source == "npr":
                content_div = (soup.find('div', id='storytext') or 
                              soup.find('article') or 
                              soup.find('div', class_='storytext') or 
                              soup.find('div', class_='transcript'))
            else:
                content_div = soup.find('article') or soup.find('div', class_='content')
            
            full_content = ""
            content_paragraphs = []
            
            if content_div:
                # Get all paragraphs
                paragraphs = content_div.find_all('p')
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    # Skip very short paragraphs (likely ads or metadata) and navigation text
                    if (text and len(text) > 20 and 
                        not any(x in text.lower() for x in ['sign up', 'subscribe', 'newsletter', 'advertisement'])):
                        content_paragraphs.append(text)
                        full_content += text + "\n\n"
            
            # Extract images if available
            images = []
            image_elems = content_div.find_all('img') if content_div else []
            for img in image_elems:
                if img.get('src'):
                    img_src = img['src']
                    if not img_src.startswith('http'):
                        img_src = urljoin(url, img_src)
                    images.append(img_src)
            
            # Extract article date more precisely
            date_elem = (soup.find('time') or 
                        soup.find('span', class_='date') or
                        soup.find('meta', property='article:published_time') or
                        soup.find('span', attrs={'data-qa': 'display-date'}))
            
            if date_elem:
                if date_elem.get('datetime'):  # If it's a time element with datetime attribute
                    article_date = date_elem['datetime']
                elif date_elem.get('content'):  # If it's a meta tag
                    article_date = date_elem['content']
                else:
                    article_date = date_elem.get_text(strip=True)
            else:
                article_date = "Date not found"
            
            return {
                'title': article_title,
                'full_content': full_content.strip(),
                'paragraphs': content_paragraphs,
                'images': images,
                'article_date': article_date
            }
            
        except Exception as e:
            print(f"Error fetching full article content from {source} (Attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1)  # Short delay before retry
                continue
            else:
                return {
                    'title': "Error retrieving title",
                    'full_content': f"Error retrieving full content: {e}",
                    'paragraphs': [],
                    'images': [],
                    'article_date': "Date not available"
                }

def enhanced_parse_articles(html_content, source, get_full_content=True, base_url=None):
    """Enhanced parsing with option to get full article content"""
    basic_data = parse_articles(html_content, source, base_url)
    
    if get_full_content and basic_data:
        print(f"Fetching full content for {len(basic_data)} {source} articles...")
        for i, article in enumerate(basic_data):
            if article['Article URL'] and article['Article URL'] != "URL not found":
                full_content_data = get_article_full_content(article['Article URL'], source)
                
                # Add all the extracted content to the article data
                article['Full Content'] = full_content_data['full_content']
                article['Content Paragraphs'] = "\n\n".join(full_content_data['paragraphs'])
                article['Paragraph Count'] = len(full_content_data['paragraphs'])
                article['Image URLs'] = ", ".join(full_content_data['images'])
                article['Image Count'] = len(full_content_data['images'])
                article['Detailed Date'] = full_content_data['article_date']
                
                # Update progress
                print(f"Fetched {i+1}/{len(basic_data)} articles from {source} - {article['Title']}")
                time.sleep(1)  # Increased delay to avoid being blocked
    
    return basic_data