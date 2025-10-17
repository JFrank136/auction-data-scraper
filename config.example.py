# BidFTA Auction Scraper Configuration Template
# Copy this file to config.py and fill in your actual values

# Search terms - add or remove as needed
SEARCH_TERMS = [
    "Cat",
    "Trash",
    "Rug"
    # Add more search terms here
]

# Email settings
# IMPORTANT: Never commit your actual credentials to GitHub!
# Use environment variables or keep config.py in .gitignore
EMAIL_CONFIG = {
    'sender_email': 'your_email@gmail.com',  # Your Gmail address
    'sender_password': 'your_app_password_here',  # Gmail app password (NOT your regular password)
    'recipient_email': 'recipient@gmail.com',  # Where to send the weekly report
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587
}

# Location settings
PRIMARY_LOCATION = "Cincinnati"  # Main location to search

# All Cincinnati area locations from BidFTA
# Customize these based on your preferred locations
CINCINNATI_LOCATIONS = [
    "Cincinnati - West Seymour Ave",
    "Cincinnati - West Seymour Ave.",
    "Springdale - Commons Drive", 
    "Cincinnati - School Road",
    "Cincinnati - Colerain Ave",
    "Cincinnati - Colerain Ave.",
    "Cincinnati - Waycross Rd CWY"
]

# Most preferred locations (will be highlighted in email with ⭐⭐)
PRIORITY_2_LOCATIONS = [
    "Cincinnati - West Seymour Ave"
]

# Preferred locations (will be highlighted in email with ⭐)
PRIORITY_1_LOCATIONS = [
    "Springdale - Commons Drive",
    "Cincinnati - School Road"
]

# Auction filters - updated to match BidFTA structure
FILTERS = {
    'condition': ['Appears New', 'Brand New'],  # Only these conditions
    'locations': CINCINNATI_LOCATIONS,  # All Cincinnati locations
    'days_to_end': 7,  # Auctions ending within this many days from Sunday
    'ended': False,  # Only active auctions
}

# BidFTA specific settings
BIDFTA_CONFIG = {
    'base_url': 'https://www.bidft.auction',
    'search_endpoint': '/archive',
    'use_encoded_params': True,  # Site uses encoded search parameters
}

# Date calculation settings
DATE_CONFIG = {
    'week_start': 'sunday',  # Week starts on Sunday
    'include_start_day': True,  # Include Sunday in "ends after" 
    'include_end_day': True,   # Include Saturday in "ends before"
}

# Scraping settings
SCRAPING_CONFIG = {
    'headless': True,  # Set to False if you want to see the browser window
    'wait_time': 10,  # Seconds to wait for pages to load
    'max_pages': 5,  # Maximum pages to scrape per search term
    'delay_between_searches': 2,  # Seconds to wait between searches
    'page_load_delay': 3,  # Extra delay for JavaScript-heavy pages
}

# Logging
LOG_FILE = 'auction_scraper.log'
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR

# File paths
OUTPUT_DIR = 'scraper_output'
IMAGES_DIR = f'{OUTPUT_DIR}/images'

# CSS Selectors for BidFTA
SELECTORS = {
    'search_box': 'input[name="searchTerm"], input[type="search"]',
    'search_button': 'button[type="submit"], .search-btn',
    'auction_items': '.auction-card, .listing-item, .auction-result',
    'auction_title': '.auction-title, .item-title, h3',
    'auction_link': 'a',
    'current_bid': '.current-bid, .bid-amount, .price',
    'end_time': '.end-time, .auction-end, .time-left',
    'location': '.location, .auction-location',
    'condition': '.condition, .item-condition',
    'auction_image': 'img',
    'next_page': '.next-page, .pagination-next, [aria-label="Next"]',
    'location_filter': 'input[type="checkbox"][data-location], .location-checkbox',
    'condition_filter': 'input[type="checkbox"][data-condition], .condition-checkbox',
}