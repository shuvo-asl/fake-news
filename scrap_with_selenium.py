# prothom_alo_selenium_scraper.py

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import time
from datetime import datetime
import os


class ProthomAloSeleniumScraper:
    def __init__(self, headless=True):
        """Initialize the scraper with Chrome WebDriver"""
        self.headless = headless
        self.driver = None
        self.base_url = "https://www.prothomalo.com"
        self.education_url = f"{self.base_url}/education"
        
    def setup_driver(self):
        """Setup Chrome WebDriver with webdriver-manager"""
        # Setup Chrome options
        chrome_options = webdriver.ChromeOptions()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # Additional options for better performance and stability
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Use webdriver-manager to automatically manage ChromeDriver
        service = Service(ChromeDriverManager().install())
        
        # Create WebDriver instance
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        
        print("Chrome WebDriver initialized successfully")
    
    def click_load_more(self):
        """Click the 'Load More' button if it exists"""
        try:
            # Try different possible selectors for the load more button
            selectors = [
                "div.more._7ZpjE",
                ".load-more",
                "[data-testid='load-more']",
                "button:contains('Load More')",
                ".more-button",
                "div[class*='more']",
                "div[class*='load']"
            ]
            
            for selector in selectors:
                try:
                    if 'contains' in selector:
                        # Handle text-based selectors
                        elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), 'Load More')]")
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                self.driver.execute_script("arguments[0].click();", element)
                                time.sleep(2)
                                return True
                    else:
                        load_more_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if load_more_button.is_displayed() and load_more_button.is_enabled():
                            self.driver.execute_script("arguments[0].click();", load_more_button)
                            time.sleep(2)
                            return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            print(f"Error clicking load more button: {e}")
            return False
    
    def scrape_education_stories(self):
        """Scrape education stories from Prothom Alo"""
        if not self.driver:
            self.setup_driver()
        
        try:
            print(f"Loading Prothom Alo education page: {self.education_url}")
            self.driver.get(self.education_url)
            
            # Wait for the page to load completely
            time.sleep(5)

            # Scroll to the bottom to load more stories if necessary
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Click "Load More" button if it exists
            try:
                # load_more_button = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'span.load-more-content _7QoIj')))
                # load_more_button.click()
                load_more_attempts = 0
                max_attempts = 20
                while load_more_attempts < max_attempts:
                    if not self.click_load_more():
                        break
                    load_more_attempts += 1

                time.sleep(3)  # Wait for more stories to load
            except (TimeoutException, NoSuchElementException):
                print("No 'Load More' button found or it is not clickable")

            elements = self.driver.find_elements(By.CSS_SELECTOR, 'a.title-link')
            print(f"Found {len(elements)} story links")

        except TimeoutException:
            print("Timeout while loading the page")
            return []
        except Exception as e:
            print(f"An error occurred: {e}")
            return []
        finally:
            self.driver.quit()


if __name__ == "__main__":
    scraper = ProthomAloSeleniumScraper(headless=False)
    scraper.scrape_education_stories()