# base_scraper.py
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import os
import time
from urllib.parse import urljoin
import shutil
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any


class BaseNewsScraper(ABC):
    """
    Base class for news scrapers with common functionality
    """
    
    def __init__(self, source_name: str, base_url: str = None):
        self.source_name = source_name
        self.base_url = base_url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'bn,en;q=0.9,en-US;q=0.8',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def make_request(self, url: str, timeout: int = 30) -> Optional[requests.Response]:
        """Make HTTP request with error handling"""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def parse_html(self, response: requests.Response) -> Optional[BeautifulSoup]:
        """Parse HTML response with error handling"""
        try:
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Error parsing HTML: {e}")
            return None
    
    def parse_json_from_script(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract JSON data from script tags"""
        json_data_list = []
        script_tags = soup.find_all('script', type='application/json')
        
        for script in script_tags:
            try:
                if script.string:
                    data = json.loads(script.string)
                    json_data_list.append(data)
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"Error processing JSON: {e}")
                continue
        
        return json_data_list
    
    def create_slug_from_url(self, url: str) -> str:
        """Generate slug from URL"""
        slug = url.split('/')[-1]
        if '?' in slug:
            slug = slug.split('?')[0]
        return slug
    
    def download_image(self, image_url: str, slug: str, image_name: str, 
                      subdirectory: str = None) -> Optional[str]:
        """Download a single image and return its local path"""
        try:
            # Create images directory structure
            base_dir = ["data", "images"]
            if subdirectory:
                base_dir.append(subdirectory)
            base_dir.append(slug)
            
            image_dir = os.path.join(*base_dir)
            os.makedirs(image_dir, exist_ok=True)
            
            # Get file extension from URL
            file_extension = os.path.splitext(image_url.split('?')[0])[1]
            if not file_extension or len(file_extension) > 5:
                file_extension = ".jpg"
            
            # Create filename and filepath
            filename = f"{image_name}{file_extension}"
            filepath = os.path.join(image_dir, filename)
            
            # Skip if file already exists
            if os.path.exists(filepath):
                return os.path.relpath(filepath, "data")
            
            # Download the image
            response = self.make_request(image_url)
            if not response:
                return None
            
            # Save the image
            with open(filepath, 'wb') as out_file:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, out_file)
            
            print(f"Downloaded image: {filename}")
            return os.path.relpath(filepath, "data")
        
        except Exception as e:
            print(f"Error downloading image {image_url}: {e}")
            return None
    
    def download_images(self, image_urls: List[str], slug: str, 
                       subdirectory: str = None) -> List[str]:
        """Download multiple images and return their local paths"""
        local_paths = []
        for i, image_url in enumerate(image_urls):
            local_path = self.download_image(
                image_url, slug, f"image_{i+1}", subdirectory
            )
            if local_path:
                local_paths.append(local_path)
        return local_paths
    
    def save_to_json(self, stories: List[Dict], filename: str = None, 
                    directory: str = "data") -> str:
        """Save stories to a JSON file with Unicode support"""
        # Create directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)
        
        if not filename:
            # Create filename with current timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_source_name = re.sub(r'[^\w\s-]', '', self.source_name.lower())
            safe_source_name = re.sub(r'[-\s]+', '_', safe_source_name)
            filename = f"{safe_source_name}_education_news_{timestamp}.json"
        
        filepath = os.path.join(directory, filename)
        
        # Prepare data for JSON
        data = {
            "source": self.source_name,
            "scraped_at": datetime.now().isoformat(),
            "story_count": len(stories),
            "stories": stories
        }
        
        # Save to JSON with ensure_ascii=False to preserve Unicode characters
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Data successfully saved to {filepath}")
        return filepath
    
    @staticmethod
    def load_from_json(filename: str) -> Optional[Dict]:
        """Load stories from a JSON file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"File {filename} not found.")
            return None
        except Exception as e:
            print(f"Error loading JSON file: {e}")
            return None
    
    def print_stories(self, stories: List[Dict], limit: int = 5) -> None:
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
            if 'description' in story:
                desc_length = len(story.get('description', ''))
                print(f"   Description length: {desc_length} characters")
            if 'image_urls' in story:
                img_count = len(story.get('image_urls', []))
                print(f"   Images: {img_count}")
            print()
    
    def scrape_all_details(self, story_list: List[Dict], max_stories: int = None, 
                          delay: int = 1) -> List[Dict]:
        """Scrape details for all stories in the list"""
        detailed_stories = []
        
        # Limit the number of stories if specified
        if max_stories:
            story_list = story_list[:max_stories]
        
        for i, story in enumerate(story_list, 1):
            print(f"Scraping story {i}/{len(story_list)}: {story['headline']}")
            
            story_details = self.scrape_story_details(story['url'])
            if story_details:
                # Merge basic story info with details
                merged_story = {**story, **story_details}
                detailed_stories.append(merged_story)
            else:
                print(f"Failed to scrape details for: {story['headline']}")
            
            # Add delay to avoid overwhelming the server
            time.sleep(delay)
        
        return detailed_stories
    
    def run_complete_scrape(self, max_stories: int = None, delay: int = 1) -> List[Dict]:
        """Run the complete scraping process"""
        print(f"Scraping {self.source_name} Education News...")
        
        # Scrape basic stories
        stories = self.scrape_stories()
        
        if not stories:
            print("No stories found. The site structure may have changed.")
            return []
        
        # Print sample stories
        self.print_stories(stories)
        
        # Scrape detailed content
        print("\nScraping detailed content for each story...")
        detailed_stories = self.scrape_all_details(stories, max_stories, delay)
        
        if detailed_stories:
            # Save to JSON
            filename = self.save_to_json(detailed_stories)
            
            # Verify saved data
            print("Loading data from JSON file to verify content...")
            loaded_data = self.load_from_json(filename)
            
            if loaded_data:
                self._print_verification_info(loaded_data)
            
            return detailed_stories
        else:
            print("No detailed stories found.")
            return []
    
    def _print_verification_info(self, loaded_data: Dict) -> None:
        """Print verification information for saved data"""
        print(f"Successfully loaded {loaded_data['story_count']} detailed stories")
        if loaded_data['stories']:
            first_story = loaded_data['stories'][0]
            print("Sample of first story:")
            print(f"Headline: {first_story['headline']}")
            print(f"URL: {first_story['url']}")
            
            if 'description' in first_story:
                desc_length = len(first_story['description'])
                print(f"Description length: {desc_length} characters")
                
                # Print preview of description
                if first_story['description']:
                    preview = (first_story['description'][:200] + "..." 
                             if len(first_story['description']) > 200 
                             else first_story['description'])
                    print(f"Description preview: {preview}")
            
            if 'local_images' in first_story:
                img_count = len(first_story['local_images'])
                print(f"Local images: {img_count}")
    
    # Abstract methods that must be implemented by subclasses
    @abstractmethod
    def scrape_stories(self) -> List[Dict]:
        """Scrape basic story information from the main page"""
        pass
    
    @abstractmethod
    def scrape_story_details(self, story_url: str) -> Optional[Dict]:
        """Scrape detailed content from an individual story page"""
        pass