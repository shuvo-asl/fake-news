# daily_star_scraper.py
from core.base import BaseNewsScraper
from datetime import datetime
from urllib.parse import urljoin
from typing import List, Dict, Optional


class DailyStarScraper(BaseNewsScraper):
    """
    Scraper for The Daily Star education news
    """
    
    def __init__(self):
        super().__init__(
            source_name="The Daily Star - Education",
            base_url="https://www.thedailystar.net"
        )
        self.education_url = f"{self.base_url}/tags/education"
    
    def scrape_stories(self) -> List[Dict]:
        """Scrape basic story information from Daily Star education page"""
        response = self.make_request(self.education_url)
        if not response:
            return []
        
        soup = self.parse_html(response)
        if not soup:
            return []
        
        cards = soup.find_all('div', {'class': 'card'})
        stories = []
        
        for card in cards:
            story = self._extract_card_info(card)
            if story:
                stories.append(story)
        
        return stories
    
    def _extract_card_info(self, card) -> Optional[Dict]:
        """Extract information from a Daily Star card element"""
        story = {
            'headline': None,
            'url': None,
            'hero_image_url': None,
            'last_published_at': None,
            'scraped_at': datetime.now().isoformat()
        }
        
        # Extract title and link
        title_tag = card.find('h3', {'class': 'title'})
        if title_tag and title_tag.a:
            story['headline'] = title_tag.a.get_text(strip=True)
            story['url'] = urljoin(self.base_url, title_tag.a['href'])
        else:
            return None
        
        # Extract hero image
        image_div = card.find('div', {'class': 'card-image'})
        if image_div:
            img_element = (image_div.a.picture.img 
                         if image_div.a and image_div.a.picture and image_div.a.picture.img 
                         else None)
            if img_element and img_element.get('data-srcset'):
                story['hero_image_url'] = img_element['data-srcset']
        
        # Extract published date
        time_tag = card.find('time')
        if time_tag:
            story['last_published_at'] = time_tag.get('datetime', '')
        
        return story
    
    def scrape_story_details(self, story_url: str) -> Optional[Dict]:
        """Scrape detailed content from an individual Daily Star news page"""
        response = self.make_request(story_url)
        if not response:
            return None
        
        soup = self.parse_html(response)
        if not soup:
            return None
        
        # Find the article section
        story_div = soup.find('article', {'class': 'article-section'})
        if not story_div:
            print(f"No article section found for {story_url}")
            return None
        
        story_details = self._extract_article_details(story_div, story_url)
        return story_details
    
    def _extract_article_details(self, story_div, story_url: str) -> Dict:
        """Extract detailed information from article section"""
        story_details = {
            'headline': '',
            'description': '',
            'image_urls': [],
            'scraped_at': datetime.now().isoformat()
        }
        
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
                img_element = (tag.picture.img 
                             if tag.picture and tag.picture.img 
                             else None)
                if img_element and img_element.get('data-srcset'):
                    story_details['image_urls'].append(img_element['data-srcset'])
        
        # Extract story description
        story_content_div = story_div.find('div', {'class': 'clearfix'})
        if story_content_div:
            story_paragraphs = story_content_div.find_all('p', class_=False)
            description_parts = []
            
            for p in story_paragraphs:
                text = p.get_text(strip=True)
                if text:
                    description_parts.append(text)
            
            story_details['description'] = "\n\n".join(description_parts)
        
        # Handle image downloads
        slug = self.create_slug_from_url(story_url)
        local_images = self.download_images(
            story_details['image_urls'], slug, "daily_star"
        )
        
        # Download hero image if available (from the original story data)
        hero_image_local = None
        # Note: hero image URL would need to be passed separately or extracted here
        
        story_details.update({
            'slug': slug,
            'local_images': local_images,
            'hero_image_local': hero_image_local
        })
        
        return story_details
    
    def scrape_all_details(self, story_list: List[Dict], max_stories: int = None, 
                          delay: int = 1) -> List[Dict]:
        """Override to handle hero image downloads"""
        detailed_stories = []
        
        if max_stories:
            story_list = story_list[:max_stories]
        
        for i, story in enumerate(story_list, 1):
            print(f"Scraping Daily Star story {i}/{len(story_list)}: {story['headline']}")
            
            story_details = self.scrape_story_details(story['url'])
            if story_details:
                # Generate slug and download hero image
                slug = story_details['slug']
                
                # Download hero image if it exists in original story
                hero_image_local = None
                if story.get('hero_image_url'):
                    hero_image_local = self.download_image(
                        story['hero_image_url'], slug, "hero", "daily_star"
                    )
                    if hero_image_local:
                        story_details['local_images'].append(hero_image_local)
                
                # Merge all data
                merged_story = {
                    **story,
                    **story_details,
                    'hero_image_local': hero_image_local
                }
                detailed_stories.append(merged_story)
            else:
                print(f"Failed to scrape details for: {story['headline']}")
            
            import time
            time.sleep(delay)
        
        return detailed_stories


def main():
    scraper = DailyStarScraper()
    scraper.run_complete_scrape(delay=2)


if __name__ == "__main__":
    main()