#!/usr/bin/env python3
"""
Comprehensive BidFTA Auction Scraper Debug Tool

This single debug script can test:
- All search terms or specific ones
- Different date ranges
- URL extraction improvements
- Detailed criteria checking
- Page content analysis

Usage:
    py comprehensive_debug.py                    # Test all search terms
    py comprehensive_debug.py --term cat         # Test specific term
    py comprehensive_debug.py --term trash       # Test trash specifically
    py comprehensive_debug.py --all-dates        # Ignore date restrictions
    py comprehensive_debug.py --max-auctions 10  # Limit how many to process
    py comprehensive_debug.py --show-page        # Show page content if no results
"""

import argparse
import os
import time
import logging
import json
import base64
from datetime import datetime, timedelta
from urllib.parse import urljoin
from typing import List, Dict, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from config import SEARCH_TERMS, FILTERS, SCRAPING_CONFIG, CINCINNATI_LOCATIONS

class ComprehensiveDebugger:
    def __init__(self, headless=True):
        self.driver = None
        self.base_url = "https://www.bidft.auction"
        self.headless = headless
        
    def setup_driver(self):
        """Setup Chrome WebDriver"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        return self.driver
    
    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
    
    def get_week_date_range(self, ignore_dates=False):
        """Calculate this week's Sunday to Saturday date range"""
        if ignore_dates:
            # Use a very wide date range
            now = datetime.now()
            start = now - timedelta(days=30)  # 30 days ago
            end = now + timedelta(days=30)    # 30 days ahead
            start_str = start.strftime('%Y-%m-%dT04:00:00.000Z')
            end_str = end.strftime('%Y-%m-%dT04:00:00.000Z')
            print(f"🗓️ Using wide date range: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
            return start_str, end_str
        
        now = datetime.now()
        days_since_sunday = (now.weekday() + 1) % 7
        sunday = now - timedelta(days=days_since_sunday)
        saturday = sunday + timedelta(days=6)
        
        sunday_str = sunday.strftime('%Y-%m-%dT04:00:00.000Z')
        saturday_str = saturday.strftime('%Y-%m-%dT04:00:00.000Z')
        
        print(f"🗓️ Week range: {sunday.strftime('%Y-%m-%d')} to {saturday.strftime('%Y-%m-%d')}")
        return sunday_str, saturday_str

    def build_search_url(self, search_term: str, ignore_dates=False) -> str:
        """Build the encoded search URL"""
        sunday_str, saturday_str = self.get_week_date_range(ignore_dates)
        
        search_params = {
            "searchTerm": search_term,
            "locations": CINCINNATI_LOCATIONS,
            "conditions": FILTERS['condition'],
            "sort": "DATE_ASC",
            "newerThan": sunday_str,
            "olderThan": saturday_str,
            "ended": False
        }
        
        json_str = json.dumps(search_params, separators=(',', ':'))
        encoded_params = base64.b64encode(json_str.encode()).decode()
        url = f"{self.base_url}/archive?searchSettings={encoded_params}"
        
        print(f"🔗 Search URL: {url[:100]}...")
        return url

    def extract_auction_from_row_comprehensive(self, row_element, search_term: str, row_number: int) -> Optional[Dict]:
        """Comprehensive auction data extraction with multiple strategies"""
        try:
            cells = row_element.find_elements(By.TAG_NAME, 'td')
            print(f"\n--- 🔍 EXTRACTING ROW {row_number} ({len(cells)} cells) ---")
            
            if len(cells) < 7:
                print(f"❌ Row has only {len(cells)} cells, need at least 7")
                return None
            
            # === TITLE AND URL EXTRACTION ===
            title = ""
            auction_url = ""
            
            print(f"🔗 Searching for title and URL...")
            
            # Strategy 1: Direct link in description cell (column 1)
            try:
                link_elem = cells[1].find_element(By.TAG_NAME, 'a')
                title = link_elem.text.strip()
                auction_url = link_elem.get_attribute('href')
                print(f"✅ Strategy 1 - Direct link: {title[:50]}...")
                print(f"✅ URL: {auction_url}")
            except NoSuchElementException:
                print(f"❌ Strategy 1 failed - No direct link in description")
                
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
                        print(f"✅ Strategy 2 - Clickable element: {title[:50]}...")
                        print(f"✅ URL from attribute: {auction_url}")
                    else:
                        print(f"❌ Strategy 2 failed - No clickable elements")
                except Exception as e:
                    print(f"❌ Strategy 2 error: {str(e)}")
                
                # Strategy 3: Look anywhere in the row for links
                if not auction_url:
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
                                    print(f"✅ Strategy 3 - Found auction link: {auction_url}")
                                    break
                            
                            # If no auction-specific link found, use first link
                            if not auction_url and all_links:
                                auction_url = all_links[0].get_attribute('href')
                                print(f"⚠️ Strategy 3 - Using first available link: {auction_url}")
                        else:
                            print(f"❌ Strategy 3 failed - No links in row")
                    except Exception as e:
                        print(f"❌ Strategy 3 error: {str(e)}")
                
                # Strategy 4: Extract title even if no URL
                if not title:
                    title = cells[1].text.strip()
                    print(f"⚠️ Using cell text as title: {title[:50]}...")
            
            # Make URL absolute and clean
            if auction_url:
                # Clean up JavaScript onclick URLs
                if 'javascript:' in auction_url or 'onclick' in auction_url:
                    print(f"⚠️ JavaScript URL detected, trying to extract actual URL")
                    # Try to extract URL from JavaScript
                    import re
                    url_match = re.search(r'(https?://[^\s\'"]+)', auction_url)
                    if url_match:
                        auction_url = url_match.group(1)
                        print(f"✅ Extracted URL from JavaScript: {auction_url}")
                
                # Make absolute
                if auction_url and not auction_url.startswith('http'):
                    if auction_url.startswith('/'):
                        auction_url = f"https://www.bidft.auction{auction_url}"
                    elif auction_url.startswith('www.bidfta.com'):
                        auction_url = f"https://{auction_url}"
                    else:
                        auction_url = f"https://www.bidft.auction/{auction_url}"
                    print(f"🔗 Made URL absolute: {auction_url}")
            
            # === EXTRACT OTHER FIELDS ===
            condition = cells[3].text.strip()
            location = cells[4].text.strip()
            end_time = cells[5].text.strip()
            current_bid = cells[6].text.strip()
            
            # Try to get image URL (column 0)
            image_url = ""
            try:
                img_elem = cells[0].find_element(By.TAG_NAME, 'img')
                image_url = img_elem.get_attribute('src')
                if image_url and not image_url.startswith('http'):
                    image_url = urljoin(self.base_url, image_url)
                print(f"🖼️ Image URL: {image_url}")
            except NoSuchElementException:
                print(f"❌ No image found")
            
            print(f"📝 Condition: {condition}")
            print(f"📍 Location: {location}")
            print(f"⏰ End Time: {end_time}")
            print(f"💰 Current Bid: {current_bid}")
            
            auction_data = {
                'title': title,
                'url': auction_url,
                'current_bid': current_bid,
                'end_time': end_time,
                'location': location,
                'condition': condition,
                'image_url': image_url,
                'search_term': search_term,
                'row_number': row_number
            }
            
            return auction_data
            
        except Exception as e:
            print(f"❌ Error extracting auction data from row {row_number}: {str(e)}")
            import traceback
            print(f"🔍 Full error: {traceback.format_exc()}")
            return None

    def meets_criteria_debug(self, auction_data: Dict) -> bool:
        """Comprehensive criteria checking with detailed debug output"""
        title = auction_data.get('title', 'No title')
        print(f"\n🔍 === CRITERIA CHECK: {title[:50]}... ===")
        
        # Check required data
        if not auction_data.get('title'):
            print(f"❌ FAIL: Missing title")
            return False
        
        if not auction_data.get('location'):
            print(f"❌ FAIL: Missing location")
            return False
        
        # Location check
        location = auction_data.get('location', '').lower()
        print(f"🏠 Location Check: '{location}'")
        print(f"🏠 Checking against: {CINCINNATI_LOCATIONS}")
        
        location_match = False
        matched_location = ""
        for cin_location in CINCINNATI_LOCATIONS:
            if cin_location.lower() in location:
                location_match = True
                matched_location = cin_location
                print(f"✅ LOCATION MATCH: '{cin_location.lower()}' found in '{location}'")
                break
        
        if not location_match:
            print(f"❌ FAIL: Location '{location}' doesn't match any allowed locations")
            return False
        
        # Condition check
        condition = auction_data.get('condition', '').lower()
        print(f"🏷️ Condition Check: '{condition}'")
        print(f"🏷️ Checking against: {FILTERS['condition']}")
        
        condition_match = False
        matched_condition = ""
        for filter_condition in FILTERS['condition']:
            if filter_condition.lower() in condition:
                condition_match = True
                matched_condition = filter_condition
                print(f"✅ CONDITION MATCH: '{filter_condition.lower()}' found in '{condition}'")
                break
        
        if not condition_match:
            print(f"❌ FAIL: Condition '{condition}' doesn't match allowed conditions")
            return False
        
        print(f"✅ PASS: All criteria met!")
        print(f"   📍 Matched Location: {matched_location}")
        print(f"   🏷️ Matched Condition: {matched_condition}")
        return True

    def debug_search_term(self, search_term: str, ignore_dates=False, max_auctions=None, show_page_content=False) -> List[Dict]:
        """Debug a specific search term"""
        print(f"\n{'='*60}")
        print(f"🔍 DEBUGGING SEARCH: '{search_term}'")
        print(f"{'='*60}")
        
        try:
            # Build and load URL
            search_url = self.build_search_url(search_term, ignore_dates)
            print(f"⏳ Loading search page...")
            self.driver.get(search_url)
            time.sleep(8)
            
            print(f"✅ Page loaded: {self.driver.current_url[:100]}...")
            print(f"📄 Page title: {self.driver.title}")
            
            # Find auction rows
            auction_rows = []
            table_selectors = ['table tbody tr', 'tbody tr', 'table tr', '.auction-row', '[role="row"]']
            
            for selector in table_selectors:
                try:
                    rows = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(rows) > 1:  # More than header
                        auction_rows = rows[1:]  # Skip header
                        print(f"✅ Found {len(auction_rows)} auction rows with selector: '{selector}'")
                        break
                    elif len(rows) == 1:
                        print(f"⚠️ Found only 1 row with '{selector}' (likely header only)")
                except Exception as e:
                    print(f"❌ Selector '{selector}' failed: {str(e)}")
                    continue
            
            if not auction_rows:
                print(f"❌ No auction rows found for '{search_term}'")
                
                if show_page_content:
                    try:
                        body_text = self.driver.find_element(By.TAG_NAME, 'body').text
                        print(f"\n📄 PAGE CONTENT PREVIEW:")
                        print("-" * 50)
                        print(body_text[:1000])
                        if len(body_text) > 1000:
                            print(f"... (showing first 1000 of {len(body_text)} characters)")
                        print("-" * 50)
                    except:
                        print(f"❌ Could not retrieve page content")
                
                return []
            
            # Process auctions
            valid_auctions = []
            max_to_process = max_auctions if max_auctions else len(auction_rows)
            
            print(f"\n📊 Processing up to {max_to_process} of {len(auction_rows)} auction rows...")
            
            for i, row in enumerate(auction_rows[:max_to_process]):
                print(f"\n{'='*50}")
                print(f"PROCESSING AUCTION {i+1}/{max_to_process}")
                print(f"{'='*50}")
                
                auction_data = self.extract_auction_from_row_comprehensive(row, search_term, i+1)
                
                if auction_data:
                    # Show extracted data
                    print(f"\n📋 EXTRACTED DATA:")
                    for key, value in auction_data.items():
                        if key != 'row_number':
                            display_value = str(value)[:100] if len(str(value)) > 100 else str(value)
                            print(f"   {key}: {display_value}")
                    
                    # Check criteria
                    if self.meets_criteria_debug(auction_data):
                        valid_auctions.append(auction_data)
                        print(f"🎯 RESULT: ✅ ACCEPTED")
                    else:
                        print(f"🎯 RESULT: ❌ REJECTED")
                else:
                    print(f"🎯 RESULT: ❌ EXTRACTION FAILED")
            
            return valid_auctions
            
        except Exception as e:
            print(f"❌ Error debugging search term '{search_term}': {str(e)}")
            import traceback
            print(f"🔍 Full error: {traceback.format_exc()}")
            return []

    def run_comprehensive_debug(self, specific_term=None, ignore_dates=False, max_auctions=None, show_page_content=False):
        """Run comprehensive debugging"""
        print(f"🚀 COMPREHENSIVE BIDFTA DEBUG TOOL")
        print(f"📅 Date filtering: {'DISABLED' if ignore_dates else 'ENABLED'}")
        print(f"🔢 Max auctions per search: {max_auctions if max_auctions else 'UNLIMITED'}")
        
        self.setup_driver()
        
        try:
            # Determine which search terms to test
            if specific_term:
                search_terms = [specific_term]
                print(f"🎯 Testing specific term: '{specific_term}'")
            else:
                search_terms = SEARCH_TERMS
                print(f"🎯 Testing all configured terms: {search_terms}")
            
            all_results = {}
            total_valid_auctions = 0
            
            # Test each search term
            for term in search_terms:
                valid_auctions = self.debug_search_term(term, ignore_dates, max_auctions, show_page_content)
                all_results[term] = valid_auctions
                total_valid_auctions += len(valid_auctions)
                
                print(f"\n📊 TERM '{term}' SUMMARY: {len(valid_auctions)} valid auctions found")
                time.sleep(2)  # Brief pause between searches
            
            # Final summary
            print(f"\n{'='*60}")
            print(f"🏁 FINAL COMPREHENSIVE SUMMARY")
            print(f"{'='*60}")
            print(f"📊 Total valid auctions found: {total_valid_auctions}")
            
            for term, auctions in all_results.items():
                print(f"\n🔍 '{term}': {len(auctions)} auctions")
                if auctions:
                    for i, auction in enumerate(auctions, 1):
                        title = auction.get('title', 'No title')[:60]
                        bid = auction.get('current_bid', 'N/A')
                        location = auction.get('location', 'N/A')[:30]
                        url_status = "✅" if auction.get('url') else "❌"
                        print(f"   {i}. {title}...")
                        print(f"      💰 {bid} | 📍 {location} | 🔗 {url_status}")
            
            if total_valid_auctions == 0:
                print(f"\n⚠️ NO VALID AUCTIONS FOUND")
                print(f"Possible issues:")
                print(f"• Date range too restrictive (try --all-dates)")
                print(f"• Location filters too specific")
                print(f"• Condition filters too restrictive")
                print(f"• Search terms not matching available items")
                print(f"• Website structure changed")
            
            return all_results
            
        finally:
            self.close_driver()

def main():
    parser = argparse.ArgumentParser(description='Comprehensive BidFTA Auction Debug Tool')
    parser.add_argument('--term', type=str, help='Test specific search term only')
    parser.add_argument('--all-dates', action='store_true', help='Ignore date restrictions')
    parser.add_argument('--max-auctions', type=int, help='Max auctions to process per search')
    parser.add_argument('--show-page', action='store_true', help='Show page content if no results')
    parser.add_argument('--no-headless', action='store_true', help='Show browser window')
    
    args = parser.parse_args()
    
    debugger = ComprehensiveDebugger(headless=not args.no_headless)
    
    try:
        results = debugger.run_comprehensive_debug(
            specific_term=args.term,
            ignore_dates=args.all_dates,
            max_auctions=args.max_auctions,
            show_page_content=args.show_page
        )
        
        print(f"\n✅ Debug completed successfully!")
        
    except KeyboardInterrupt:
        print(f"\n⚠️ Debug interrupted by user")
    except Exception as e:
        print(f"\n❌ Debug failed: {str(e)}")
        import traceback
        print(f"🔍 Full error: {traceback.format_exc()}")

if __name__ == "__main__":
    main()