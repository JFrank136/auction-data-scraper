#!/usr/bin/env python3
"""
BidFTA Auction Scraper - Main Entry Point

This script scrapes BidFTA auctions based on your search criteria
and sends a weekly email report with matching auctions.

Usage:
    py main.py              # Run full scraping and email
    py main.py --test       # Test mode (scrape but don't send email)
    py main.py --email-only # Send test email with sample data
"""

import argparse
import logging
import sys
import traceback
from datetime import datetime
from typing import List, Dict

from scraper import BidFTAScraper
from email_sender import EmailSender
from config import SEARCH_TERMS, OUTPUT_DIR

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('auction_scraper.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def save_results_to_file(auctions: List[Dict], filename: str = None):
    """Save scraping results to a file for debugging"""
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{OUTPUT_DIR}/auctions_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"BidFTA Auction Scraper Results\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total auctions found: {len(auctions)}\n")
        f.write("=" * 50 + "\n\n")
        
        if not auctions:
            f.write("No auctions found matching your criteria.\n")
            return filename
        
        for i, auction in enumerate(auctions, 1):
            f.write(f"{i}. {auction.get('title', 'No title')}\n")
            f.write(f"   URL: {auction.get('url', 'N/A')}\n")
            f.write(f"   Current Bid: {auction.get('current_bid', 'N/A')}\n")
            f.write(f"   End Time: {auction.get('end_time', 'N/A')}\n")
            f.write(f"   Location: {auction.get('location', 'N/A')}\n")
            f.write(f"   Condition: {auction.get('condition', 'N/A')}\n")
            f.write(f"   Search Term: {auction.get('search_term', 'N/A')}\n")
            f.write(f"   Image URL: {auction.get('image_url', 'N/A')}\n")
            f.write("-" * 30 + "\n")
    
    return filename

def run_full_scraping(logger):
    """Run the complete scraping process with error handling"""
    logger.info("Starting BidFTA auction scraping...")
    logger.info(f"Search terms: {', '.join(SEARCH_TERMS)}")
    
    try:
        # Initialize scraper
        scraper = BidFTAScraper()
        
        # Scrape auctions
        auctions = scraper.scrape_all_searches()
        logger.info(f"Scraping completed. Found {len(auctions)} auctions.")
        
        # Save results to file
        results_file = save_results_to_file(auctions)
        logger.info(f"Results saved to: {results_file}")
        
        # Send email
        email_sender = EmailSender()
        success = email_sender.send_email(auctions)
        
        if success:
            logger.info("Email sent successfully!")
            return True
        else:
            logger.error("Failed to send email.")
            # Send failure notification
            error_msg = "Failed to send weekly auction report email. Check email configuration."
            email_sender.send_failure_notification(error_msg)
            return False
            
    except Exception as e:
        error_msg = f"Error during scraping: {str(e)}\n\nFull traceback:\n{traceback.format_exc()}"
        logger.error(error_msg)
        
        # Try to send failure notification
        try:
            email_sender = EmailSender()
            email_sender.send_failure_notification(error_msg)
        except Exception as email_error:
            logger.error(f"Failed to send failure notification: {str(email_error)}")
        
        return False

def run_test_mode(logger):
    """Run in test mode - scrape but don't send email"""
    logger.info("Running in TEST MODE - scraping only, no email will be sent")
    
    try:
        scraper = BidFTAScraper()
        auctions = scraper.scrape_all_searches()
        logger.info(f"Test scraping completed. Found {len(auctions)} auctions.")
        
        # Save results
        results_file = save_results_to_file(auctions)
        logger.info(f"Test results saved to: {results_file}")
        
        # Print summary
        print(f"\n{'='*50}")
        print(f"TEST MODE RESULTS")
        print(f"{'='*50}")
        print(f"Total auctions found: {len(auctions)}")
        
        if auctions:
            print(f"\nFirst few results:")
            for i, auction in enumerate(auctions[:3], 1):
                print(f"{i}. {auction.get('title', 'No title')}")
                print(f"   Bid: {auction.get('current_bid', 'N/A')} | Location: {auction.get('location', 'N/A')}")
        
        print(f"\nFull results saved to: {results_file}")
        print("No email was sent (test mode)")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during test scraping: {str(e)}")
        print(f"❌ Test failed: {str(e)}")
        return False

def send_test_email(logger):
    """Send a test email with sample data"""
    logger.info("Sending test email with sample data...")
    
    # Create sample auction data
    sample_auctions = [
        {
            'title': 'Brand New Cat Litter Box with Lid',
            'url': 'https://www.bidft.auction/auction/123456',
            'current_bid': '$25.50',
            'end_time': 'Ends Sunday 8:00 PM',
            'location': 'Cincinnati - West Seymour Ave',
            'condition': 'Brand New',
            'search_term': 'cat',
            'image_url': 'https://example.com/image1.jpg'
        },
        {
            'title': 'Heavy Duty Trash Can 32 Gallon',
            'url': 'https://www.bidft.auction/auction/789012',
            'current_bid': '$15.00',
            'end_time': 'Ends Saturday 6:30 PM',
            'location': 'Springdale - Commons Drive',
            'condition': 'Appears New',
            'search_term': 'trash',
            'image_url': 'https://example.com/image2.jpg'
        }
    ]
    
    try:
        email_sender = EmailSender()
        success = email_sender.send_email(sample_auctions)
        
        if success:
            logger.info("Test email sent successfully!")
            print("✅ Test email sent! Check your inbox.")
            return True
        else:
            logger.error("Failed to send test email.")
            print("❌ Test email failed. Check your email settings in config.py")
            return False
            
    except Exception as e:
        logger.error(f"Test email error: {str(e)}")
        print(f"❌ Test email failed: {str(e)}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='BidFTA Auction Scraper')
    parser.add_argument('--test', action='store_true', 
                       help='Run in test mode (scrape but don\'t send email)')
    parser.add_argument('--email-only', action='store_true',
                       help='Send test email only (no scraping)')
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging()
    
    logger.info("BidFTA Auction Scraper starting...")
    logger.info(f"Arguments: test={args.test}, email_only={args.email_only}")
    
    try:
        if args.email_only:
            success = send_test_email(logger)
        elif args.test:
            success = run_test_mode(logger)
        else:
            success = run_full_scraping(logger)
        
        if success:
            logger.info("Script completed successfully!")
            sys.exit(0)
        else:
            logger.error("Script completed with errors!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(0)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}\n\nFull traceback:\n{traceback.format_exc()}"
        logger.error(error_msg)
        
        # Try to send failure notification for unexpected errors
        try:
            email_sender = EmailSender()
            email_sender.send_failure_notification(error_msg)
        except:
            pass  # Don't crash if we can't send the notification
            
        sys.exit(1)

if __name__ == "__main__":
    main()