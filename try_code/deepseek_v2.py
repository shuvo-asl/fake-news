import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import os
import time
from urllib.parse import urljoin

def scrape_prothom_alo_education():
    # URL of the education section
    url = "https://www.prothomalo.com/education"
    
    # Headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'bn,en;q=0.9,en-US;q=0.8',
    }
    
    try:
        # Send GET request to the website
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all script tags with type application/json
        script_tags = soup.find_all('script', type='application/json')
        
        stories = []
        
        # Process each script tag with JSON data
        for script in script_tags:
            try:
                # Parse the JSON data
                data = json.loads(script.string)
                
                # Look for the qt.data structure
                if 'qt' in data and 'data' in data['qt']:
                    qt_data = data['qt']['data']
                    # Recursively traverse the data to find all stories
                    stories.extend(traverse_collections(qt_data))
                
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"Error processing JSON: {e}")
                continue
        
        # Remove duplicates by slug
        unique_stories = []
        seen_slugs = set()
        
        for story in stories:
            if story['slug'] not in seen_slugs:
                seen_slugs.add(story['slug'])
                unique_stories.append(story)
        
        return unique_stories
        
    except requests.RequestException as e:
        print(f"Error fetching the page: {e}")
        return []
    except Exception as e:
        print(f"Error parsing the page: {e}")
        return []

def traverse_collections(data):
    """
    Recursively traverse through collections to find all stories
    """
    stories = []
    
    # If data is a dictionary
    if isinstance(data, dict):
        # Check if this is a collection
        if data.get('type') == 'collection' and 'items' in data:
            # Process each item in the collection
            for item in data['items']:
                stories.extend(traverse_collections(item))
        
        # Check if this is a story
        elif data.get('type') == 'story':
            story = extract_story_info(data['story'])
            if story:
                stories.append(story)
        
        # Recursively search through all values
        for value in data.values():
            if isinstance(value, (dict, list)):
                stories.extend(traverse_collections(value))
    
    # If data is a list, process each item
    elif isinstance(data, list):
        for item in data:
            stories.extend(traverse_collections(item))
    
    return stories

def extract_story_info(story_data):
    """
    Extract required information from a story object
    """
    try:
        # Extract headline
        headline = story_data.get('headline')
        if not headline:
            return None
        
        # Extract slug
        slug = story_data.get('slug')
        if not slug:
            return None
        
        # Extract last published date
        last_published_at = story_data.get('last-published-at')
        
        # Extract hero image
        hero_image_s3_key = story_data.get('hero-image-s3-key')
        hero_image_url = None
        if hero_image_s3_key:
            # Construct the full image URL (this might need adjustment based on actual URL pattern)
            hero_image_url = f"https://media.prothomalo.com/{hero_image_s3_key}"
        
        # Construct the story URL
        story_url = f"https://www.prothomalo.com/{slug}"
        
        return {
            'headline': headline,
            'slug': slug,
            'url': story_url,
            'last_published_at': last_published_at,
            'hero_image_url': hero_image_url,
            'scraped_at': datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"Error extracting story info: {e}")
        return None

def save_to_json(stories, filename=None, directory="data"):
    """Save stories to a JSON file with Unicode support"""
    # Create directory if it doesn't exist
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    if not filename:
        # Create filename with current timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"prothom_alo_education_news_{timestamp}.json"
    
    # Add full path
    filepath = os.path.join(directory, filename)
    
    # Prepare data for JSON
    data = {
        "source": "Prothom Alo Education",
        "scraped_at": datetime.now().isoformat(),
        "story_count": len(stories),
        "stories": stories
    }
    
    # Save to JSON with ensure_ascii=False to preserve Bangla characters
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Data successfully saved to {filepath}")
    return filepath

def load_from_json(filename):
    """Load stories from a JSON file"""
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

def print_stories(stories, limit=5):
    """Print stories in a formatted way"""
    if not stories:
        print("No stories to display.")
        return
    
    print(f"\nFound {len(stories)} stories:")
    print("=" * 80)
    
    for i, story in enumerate(stories[:limit], 1):
        print(f"{i}. {story['headline']}")
        print(f"   URL: {story['url']}")
        if story['last_published_at']:
            print(f"   Published: {story['last_published_at']}")
        if story['hero_image_url']:
            print(f"   Image: {story['hero_image_url']}")
        print()

if __name__ == "__main__":
    print("Scraping Prothom Alo Education News with recursive JSON traversal...")
    
    # Scrape the stories
    stories = scrape_prothom_alo_education()
    
    if stories:
        # Print the first few stories
        print_stories(stories)
        
        # Save to JSON file
        filename = save_to_json(stories)
        
        # Demonstrate loading the data back
        print("Loading data from JSON file to verify Unicode support...")
        loaded_data = load_from_json(filename)
        
        if loaded_data:
            print(f"Successfully loaded {loaded_data['story_count']} stories")
            print("Sample of first story:")
            print(f"Headline: {loaded_data['stories'][0]['headline']}")
            print(f"URL: {loaded_data['stories'][0]['url']}")
    else:
        print("No stories found. The site structure may have changed.")