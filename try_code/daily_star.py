# daily_store.py
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import os
import time
from urllib.parse import urljoin
import shutil

def scrape_daily_star_education():
    # Base URL of the website
    base_url = "https://www.thedailystar.net"
    # URL of the education section
    url = base_url + "/tags/education"
    
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
        cards = soup.find_all('div', {'class': 'card'})
        stories = []
        
        for card in cards:
            title_tag = card.find('h3', {'class': 'title'})
            story = {
                'headline': None,
                'url': None,
                'hero_image_url': None,
                'last_published_at': None,
                'scraped_at': datetime.now().isoformat()
            }

            # Extract title and link
            if title_tag and title_tag.a:
                title = title_tag.a.get_text(strip=True)
                link = urljoin(base_url, title_tag.a['href'])
                story['headline'] = title
                story['url'] = link
            
            # Extract card-image if available
            image_div = card.find('div', {'class': 'card-image'})
            if image_div:
                image_url = image_div.a.picture.img['data-srcset'] if image_div.a and image_div.a.picture and image_div.a.picture.img else None
                story['hero_image_url'] = image_url

            # Extract published date if available
            time_tag = card.find('time')
            if time_tag:
                story['last_published_at'] = time_tag.get('datetime', '')

            stories.append(story)
        
        return stories
        
    except requests.RequestException as e:
        print(f"Error fetching the page: {e}")
        return []
    except Exception as e:
        print(f"Error parsing the page: {e}")
        return []

def scrape_daily_star_news_details(story_url):
    """
    Scrape detailed content from an individual Daily Star news page
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
        
        story_details = {
            'headline': '',
            'description': '',
            'image_urls': [],
            'scraped_at': datetime.now().isoformat()
        }
        
        try:
            # Find the article section
            story_div = soup.find('article', {'class': 'article-section'})
            if not story_div:
                print(f"No article section found for {story_url}")
                return None
            
            # Extract title
            story_title_tag = story_div.find('h1', {'class': 'article-title'})
            if story_title_tag:
                story_details['headline'] = story_title_tag.get_text(strip=True)
            
            # Extract published date
            time_tag = story_div.find('time')
            if time_tag:
                story_details['last_published_at'] = time_tag.get('datetime', '')
            
            # Extract images from media section
            story_media_div = story_div.find('div', {'class': 'section-media'})
            if story_media_div:
                img_tags = story_media_div.find_all('span', {'class': 'lg-gallery'})
                for tag in img_tags:
                    if tag.picture and tag.picture.img and tag.picture.img.get('data-srcset'):
                        img_url = tag.picture.img['data-srcset']
                        story_details['image_urls'].append(img_url)
            
            # Extract story description - only paragraphs without classes
            story_content_div = story_div.find('div', {'class': 'clearfix'})
            if story_content_div:
                # Find all p tags that don't have a class attribute
                story_paragraphs = story_content_div.find_all('p', class_=False)
                description_parts = []
                
                for p in story_paragraphs:
                    text = p.get_text(strip=True)
                    if text:  # Only add non-empty text
                        description_parts.append(text)
                
                story_details['description'] = "\n\n".join(description_parts)
            
            return story_details
            
        except Exception as e:
            print(f"Error parsing story content for {story_url}: {e}")
            return None
        
    except requests.RequestException as e:
        print(f"Error fetching the story page {story_url}: {e}")
        return None
    except Exception as e:
        print(f"Error parsing the story page {story_url}: {e}")
        return None

def download_daily_star_images(image_urls, slug):
    """
    Download multiple images from Daily Star and return their local paths
    """
    local_paths = []
    for i, image_url in enumerate(image_urls):
        local_path = download_daily_star_image(image_url, slug, f"image_{i+1}")
        if local_path:
            local_paths.append(local_path)
    
    return local_paths

def download_daily_star_image(image_url, slug, image_name):
    """
    Download a single image from Daily Star and return its local path
    """
    try:
        # Create images directory if it doesn't exist
        image_dir = os.path.join("data", "images", "daily_star", slug)
        os.makedirs(image_dir, exist_ok=True)
        
        # Get file extension from URL or use default
        file_extension = os.path.splitext(image_url.split('?')[0])[1]  # Remove query parameters
        if not file_extension or len(file_extension) > 5:  # Sanity check
            file_extension = ".jpg"
        
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
        
        print(f"Downloaded image: {filename}")
        
        # Return relative path
        return os.path.relpath(filepath, "data")
    
    except Exception as e:
        print(f"Error downloading image {image_url}: {e}")
        return None

def scrape_all_daily_star_news_details(story_list, max_stories=None, delay=1):
    """
    Scrape details for all Daily Star stories in the list
    """
    detailed_stories = []
    
    # Limit the number of stories if specified
    if max_stories:
        story_list = story_list[:max_stories]
    
    for i, story in enumerate(story_list, 1):
        print(f"Scraping Daily Star story {i}/{len(story_list)}: {story['headline']}")
        
        story_details = scrape_daily_star_news_details(story['url'])
        if story_details:
            # Generate slug from URL for image directory
            slug = story['url'].split('/')[-1]  # Use the last part of URL as slug
            if '?' in slug:  # Remove query parameters if any
                slug = slug.split('?')[0]
            
            # Download images and get local paths
            local_images = download_daily_star_images(story_details['image_urls'], slug)
            
            # Download hero image if it exists
            hero_image_local = None
            if story.get('hero_image_url'):
                hero_image_local = download_daily_star_image(story['hero_image_url'], slug, "hero")
                if hero_image_local:
                    local_images.append(hero_image_local)
            
            # Merge basic story info with details
            merged_story = {
                **story,
                **story_details,
                'slug': slug,
                'local_images': local_images,
                'hero_image_local': hero_image_local
            }
            detailed_stories.append(merged_story)
        else:
            print(f"Failed to scrape details for: {story['headline']}")
        
        # Add delay to avoid overwhelming the server
        time.sleep(delay)
    
    return detailed_stories

def save_daily_star_to_json(stories, filename=None, directory="data"):
    """Save Daily Star stories to a JSON file with Unicode support"""
    # Create directory if it doesn't exist
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    if not filename:
        # Create filename with current timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"daily_star_education_news_{timestamp}.json"
    
    # Add full path
    filepath = os.path.join(directory, filename)
    
    # Prepare data for JSON
    data = {
        "source": "The Daily Star - Education",
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
        print(f"   Description length: {len(story.get('description', ''))} characters")
        print(f"   Images: {len(story.get('image_urls', []))}")
        print()

def main():
    print("Scraping The Daily Star Education News...")
    
    # Scrape the basic stories
    stories = scrape_daily_star_education()
    
    if stories:
        # Print the first few stories
        print_stories(stories)
        
        # Scrape detailed content for all stories
        print("\nScraping detailed content for each story...")
        detailed_stories = scrape_all_daily_star_news_details(stories, delay=2)

        if detailed_stories:
            # Save to JSON file
            filename = save_daily_star_to_json(detailed_stories)
            
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

if __name__ == "__main__":
    main()