import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import os
import time
from urllib.parse import urljoin
import shutil

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
            if story and story['slug'] not in seen_slugs:
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
            # Some stories might be nested under a 'story' key
            story_data = data.get('story', data)
            story = extract_story_info(story_data)
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
            # Construct the full image URL
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

def scrape_news_details(story_url):
    """
    Scrape detailed content from an individual news page
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'bn,en;q=0.9,en-US;q=0.8',
    }
    
    try:
        # Send GET request to the story page
        response = requests.get(story_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all script tags with type application/json
        script_tags = soup.find_all('script', type='application/json')
        
        story_details = None
        
        # Process each script tag with JSON data
        for script in script_tags:
            try:
                # Parse the JSON data
                data = json.loads(script.string)
                
                # Look for the qt.data structure
                if 'qt' in data and 'data' in data['qt']:
                    qt_data = data['qt']['data']['story']
                    # print(qt_data['story']['cards'])
                    story_details = extract_story_details(qt_data, story_url)
                    if story_details:
                        break
                
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"Error processing JSON for {story_url}: {e}")
                continue
        
        return story_details
        
    except requests.RequestException as e:
        print(f"Error fetching the story page {story_url}: {e}")
        return None
    except Exception as e:
        print(f"Error parsing the story page {story_url}: {e}")
        return None

def extract_story_details(story_data, story_url):
    """
    Extract detailed information from a story object
    """
    try:
        # Extract basic story information
        headline = story_data.get('headline', '')
        slug = story_data.get('slug', '')
        last_published_at = story_data.get('last-published-at', '')
        
        # Extract hero image
        hero_image_s3_key = story_data.get('hero-image-s3-key', '')
        hero_image_url = None
        if hero_image_s3_key:
            hero_image_url = f"https://media.prothomalo.com/{hero_image_s3_key}"
        
        # Extract story content from cards
        description = ""
        image_urls = []
        textCount = 0 
        
        cards = story_data.get('cards', [])
        for card in cards:
            story_elements = card.get('story-elements', [])
            for element in story_elements:
                element_type = element.get('type', '')
                subtype = element.get('subtype', '')
                
                # Only process elements with null subtype
                if subtype is None:
                    if element_type == 'text' or element_type == 'title':
                        text = element.get('text', '')
                        if text:
                            # Clean up text (remove HTML tags if any)
                            text = re.sub('<[^<]+?>', '', text)
                            description += text + "\n\n"
                    
                    elif element_type == 'image':
                        image_s3_key = element.get('image-s3-key', '')
                        if image_s3_key:
                            image_url = f"https://media.prothomalo.com/{image_s3_key}"
                            image_urls.append(image_url)
        
        # Download images and get local paths
        local_images = download_images(image_urls, slug)
        
        # Download hero image if it exists
        hero_image_local = None
        if hero_image_url:
            hero_image_local = download_image(hero_image_url, slug, "hero")
        
        return {
            'headline': headline,
            'slug': slug,
            'url': story_url,
            'last_published_at': last_published_at,
            'hero_image_url': hero_image_url,
            'hero_image_local': hero_image_local,
            'description': description.strip(),
            'image_urls': image_urls,
            'local_images': local_images,
            'textCount':textCount,
            'scraped_at': datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"Error extracting story details: {e}")
        return None

def download_images(image_urls, slug):
    """
    Download multiple images and return their local paths
    """
    local_paths = []
    for i, image_url in enumerate(image_urls):
        local_path = download_image(image_url, slug, f"image_{i+1}")
        if local_path:
            local_paths.append(local_path)
    
    return local_paths

def download_image(image_url, slug, image_name):
    """
    Download a single image and return its local path
    """
    try:
        # Create images directory if it doesn't exist
        image_dir = os.path.join("data", "images", slug)
        os.makedirs(image_dir, exist_ok=True)
        
        # Get file extension from URL
        file_extension = os.path.splitext(image_url)[1]
        # if not file_extension:
        #     file_extension = ".jpg"  # Default extension
        
        # Create filename
        filename = f"{image_name}{file_extension}"
        filepath = os.path.join(image_dir, filename)
        
        # Skip if file already exists
        if os.path.exists(filepath):
            return os.path.relpath(filepath, "data")
        
        # Download the image
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(image_url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        # Save the image
        with open(filepath, 'wb') as out_file:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, out_file)
        
        # print(f"Downloaded image: {filename}")
        
        # Return relative path
        return os.path.relpath(filepath, "data")
    
    except Exception as e:
        print(f"Error downloading image {image_url}: {e}")
        return None

def scrape_all_news_details(story_list, max_stories=None, delay=1):
    """
    Scrape details for all stories in the list
    """
    detailed_stories = []
    
    # Limit the number of stories if specified
    if max_stories:
        story_list = story_list[:max_stories]
    
    for i, story in enumerate(story_list, 1):
        print(f"Scraping story {i}/{len(story_list)}: {story['headline']}")
        
        story_details = scrape_news_details(story['url'])
        if story_details:
            # Merge basic story info with details
            merged_story = {**story, **story_details}
            detailed_stories.append(merged_story)
        else:
            print(f"Failed to scrape details for: {story['headline']}")
        
        # Add delay to avoid overwhelming the server
        time.sleep(delay)
    
    return detailed_stories

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
        if story.get('last_published_at'):
            print(f"   Published: {story['last_published_at']}")
        if story.get('hero_image_url'):
            print(f"   Hero Image: {story['hero_image_url']}")
        print()

if __name__ == "__main__":
    print("Scraping Prothom Alo Education News with detailed content...")
    
    # Scrape the basic stories
    stories = scrape_prothom_alo_education()
    
    if stories:
        # Print the first few stories
        print_stories(stories)
        
        # Scrape detailed content for all stories (limit to 3 for demo)
        print("\nScraping detailed content for each story...")
        detailed_stories = scrape_all_news_details(stories, delay=2)
        
        if detailed_stories:
            # Save to JSON file
            filename = save_to_json(detailed_stories)
            
            # Demonstrate loading the data back
            print("Loading data from JSON file to verify content...")
            loaded_data = load_from_json(filename)
            
            if loaded_data:
                print(f"Successfully loaded {loaded_data['story_count']} detailed stories")
                print("Sample of first story:")
                print(f"Headline: {loaded_data['stories'][0]['headline']}")
                print(f"URL: {loaded_data['stories'][0]['url']}")
                print(f"Description length: {len(loaded_data['stories'][0]['description'])} characters")
                print(f"Local images: {len(loaded_data['stories'][0]['local_images'])}")
                
                # Print first 200 characters of description
                if loaded_data['stories'][0]['description']:
                    description_preview = loaded_data['stories'][0]['description'][:200] + "..." if len(loaded_data['stories'][0]['description']) > 200 else loaded_data['stories'][0]['description']
                    print(f"Description preview: {description_preview}")
        else:
            print("No detailed stories found.")
    else:
        print("No stories found. The site structure may have changed.")