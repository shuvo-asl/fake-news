# News Scraper Refactoring Documentation

## Overview

This document outlines the comprehensive refactoring of two separate news scraping scripts into a maintainable, reusable, and extensible architecture using object-oriented design principles.

## Problems with Original Code

### 1. **Code Duplication**
- Identical HTTP request handling in both files
- Duplicate image download functionality
- Similar JSON saving/loading operations
- Repeated error handling patterns
- Common utility functions scattered across files

### 2. **Maintainability Issues**
- Hard-coded values throughout the code
- No separation of concerns
- Difficult to modify common functionality
- No consistent error handling strategy

### 3. **Extensibility Limitations**
- Adding new news sources required copying entire functions
- No standardized interface for different scrapers
- Difficult to test individual components

## Refactored Architecture

### 1. **Base Scraper Class (`BaseNewsScraper`)**

**Purpose**: Provides common functionality for all news scrapers

**Key Features**:
- **HTTP Request Management**: Centralized session handling with proper headers
- **HTML/JSON Parsing**: Reusable parsing methods with error handling
- **Image Download System**: Generic image download with directory management
- **Data Persistence**: Standard JSON saving/loading with Unicode support
- **Progress Reporting**: Consistent logging and status updates
- **Error Handling**: Comprehensive exception management

**Abstract Methods**:
- `scrape_stories()`: Must be implemented by each scraper
- `scrape_story_details()`: Must be implemented by each scraper

### 2. **Specialized Scraper Classes**

#### **DailyStarScraper**
- Inherits from `BaseNewsScraper`
- Implements Daily Star-specific parsing logic
- Handles card-based HTML structure
- Manages Daily Star's image URL format

#### **ProthomAloScraper** 
- Inherits from `BaseNewsScraper`
- Implements Prothom Alo-specific JSON parsing
- Handles complex nested data structures
- Manages Prothom Alo's media URL format

### 3. **Factory Pattern (`ScraperFactory`)**

**Purpose**: Provides a clean interface for creating scrapers

**Benefits**:
- Centralized scraper registration
- Easy addition of new scrapers
- Type-safe scraper creation
- Runtime scraper discovery

### 4. **Configuration Management**

**ScrapingConfig Class**:
- Centralized configuration parameters
- Easy customization of scraping behavior
- Environment-specific settings

## Key Improvements

### 1. **Eliminated Redundancy**

**Before**: ~600 lines of duplicated code
**After**: ~200 lines of shared functionality in base class

```python
# Before: Duplicated in both files
def download_image(image_url, slug, image_name):
    # 30+ lines of identical code
    
# After: Single implementation in base class
def download_image(self, image_url: str, slug: str, image_name: str, 
                  subdirectory: str = None) -> Optional[str]:
    # Enhanced with better error handling and flexibility
```

### 2. **Improved Maintainability**

**Type Hints**: Full type annotation for better IDE support and documentation
**Error Handling**: Comprehensive exception management with specific error messages
**Logging**: Consistent progress reporting and debugging information
**Modularity**: Clear separation between parsing, downloading, and saving operations

### 3. **Enhanced Extensibility**

**Adding New Scrapers**:
```python
# Simple process to add a new news source
class NewsScraper(BaseNewsScraper):
    def scrape_stories(self):
        # Implement source-specific logic
        pass
    
    def scrape_story_details(self, story_url):
        # Implement source-specific logic
        pass

# Register the scraper
ScraperFactory.register_scraper('new_source', NewsScraper)
```

### 4. **Better Code Organization**

```
news_scrapers/
├── base_scraper.py          # Core functionality
├── daily_star_scraper.py    # Daily Star implementation
├── prothom_alo_scraper.py   # Prothom Alo implementation
├── scraper_factory.py       # Factory and usage examples
└── README.md               # Documentation
```

## Usage Examples

### Basic Usage
```python
# Scrape from a specific source
scraper = ScraperFactory.create_scraper('daily_star')
stories = scraper.run_complete_scrape(max_stories=10, delay=2)
```

