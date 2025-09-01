

# advanced_usage_example.py
"""
Advanced usage examples showing extensibility and customization
"""

class CustomNewsScraper(BaseNewsScraper):
    """Example of how to create a new scraper by extending the base class"""
    
    def __init__(self, source_name: str, url: str):
        super().__init__(source_name)
        self.url = url
    
    def scrape_stories(self):
        # Implement your custom logic here
        return []
    
    def scrape_story_details(self, story_url: str):
        # Implement your custom logic here
        return None


def register_custom_scraper():
    """Example of how to register a custom scraper"""
    # Register a custom scraper
    ScraperFactory.register_scraper(
        'custom_news',
        lambda: CustomNewsScraper("Custom News", "https://example.com/news")
    )


def batch_scraping_with_error_handling():
    """Example of robust batch scraping with comprehensive error handling"""
    import logging
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('scraping.log'),
            logging.StreamHandler()
        ]
    )
    
    results = {}
    failed_sources = []
    
    for source in ScraperFactory.get_available_scrapers():
        try:
            logging.info(f"Starting scrape for {source}")
            scraper = ScraperFactory.create_scraper(source)
            
            # Custom configuration for each scraper
            if source == 'daily_star':
                stories = scraper.run_complete_scrape(max_stories=5, delay=3)
            else:
                stories = scraper.run_complete_scrape(max_stories=10, delay=2)
            
            results[source] = stories
            logging.info(f"Successfully scraped {len(stories)} stories from {source}")
            
        except Exception as e:
            logging.error(f"Failed to scrape {source}: {e}")
            failed_sources.append(source)
            results[source] = []
    
    # Generate comprehensive report
    generate_scraping_report(results, failed_sources)
    
    return results


def generate_scraping_report(results: Dict, failed_sources: list):
    """Generate a comprehensive scraping report"""
    from datetime import datetime
    
    report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\n{'='*80}")
    print(f"COMPREHENSIVE SCRAPING REPORT - {report_time}")
    print(f"{'='*80}")
    
    total_stories = sum(len(stories) for stories in results.values())
    successful_sources = [k for k, v in results.items() if v]
    
    print(f"Total Sources Attempted: {len(results)}")
    print(f"Successful Sources: {len(successful_sources)}")
    print(f"Failed Sources: {len(failed_sources)}")
    print(f"Total Stories Scraped: {total_stories}")
    
    if successful_sources:
        print(f"\n✅ SUCCESSFUL SOURCES:")
        for source in successful_sources:
            story_count = len(results[source])
            print(f"  • {source.title().replace('_', ' ')}: {story_count} stories")
    
    if failed_sources:
        print(f"\n❌ FAILED SOURCES:")
        for source in failed_sources:
            print(f"  • {source.title().replace('_', ' ')}")
    
    print(f"\n📊 DETAILED BREAKDOWN:")
    for source, stories in results.items():
        if stories:
            print(f"\n{source.title().replace('_', ' ')} ({len(stories)} stories):")
            for i, story in enumerate(stories[:3], 1):
                headline = story['headline'][:60] + "..." if len(story['headline']) > 60 else story['headline']
                print(f"  {i}. {headline}")
            if len(stories) > 3:
                print(f"  ... and {len(stories) - 3} more stories")


# Configuration and utilities
class ScrapingConfig:
    """Configuration class for scraping parameters"""
    
    DEFAULT_DELAY = 2
    DEFAULT_TIMEOUT = 30
    DEFAULT_MAX_STORIES = None
    DEFAULT_DATA_DIR = "data"
    
    @classmethod
    def create_custom_config(cls, **kwargs):
        """Create a custom configuration"""
        config = {
            'delay': kwargs.get('delay', cls.DEFAULT_DELAY),
            'timeout': kwargs.get('timeout', cls.DEFAULT_TIMEOUT),
            'max_stories': kwargs.get('max_stories', cls.DEFAULT_MAX_STORIES),
            'data_dir': kwargs.get('data_dir', cls.DEFAULT_DATA_DIR),
        }
        return config


def run_with_custom_config():
    """Example of running scrapers with custom configuration"""
    config = ScrapingConfig.create_custom_config(
        delay=1,
        max_stories=5,
        data_dir="custom_data"
    )
    
    for source in ScraperFactory.get_available_scrapers():
        scraper = ScraperFactory.create_scraper(source)
        stories = scraper.run_complete_scrape(
            max_stories=config['max_stories'],
            delay=config['delay']
        )
        print(f"Scraped {len(stories)} stories from {source} with custom config")