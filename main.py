#!/usr/bin/env python3
"""
BidFTA Auction Scraper - Main Entry Point

Usage:
    py main.py              # Run full scraping and email
    py main.py --test       # Test mode (scrape but don't send email)
    py main.py --email-only # Send test email with sample data
"""

import argparse
import logging
import os
import glob
import sys
import traceback
from datetime import datetime
from typing import List, Dict

from scraper import BidFTAScraper
from email_sender import EmailSender
from config import SEARCH_TERMS, OUTPUT_DIR

# ── Log settings ─────────────────────────────────────────
LOG_DIR = 'log'
MAX_LOG_FILES = 8       # Keep last 8 weekly runs (2 months)
LOCK_FILE = 'scraper.lock'
# ─────────────────────────────────────────────────────────

def acquire_lock():
    """
    Prevent duplicate runs from Task Scheduler firing the script more than once.
    Writes a lock file with the current PID. Returns False if already running.
    """
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, 'r') as f:
            old_pid = f.read().strip()
        print(f"Lock file found (PID {old_pid}). Another instance may be running. Exiting.")
        return False
    with open(LOCK_FILE, 'w') as f:
        f.write(str(os.getpid()))
    return True

def release_lock():
    """Remove the lock file on exit."""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except OSError:
        pass

def setup_logging():
    """Setup logging — writes dated files to log/ folder, prunes old ones."""
    os.makedirs(LOG_DIR, exist_ok=True)

    timestamp = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(LOG_DIR, f'scraper_{timestamp}.log')

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Silence noisy WDM (WebDriver Manager) logs
    logging.getLogger('WDM').setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Log: {os.path.abspath(log_file)}")

    _prune_old_logs(logger)
    return logger

def _prune_old_logs(logger):
    """Delete oldest scraper log files, keeping only the last MAX_LOG_FILES."""
    pattern = os.path.join(LOG_DIR, 'scraper_*.log')
    log_files = sorted(glob.glob(pattern))

    if len(log_files) > MAX_LOG_FILES:
        for f in log_files[:len(log_files) - MAX_LOG_FILES]:
            try:
                os.remove(f)
                logger.info(f"Pruned old log: {f}")
            except OSError as e:
                logger.warning(f"Could not delete {f}: {e}")

def save_results_to_file(auctions: List[Dict], filename: str = None):
    """Save scraping results to a file for debugging."""
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
    """Run the complete scraping process with error handling."""
    logger.info(f"Search terms: {', '.join(SEARCH_TERMS)}")

    try:
        scraper = BidFTAScraper()
        auctions = scraper.scrape_all_searches()
        logger.info(f"Scraping complete — {len(auctions)} auctions found")

        results_file = save_results_to_file(auctions)
        logger.info(f"Results saved: {results_file}")

        email_sender = EmailSender()
        success = email_sender.send_email(auctions)

        if success:
            logger.info("Email sent successfully")
            return True
        else:
            logger.error("Failed to send email")
            email_sender.send_failure_notification("Failed to send weekly auction report. Check email config.")
            return False

    except Exception as e:
        error_msg = f"Error during scraping: {str(e)}\n\nFull traceback:\n{traceback.format_exc()}"
        logger.error(error_msg)
        try:
            email_sender = EmailSender()
            email_sender.send_failure_notification(error_msg)
        except Exception as email_error:
            logger.error(f"Failed to send failure notification: {str(email_error)}")
        return False

def run_test_mode(logger):
    """Run in test mode — scrape but don't send email."""
    logger.info("TEST MODE — no email will be sent")

    try:
        scraper = BidFTAScraper()
        auctions = scraper.scrape_all_searches()
        logger.info(f"Test complete — {len(auctions)} auctions found")

        results_file = save_results_to_file(auctions)
        logger.info(f"Results saved: {results_file}")

        print(f"\n{'='*50}\nTEST MODE RESULTS\n{'='*50}")
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
    """Send a test email with sample data."""
    logger.info("Sending test email with sample data...")

    sample_auctions = [
        {
            'title': 'Brand New Cat Litter Box with Lid',
            'url': 'https://www.bidfta.com/auction/123456',
            'current_bid': '$25.50',
            'end_time': 'Ends Sunday 8:00 PM',
            'location': 'Cincinnati - West Seymour Ave',
            'condition': 'Brand New',
            'search_term': 'cat',
            'image_url': 'https://example.com/image1.jpg'
        },
        {
            'title': 'Heavy Duty Trash Can 32 Gallon',
            'url': 'https://www.bidfta.com/auction/789012',
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
            logger.info("Test email sent successfully")
            print("✅ Test email sent! Check your inbox.")
            return True
        else:
            logger.error("Failed to send test email")
            print("❌ Test email failed. Check your email settings in config.py")
            return False
    except Exception as e:
        logger.error(f"Test email error: {str(e)}")
        print(f"❌ Test email failed: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='BidFTA Auction Scraper')
    parser.add_argument('--test', action='store_true',
                        help='Run in test mode (scrape but don\'t send email)')
    parser.add_argument('--email-only', action='store_true',
                        help='Send test email only (no scraping)')
    args = parser.parse_args()

    logger = setup_logging()
    logger.info(f"BidFTA Auction Scraper starting — test={args.test}, email_only={args.email_only}")

    # ── Lock: prevent Task Scheduler from running overlapping instances ──
    if not acquire_lock():
        logger.warning("Another instance is already running. Exiting.")
        sys.exit(0)

    try:
        if args.email_only:
            success = send_test_email(logger)
        elif args.test:
            success = run_test_mode(logger)
        else:
            success = run_full_scraping(logger)

        if success:
            logger.info("Script completed successfully")
            sys.exit(0)
        else:
            logger.error("Script completed with errors")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(0)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}\n\nFull traceback:\n{traceback.format_exc()}"
        logger.error(error_msg)
        try:
            email_sender = EmailSender()
            email_sender.send_failure_notification(error_msg)
        except:
            pass
        sys.exit(1)
    finally:
        release_lock()

if __name__ == "__main__":
    main()