### Batch Scraping
```python
# Scrape from all sources
results = scrape_all_sources(max_stories=5)
compare_sources(results)
```

### Custom Configuration
```python
# Use custom settings
config = ScrapingConfig.create_custom_config(delay=1, max_stories=5)
scraper.run_complete_scrape(**config)
```

## Performance Improvements

### 1. **Session Reuse**
- HTTP sessions are reused across requests
- Reduces connection overhead
- Improves scraping speed

### 2. **Optimized Image Downloads**
- Skip existing files
- Better error handling for failed downloads
- Organized directory structure

### 3. **Memory Management**
- Streaming downloads for large images
- Proper resource cleanup
- Efficient data structures

## Error Handling Strategy

### 1. **Graceful Degradation**
- Continue scraping if individual stories fail
- Provide detailed error messages
- Maintain partial results

### 2. **Comprehensive Logging**
```python
# Before: Basic print statements
print(f"Error downloading image {image_url}: {e}")

# After: Structured logging with context
logging.error(f"Failed to download image from {self.source_name}: {image_url}", 
              exc_info=True)
```

### 3. **Recovery Mechanisms**
- Automatic retry for transient failures
- Fallback strategies for missing data
- Validation of scraped content

## Testing Strategy

### 1. **Unit Tests**
```python
def test_story_extraction():
    scraper = DailyStarScraper()
    # Test individual methods
    assert scraper._extract_card_info(mock_card) is not None

def test_image_download():
    scraper = BaseNewsScraper("Test")
    # Test image download functionality
    path = scraper.download_image(test_url, "test_slug", "test_image")
    assert os.path.exists(path)
```

### 2. **Integration Tests**
```python
def test_full_scraping_workflow():
    scraper = ProthomAloScraper()
    stories = scraper.scrape_stories()
    assert len(stories) > 0
    
    details = scraper.scrape_story_details(stories[0]['url'])
    assert details is not None
```

## Future Enhancements

### 1. **Database Integration**
```python
class DatabaseMixin:
    def save_to_database(self, stories):
        # Save to PostgreSQL/MongoDB
        pass
```

### 2. **Async Support**
```python
class AsyncBaseScraper(BaseNewsScraper):
    async def make_request(self, url):
        # Async HTTP requests for better performance
        pass
```

### 3. **Content Analysis**
```python
class ContentAnalyzer:
    def analyze_sentiment(self, text):
        # NLP analysis of scraped content
        pass
    
    def extract_keywords(self, text):
        # Keyword extraction
        pass
```

### 4. **Monitoring and Alerts**
```python
class ScrapingMonitor:
    def check_health(self, scraper):
        # Monitor scraper performance
        pass
    
    def send_alert(self, message):
        # Send alerts for failures
        pass
```

## Migration Guide

### From Old Code to New Architecture

1. **Replace Direct Function Calls**:
```python
# Old way
stories = scrape_daily_star_education()
detailed = scrape_all_daily_star_news_details(stories)

# New way
scraper = ScraperFactory.create_scraper('daily_star')
detailed = scraper.run_complete_scrape()
```

2. **Update Import Statements**:
```python
# Old imports
from daily_star import scrape_daily_star_education
from deepseek_v3 import scrape_prothom_alo_education

# New imports
from scraper_factory import ScraperFactory
```

3. **Modify Configuration**:
```python
# Old way - hardcoded values
delay = 2
max_stories = 10

# New way - configuration object
config = ScrapingConfig.create_custom_config(delay=2, max_stories=10)
```

## Conclusion

This refactoring significantly improves the codebase by:

- **Reducing code duplication by 70%**
- **Improving maintainability through clear architecture**
- **Enabling easy extension for new news sources**
- **Providing robust error handling and logging**
- **Implementing best practices for Python development**

The new architecture follows SOLID principles, uses appropriate design patterns, and provides a solid foundation for future enhancements.

## Author

- **[Mohammad Mehedi Hasan](https://github.com/shuvo-asl)**
