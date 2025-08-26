# prothom_alo_scraper.py
from core.base import BaseNewsScraper
from datetime import datetime
import json
import re
from typing import List, Dict, Optional, Any


class ProthomAloScraper(BaseNewsScraper):
    """
    Scraper for Prothom Alo education news
    """
    
    def __init__(self):
        super().__init__(
            source_name="Prothom Alo Education",
            base_url="https://www.prothomalo.com"
        )
        self.education_url = f"{self.base_url}/education"
        self.media_base_url = "https://media.prothomalo.com/"
    
    def scrape_stories(self) -> List[Dict]:
        """Scrape basic story information from Prothom Alo education page"""
        response = self.make_request(self.education_url)
        if not response:
            return []
        
        soup = self.parse_html(response)
        if not soup:
            return []
        
        # Extract JSON data from script tags
        json_data_list = self.parse_json_from_script(soup)
        
        stories = []
        for data in json_data_list:
            if 'qt' in data and 'data' in data['qt']:
                qt_data = data['qt']['data']
                stories.extend(self._traverse_collections(qt_data))
        
        # Remove duplicates by slug
        return self._remove_duplicate_stories(stories)
    
    def _traverse_collections(self, data: Any) -> List[Dict]:
        """Recursively traverse through collections to find all stories"""
        stories = []
        
        if isinstance(data, dict):
            if data.get('type') == 'collection' and 'items' in data:
                for item in data['items']:
                    stories.extend(self._traverse_collections(item))
            elif data.get('type') == 'story':
                story_data = data.get('story', data)
                story = self._extract_story_info(story_data)
                if story:
                    stories.append(story)
            else:
                for value in data.values():
                    if isinstance(value, (dict, list)):
                        stories.extend(self._traverse_collections(value))
        
        elif isinstance(data, list):
            for item in data:
                stories.extend(self._traverse_collections(item))
        
        return stories
    
    def _extract_story_info(self, story_data: Dict) -> Optional[Dict]:
        """Extract required information from a story object"""
        try:
            headline = story_data.get('headline')
            slug = story_data.get('slug')
            
            if not headline or not slug:
                return None
            
            # Extract hero image
            hero_image_s3_key = story_data.get('hero-image-s3-key')
            hero_image_url = None
            if hero_image_s3_key:
                hero_image_url = f"{self.media_base_url}{hero_image_s3_key}"
            
            return {
                'headline': headline,
                'slug': slug,
                'url': f"{self.base_url}/{slug}",
                'last_published_at': story_data.get('last-published-at'),
                'hero_image_url': hero_image_url,
                'scraped_at': datetime.now().isoformat()
            }
        
        except Exception as e:
            print(f"Error extracting story info: {e}")
            return None
    
    def _remove_duplicate_stories(self, stories: List[Dict]) -> List[Dict]:
        """Remove duplicate stories by slug"""
        unique_stories = []
        seen_slugs = set()
        
        for story in stories:
            if story and story['slug'] not in seen_slugs:
                seen_slugs.add(story['slug'])
                unique_stories.append(story)
        
        return unique_stories
    
    def scrape_story_details(self, story_url: str) -> Optional[Dict]:
        """Scrape detailed content from an individual Prothom Alo news page"""
        response = self.make_request(story_url)
        if not response:
            return None
        
        soup = self.parse_html(response)
        if not soup:
            return None
        
        # Extract JSON data from script tags
        json_data_list = self.parse_json_from_script(soup)
        
        for data in json_data_list:
            try:
                if 'qt' in data and 'data' in data['qt']:
                    qt_data = data['qt']['data']['story']
                    story_details = self._extract_story_details(qt_data, story_url)
                    if story_details:
                        return story_details
            except (KeyError, TypeError) as e:
                continue
            except Exception as e:
                print(f"Error processing JSON for {story_url}: {e}")
                continue
        
        return None
    
    def _extract_story_details(self, story_data: Dict, story_url: str) -> Dict:
        """Extract detailed information from a story object"""
        try:
            # Extract basic information
            headline = story_data.get('headline', '')
            slug = story_data.get('slug', '')
            last_published_at = story_data.get('last-published-at', '')
            
            # Extract hero image
            hero_image_s3_key = story_data.get('hero-image-s3-key', '')
            hero_image_url = None
            if hero_image_s3_key:
                hero_image_url = f"{self.media_base_url}{hero_image_s3_key}"
            
            # Extract content from cards
            description, image_urls = self._extract_content_from_cards(
                story_data.get('cards', [])
            )
            
            # Handle image downloads
            slug = slug or self.create_slug_from_url(story_url)
            local_images = self.download_images(image_urls, slug)
            
            # Download hero image
            hero_image_local = None
            if hero_image_url:
                hero_image_local = self.download_image(hero_image_url, slug, "hero")
            
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
                'scraped_at': datetime.now().isoformat()
            }
        
        except Exception as e:
            print(f"Error extracting story details: {e}")
            return None
    
    def _extract_content_from_cards(self, cards: List[Dict]) -> tuple[str, List[str]]:
        """Extract description and image URLs from story cards"""
        description = ""
        image_urls = []
        
        for card in cards:
            story_elements = card.get('story-elements', [])
            for element in story_elements:
                element_type = element.get('type', '')
                subtype = element.get('subtype', '')
                
                # Only process elements with null subtype
                if subtype is None:
                    if element_type in ['text', 'title']:
                        text = element.get('text', '')
                        if text:
                            # Clean up text (remove HTML tags if any)
                            text = re.sub('<[^<]+?>', '', text)
                            description += text + "\n\n"
                    
                    elif element_type == 'image':
                        image_s3_key = element.get('image-s3-key', '')
                        if image_s3_key:
                            image_url = f"{self.media_base_url}{image_s3_key}"
                            image_urls.append(image_url)
        
        return description, image_urls


def main():
    scraper = ProthomAloScraper()
    scraper.run_complete_scrape(delay=2)


if __name__ == "__main__":
    main()