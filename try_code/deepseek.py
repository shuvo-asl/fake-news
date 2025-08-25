import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import os

def scrape_prothom_alo_education():
    # URL of the education section
    url = "https://www.prothomalo.com/education"
    
    # Headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Send GET request to the website
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all script tags with type application/json
        script_tags = soup.find_all('script', type='application/json')
        
        articles = []
        
        # Process each script tag with JSON data
        for script in script_tags:
            try:
                # Parse the JSON data
                data = json.loads(script.string)
                
                # Look for articles in different possible JSON structures
                articles.extend(extract_articles_from_json(data))
                
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"Error processing JSON: {e}")
                continue
        
        # Remove duplicates by link
        unique_articles = []
        seen_links = set()
        
        for article in articles:
            if article['link'] not in seen_links:
                seen_links.add(article['link'])
                unique_articles.append(article)
        
        return unique_articles
        
    except requests.RequestException as e:
        print(f"Error fetching the page: {e}")
        return []
    except Exception as e:
        print(f"Error parsing the page: {e}")
        return []

def extract_articles_from_json(data):
    """Recursively search through JSON data for articles"""
    articles = []
    
    # If data is a dictionary, search for articles
    if isinstance(data, dict):
        # Check if this dictionary represents an article
        if is_article(data):
            article = extract_article_info(data)
            if article:
                articles.append(article)
        
        # Recursively search through all values
        for value in data.values():
            articles.extend(extract_articles_from_json(value))
    
    # If data is a list, search each item
    elif isinstance(data, list):
        for item in data:
            articles.extend(extract_articles_from_json(item))
    
    return articles

def is_article(data):
    """Check if a dictionary represents an article"""
    # Common patterns for article objects
    article_indicators = ['headline', 'url', 'link', 'title', 'story', 'article']
    
    if not isinstance(data, dict):
        return False
    
    # Check if any article indicators are in the keys
    for key in data.keys():
        if any(indicator in str(key).lower() for indicator in article_indicators):
            return True
    
    return False

def extract_article_info(article_data):
    """Extract title and link from article data"""
    title = None
    link = None
    
    # Try different possible keys for title/headline
    title_keys = ['headline', 'title', 'name', 'heading', 'caption']
    for key in title_keys:
        if key in article_data and article_data[key]:
            title = article_data[key]
            # If it's a dictionary, look for text value
            if isinstance(title, dict) and 'text' in title:
                title = title['text']
            break
    
    # Try different possible keys for link/url
    link_keys = ['url', 'link', 'webUrl', 'permalink', 'href']
    for key in link_keys:
        if key in article_data and article_data[key]:
            link = article_data[key]
            break
    
    # If we have a relative URL, make it absolute
    if link and not link.startswith('http'):
        link = 'https://www.prothomalo.com' + link
    
    # Clean up title if it's found
    if title:
        # Remove HTML tags if any
        title = re.sub('<[^<]+?>', '', str(title))
        title = title.strip()
    
    if title and link:
        return {'title': title, 'link': link}
    
    return None

def save_to_json(articles, filename=None):
    """Save articles to a JSON file with Unicode support"""
    if not filename:
        # Create filename with current timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"prothom_alo_education_news_{timestamp}.json"
    
    # Prepare data for JSON
    data = {
        "source": "Prothom Alo Education",
        "scraped_at": datetime.now().isoformat(),
        "articles": articles
    }
    
    # Save to JSON with ensure_ascii=False to preserve Bangla characters
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filename

def load_from_json(filename):
    """Load articles from a JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"File {filename} not found.")
        return None
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return None

if __name__ == "__main__":
    print("Scraping Prothom Alo Education News from JSON data...")
    articles = scrape_prothom_alo_education()
    
    if articles:
        print(f"Found {len(articles)} articles:")
        for i, article in enumerate(articles, 1):
            print(f"{i}. {article['title']}")
            print(f"   Link: {article['link']}")
            print()
        
        # Save to JSON file
        filename = save_to_json(articles)
        print(f"Data saved to {filename}")
        
        # Demonstrate loading the data back
        print("\nLoading data from JSON file to verify Unicode support...")
        loaded_data = load_from_json(filename)
        
        if loaded_data:
            print(f"Successfully loaded {len(loaded_data['articles'])} articles")
            print("Sample of first article:")
            print(f"Title: {loaded_data['articles'][0]['title']}")
            print(f"Link: {loaded_data['articles'][0]['link']}")
    else:
        print("No articles found. The site structure may have changed.")