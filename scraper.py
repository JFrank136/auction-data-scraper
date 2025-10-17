import os
import time
import logging
import requests
import json
import base64
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

from config import SEARCH_TERMS, FILTERS, SCRAPING_CONFIG, CINCINNATI_LOCATIONS, OUTPUT_DIR, IMAGES_DIR

class BidFTAScraper:
    def __init__(self):
        self.setup_logging()
        self.setup_directories()
        self.driver = None
        self.base_url = "https://www.bidft.auction"
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('auction_scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_directories(self):
        """Create necessary directories"""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(IMAGES_DIR, exist_ok=True)
        
    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        if SCRAPING_CONFIG['headless']:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, SCRAPING_CONFIG['wait_time'])
        
    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            
    def get_week_date_range(self):
        """Calculate this week's Sunday to Sunday date range (includes full weekend)"""
        now = datetime.now()
        
        # Find this Sunday (start of week)
        days_since_sunday = (now.weekday() + 1) % 7  # Monday=0, Sunday=6, convert to Sunday=0
        sunday = now - timedelta(days=days_since_sunday)
        
        # Find next Sunday (end of week) - this includes Saturday auctions
        next_sunday = sunday + timedelta(days=7)
        
        # Format for BidFT (they seem to use ISO format with T04:00:00.000Z)
        sunday_str = sunday.strftime('%Y-%m-%dT04:00:00.000Z')
        next_sunday_str = next_sunday.strftime('%Y-%m-%dT04:00:00.000Z')
        
        self.logger.info(f"Week range: {sunday.strftime('%Y-%m-%d')} to {next_sunday.strftime('%Y-%m-%d')} (includes Saturday)")
        
        return sunday_str, next_sunday_str
            
    def build_search_url(self, search_term: str) -> str:
        """Build the encoded search URL like BidFT uses"""
        
        sunday_str, next_sunday_str = self.get_week_date_range()
        
        # Build the search parameters object
        search_params = {
            "searchTerm": search_term,
            "locations": CINCINNATI_LOCATIONS,
            "conditions": FILTERS['condition'],
            "sort": "DATE_ASC",  # Oldest first, like in your screenshot
            "newerThan": sunday_str,  # Ends after Sunday
            "olderThan": next_sunday_str,  # Ends before next Sunday (includes Saturday)
            "ended": False  # Only active auctions
        }
        
        # Convert to JSON and encode like BidFT does
        json_str = json.dumps(search_params, separators=(',', ':'))
        encoded_params = base64.b64encode(json_str.encode()).decode()
        
        url = f"{self.base_url}/archive?searchSettings={encoded_params}"
        
        self.logger.info(f"Built search URL for '{search_term}' (BidFTA)")
        self.logger.debug(f"Search params: {search_params}")
        
        return url
        
    def download_image(self, image_url: str, filename: str) -> Optional[str]:
        """Download and save auction item image"""
        try:
            if not image_url or image_url.startswith('data:'):
                return None
                
            response = requests.get(image_url, timeout=10)
            if response.status_code == 200:
                filepath = os.path.join(IMAGES_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return filepath
        except Exception as e:
            self.logger.warning(f"Failed to download image {image_url}: {str(e)}")
        return None
        
    def extract_auction_from_row(self, row_element, search_term: str) -> Optional[Dict]:
        """Extract auction data from a table row with improved URL extraction"""
        try:
            # Get all cells in the row
            cells = row_element.find_elements(By.TAG_NAME, 'td')
            
            if len(cells) < 7:  # Should have PHOTO, DESCRIPTION, AMAZON, CONDITION, LOCATION, ENDS AT, PRICE columns
                return None
            
            # === TITLE AND URL EXTRACTION WITH MULTIPLE STRATEGIES ===
            title = ""
            auction_url = ""
            
            # Strategy 1: Direct link in description cell (column 1)
            try:
                link_elem = cells[1].find_element(By.TAG_NAME, 'a')
                title = link_elem.text.strip()
                auction_url = link_elem.get_attribute('href')
                self.logger.debug(f"Strategy 1 success: Found direct link for {title[:30]}...")
            except NoSuchElementException:
                # Strategy 2: Look for clickable elements with data attributes
                try:
                    clickable_elements = cells[1].find_elements(By.XPATH, ".//*[@onclick or @data-href or @data-url or contains(@class, 'link') or contains(@class, 'clickable')]")
                    if clickable_elements:
                        elem = clickable_elements[0]
                        title = cells[1].text.strip()
                        auction_url = (elem.get_attribute('onclick') or 
                                     elem.get_attribute('data-href') or 
                                     elem.get_attribute('data-url') or
                                     elem.get_attribute('href'))
                        self.logger.debug(f"Strategy 2 success: Found clickable element")
                    else:
                        raise NoSuchElementException
                except:
                    # Strategy 3: Look anywhere in the row for auction links
                    try:
                        all_links = row_element.find_elements(By.TAG_NAME, 'a')
                        if all_links:
                            # Try each link to find the best one
                            for link in all_links:
                                href = link.get_attribute('href')
                                if href and ('itemDetails' in href or 'auction' in href):
                                    auction_url = href
                                    if not title:
                                        title = link.text.strip() or cells[1].text.strip()
                                    self.logger.debug(f"Strategy 3 success: Found auction link")
                                    break
                            
                            # If no auction-specific link found, use first link
                            if not auction_url and all_links:
                                auction_url = all_links[0].get_attribute('href')
                                self.logger.debug(f"Strategy 3 fallback: Using first available link")
                        else:
                            self.logger.debug(f"No links found in row")
                    except Exception as e:
                        self.logger.debug(f"Strategy 3 failed: {str(e)}")
                
                # Strategy 4: Extract title even if no URL
                if not title:
                    title = cells[1].text.strip()
                    self.logger.debug(f"Using cell text as title: {title[:30]}...")
            
            # Clean and make URL absolute
            if auction_url:
                # Clean up JavaScript onclick URLs
                if 'javascript:' in auction_url or 'onclick' in auction_url:
                    # Try to extract URL from JavaScript
                    url_match = re.search(r'(https?://[^\s\'"]+)', auction_url)
                    if url_match:
                        auction_url = url_match.group(1)
                        self.logger.debug(f"Extracted URL from JavaScript")
                
                # Make absolute
                if auction_url and not auction_url.startswith('http'):
                    if auction_url.startswith('/'):
                        auction_url = f"https://www.bidft.auction{auction_url}"
                    elif auction_url.startswith('www.bidfta.com'):
                        auction_url = f"https://{auction_url}"
                    else:
                        auction_url = f"https://www.bidft.auction/{auction_url}"
                    self.logger.debug(f"Made URL absolute")
            
            # === EXTRACT IMAGE URL (column 0) ===
            image_url = ""
            try:
                img_elem = cells[0].find_element(By.TAG_NAME, 'img')
                image_url = img_elem.get_attribute('src')
                if image_url and not image_url.startswith('http'):
                    image_url = urljoin(self.base_url, image_url)
            except NoSuchElementException:
                pass
            
            # === EXTRACT OTHER FIELDS ===
            # CONDITION (column 3)
            condition = cells[3].text.strip()
            
            # LOCATION (column 4)
            location = cells[4].text.strip()
            
            # ENDS AT (column 5)
            end_time = cells[5].text.strip()
            
            # PRICE (column 6)
            current_bid = cells[6].text.strip()
            
            # Download image
            image_path = None
            if image_url:
                image_filename = f"{hash(auction_url or title)}_{int(time.time())}.jpg"
                image_path = self.download_image(image_url, image_filename)
            
            auction_data = {
                'title': title,
                'url': auction_url,
                'current_bid': current_bid,
                'end_time': end_time,
                'location': location,
                'condition': condition,
                'image_url': image_url,
                'image_path': image_path,
                'search_term': search_term
            }
            
            self.logger.debug(f"Extracted auction: {title[:30]}... - {current_bid} - {location}")
            return auction_data
            
        except Exception as e:
            self.logger.error(f"Error extracting auction data from row: {str(e)}")
            return None
            
    def search_auctions(self, search_term: str) -> List[Dict]:
        """Search for auctions with given term"""
        auctions = []
        
        try:
            # Build and load the search URL
            search_url = self.build_search_url(search_term)
            self.logger.info(f"Loading search URL for '{search_term}'...")
            
            self.driver.get(search_url)
            
            # Wait for page to load
            time.sleep(8)
            
            self.logger.info(f"Page loaded: {self.driver.current_url}")
            
            # Wait for the results table to load
            try:
                # Look for table or tbody containing results
                table_selectors = [
                    'table tbody tr',
                    'tbody tr',
                    'table tr',
                    '[role="table"] [role="row"]',
                    '.table-row',
                    'tr'
                ]
                
                auction_rows = []
                for selector in table_selectors:
                    try:
                        rows = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if len(rows) > 1:  # More than just header
                            auction_rows = rows[1:]  # Skip header row
                            self.logger.info(f"Found {len(auction_rows)} auction rows with selector: {selector}")
                            break
                    except:
                        continue
                
                if not auction_rows:
                    self.logger.warning(f"No auction rows found for search term: {search_term}")
                    return auctions
                
                # Extract data from each row
                for row in auction_rows:
                    auction_data = self.extract_auction_from_row(row, search_term)
                    if auction_data and self.meets_criteria(auction_data):
                        auctions.append(auction_data)
                
                self.logger.info(f"Extracted {len(auctions)} valid auctions for '{search_term}'")
                
            except TimeoutException:
                self.logger.error(f"Timeout waiting for results for search term: {search_term}")
                
        except Exception as e:
            self.logger.error(f"Error searching for {search_term}: {str(e)}")
            
        return auctions
        
    def meets_criteria(self, auction_data: Dict) -> bool:
        """Check if auction meets our filtering criteria"""
        
        # Check if we have required data
        if not auction_data.get('title') or not auction_data.get('location'):
            return False
        
        # Location is already filtered by the URL parameters, but double-check
        location = auction_data.get('location', '').lower()
        location_match = any(
            cin_location.lower() in location 
            for cin_location in CINCINNATI_LOCATIONS
        )
        
        if not location_match:
            self.logger.debug(f"Location filter failed for: {location}")
            return False
            
        # Condition is already filtered by URL parameters, but double-check
        condition = auction_data.get('condition', '').lower()
        condition_match = any(
            filter_condition.lower() in condition 
            for filter_condition in FILTERS['condition']
        )
        
        if not condition_match:
            self.logger.debug(f"Condition filter failed for: {condition}")
            return False
            
        return True
        
    def remove_duplicates(self, auctions: List[Dict]) -> List[Dict]:
        """Remove duplicate auctions based on URL or title"""
        seen_urls = set()
        seen_titles = set()
        unique_auctions = []
        
        for auction in auctions:
            url = auction.get('url', '')
            title = auction.get('title', '').lower().strip()
            
            # Check URL first (most reliable)
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_auctions.append(auction)
            # If no URL, check title
            elif not url and title and title not in seen_titles:
                seen_titles.add(title)
                unique_auctions.append(auction)
            # If duplicate found, log it
            elif url and url in seen_urls:
                self.logger.debug(f"Duplicate URL filtered: {url}")
            elif title and title in seen_titles:
                self.logger.debug(f"Duplicate title filtered: {title[:30]}...")
                
        return unique_auctions
        
    def scrape_all_searches(self) -> List[Dict]:
        """Scrape auctions for all search terms"""
        all_auctions = []
        
        self.setup_driver()
        
        try:
            for search_term in SEARCH_TERMS:
                self.logger.info(f"Starting search for: {search_term}")
                auctions = self.search_auctions(search_term)
                all_auctions.extend(auctions)
                self.logger.info(f"Found {len(auctions)} auctions for {search_term}")
                
                # Delay between searches
                time.sleep(SCRAPING_CONFIG['delay_between_searches'])
                
        finally:
            self.close_driver()
            
        # Remove duplicates
        unique_auctions = self.remove_duplicates(all_auctions)
        self.logger.info(f"Total unique auctions found: {len(unique_auctions)}")
        
        return unique_auctions

if __name__ == "__main__":  
    scraper = BidFTAScraper()
    auctions = scraper.scrape_all_searches()
    print(f"Found {len(auctions)} auctions")
    for auction in auctions[:3]:  # Print first 3 for testing
        print(f"- {auction['title']} - {auction['current_bid']} - {auction['location']}")
        print(f"  URL: {auction.get('url', 'No URL')}")