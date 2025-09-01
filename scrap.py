# scraper_factory.py
from typing import Dict, Type
from core.base import BaseNewsScraper
from scrapper.daily_star import DailyStarScraper
from scrapper.prothom_alo import ProthomAloScraper


class ScraperFactory:
    """
    Factory class for creating different news scrapers
    """
    
    _scrapers: Dict[str, Type[BaseNewsScraper]] = {
        'daily_star': DailyStarScraper,
        'prothom_alo': ProthomAloScraper,
    }
    
    @classmethod
    def create_scraper(cls, scraper_type: str) -> BaseNewsScraper:
        """Create a scraper instance based on type"""
        scraper_class = cls._scrapers.get(scraper_type.lower())
        if not scraper_class:
            available = ', '.join(cls._scrapers.keys())
            raise ValueError(f"Unknown scraper type: {scraper_type}. "
                           f"Available types: {available}")
        return scraper_class()
    
    @classmethod
    def get_available_scrapers(cls) -> list:
        """Get list of available scraper types"""
        return list(cls._scrapers.keys())
    
    @classmethod
    def register_scraper(cls, name: str, scraper_class: Type[BaseNewsScraper]):
        """Register a new scraper type"""
        cls._scrapers[name] = scraper_class


# usage_example.py
def scrape_single_source(source: str, max_stories: int = None):
    """Scrape news from a single source"""
    try:
        scraper = ScraperFactory.create_scraper(source)
        return scraper.run_complete_scrape(max_stories=max_stories, delay=2)
    except ValueError as e:
        print(f"Error: {e}")
        return []


def scrape_all_sources(max_stories: int = None):
    """Scrape news from all available sources"""
    all_results = {}
    
    for source in ScraperFactory.get_available_scrapers():
        print(f"\n{'='*60}")
        print(f"Starting scrape for: {source}")
        print(f"{'='*60}")
        
        try:
            scraper = ScraperFactory.create_scraper(source)
            results = scraper.run_complete_scrape(max_stories=max_stories, delay=2)
            all_results[source] = results
            print(f"✅ Successfully scraped {len(results)} stories from {source}")
        except Exception as e:
            print(f"❌ Error scraping {source}: {e}")
            all_results[source] = []
    
    return all_results


def compare_sources(results: Dict):
    """Compare results from different sources"""
    print(f"\n{'='*60}")
    print("SCRAPING SUMMARY")
    print(f"{'='*60}")
    
    total_stories = 0
    for source, stories in results.items():
        count = len(stories)
        total_stories += count
        print(f"{source.title().replace('_', ' ')}: {count} stories")
    
    print(f"Total stories across all sources: {total_stories}")
    
    if total_stories > 0:
        print(f"\nSample headlines from each source:")
        for source, stories in results.items():
            if stories:
                print(f"\n{source.title().replace('_', ' ')}:")
                for i, story in enumerate(stories[:3], 1):
                    print(f"  {i}. {story['headline'][:80]}...")


def main():
    """Main function demonstrating different usage patterns"""
    import argparse
    
    parser = argparse.ArgumentParser(description='News Scraper')
    parser.add_argument('--source', type=str, 
                       help=f"Specific source to scrape. Options: {', '.join(ScraperFactory.get_available_scrapers())}")
    parser.add_argument('--max-stories', type=int, default=0,
                       help='Maximum number of stories to scrape per source')
    parser.add_argument('--all', action='store_true',
                       help='Scrape from all available sources')
    
    args = parser.parse_args()
    
    if args.source:
        # Scrape from specific source
        print(f"Scraping from {args.source}...")
        results = scrape_single_source(args.source, args.max_stories)
        print(f"Scraped {len(results)} stories from {args.source}")
        
    elif args.all:
        # Scrape from all sources
        print("Scraping from all available sources...")
        results = scrape_all_sources(args.max_stories)
        compare_sources(results)
        
    else:
        # Interactive mode
        available_scrapers = ScraperFactory.get_available_scrapers()
        print("Available news sources:")
        for i, source in enumerate(available_scrapers, 1):
            print(f"{i}. {source.title().replace('_', ' ')}")
        print(f"{len(available_scrapers) + 1}. All sources")
        
        try:
            choice = input(f"\nSelect a source (1-{len(available_scrapers) + 1}): ").strip()
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(available_scrapers):
                selected_source = available_scrapers[choice_num - 1]
                max_stories = input("Max stories (press Enter for all): ").strip()
                max_stories = int(max_stories) if max_stories else None
                
                results = scrape_single_source(selected_source, max_stories)
                print(f"Scraped {len(results)} stories from {selected_source}")
                
            elif choice_num == len(available_scrapers) + 1:
                max_stories = input("Max stories per source (press Enter for all): ").strip()
                max_stories = int(max_stories) if max_stories else None
                
                results = scrape_all_sources(max_stories)
                compare_sources(results)
                
            else:
                print("Invalid choice!")
                
        except ValueError:
            print("Please enter a valid number!")
        except KeyboardInterrupt:
            print("\nScraping cancelled by user.")


if __name__ == "__main__":
    main()