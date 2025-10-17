# Auction Data Scraper

A Python script I built to automate checking BidFTA auctions for items I'm interested in. Instead of manually browsing, this runs weekly and emails me a summary of what's available.

## What It Does

Automatically searches BidFTA for specific items and sends me a weekly email with:
- Items matching my search terms
- Current bid prices
- When auctions end
- Pickup locations
- Item photos

**Time saved:** About 2 hours per week → 5 minutes to review an email

## Why I Built This

I was checking auction sites daily for specific items (cat supplies, household stuff, etc.) and it was getting tedious. So I automated it. Now I get a weekly email on Sunday mornings with everything I care about, already filtered and sorted.

## Tech Stack

- **Python 3.8+** - Main language
- **Selenium** - Web scraping and browser automation
- **ChromeDriver** - Headless browser
- **Gmail SMTP** - Email delivery

## Quick Setup

```bash
# Clone and install
git clone https://github.com/JFrank136/auction-data-scraper.git
cd auction-data-scraper
pip install -r requirements.txt

# Configure
cp config.example.py config.py
# Edit config.py with your settings

# Test it
python main.py --test
```

## Configuration

Edit `config.py` to customize:

**What to search for:**
```python
SEARCH_TERMS = ["Cat", "Trash", "Chair"]
```

**Where to search:**
```python
CINCINNATI_LOCATIONS = [
    "Cincinnati - West Seymour Ave",
    "Springdale - Commons Drive",
    # Add your preferred pickup locations
]
```

**Email settings:**
```python
EMAIL_CONFIG = {
    'sender_email': 'your_email@gmail.com',
    'sender_password': 'your_gmail_app_password',
    'recipient_email': 'your_email@gmail.com',
}
```

**Gmail App Password Setup:**
1. Google Account → Security → 2-Step Verification
2. App Passwords → Generate for "Mail"
3. Use that 16-character password (not your regular password)

## Usage

```bash
# Run full pipeline (scrape + email)
python main.py

# Test scraping only (no email)
python main.py --test

# Test email only (with sample data)
python main.py --email-only
```

## Scheduling

**Windows (Task Scheduler):**
- Run `run_weekly.bat`
- Schedule for Sunday mornings

**Mac/Linux (cron):**
```bash
# Add to crontab (Sunday 8:00 AM)
0 8 * * 0 cd /path/to/auction-data-scraper && python main.py
```

## How It Works

1. **Scrapes auction site** - Uses Selenium to navigate and extract data
2. **Filters results** - Keeps only items matching location/condition preferences
3. **Removes duplicates** - Checks for duplicate listings by URL and title
4. **Generates email** - Creates HTML email with images and sorting
5. **Sends report** - Delivers via Gmail on schedule

## Data Pipeline

```
Search BidFTA
    ↓
Extract auction data (title, price, location, end time)
    ↓
Clean & validate (remove duplicates, check required fields)
    ↓
Download images
    ↓
Generate HTML report
    ↓
Email to me
```

## Files

- `main.py` - Entry point, orchestrates everything
- `scraper.py` - Web scraping logic
- `email_sender.py` - Email generation and sending
- `config.py` - Your settings (not in repo, see config.example.py)
- `comprehensive_debug.py` - Debugging tool when things break

## Debugging

If it's not working:

```bash
# See what's happening
python comprehensive_debug.py

# Test specific search term
python comprehensive_debug.py --term "cat"

# Ignore date filters to see all data
python comprehensive_debug.py --all-dates
```

Check `auction_scraper.log` for detailed error messages.

## Project Structure

```
auction-data-scraper/
├── main.py                  # Main script
├── scraper.py              # Scraping logic
├── email_sender.py         # Email functionality
├── config.py               # Your config (gitignored)
├── config.example.py       # Config template
├── requirements.txt        # Dependencies
├── .gitignore             
└── scraper_output/        # Generated files (gitignored)
    ├── images/            # Downloaded photos
    └── *.txt              # Text reports
```

## Output

**Console:**
```
2025-10-16 08:00:15 - INFO - Starting scraper...
2025-10-16 08:00:20 - INFO - Searching for: Cat
2025-10-16 08:00:35 - INFO - Found 25 auctions
2025-10-16 08:01:15 - INFO - Email sent successfully!
```

**Email you receive:**
- Summary stats (48 auctions found)
- Grouped by search term
- Sorted by end date (soonest first)
- Images embedded
- Priority locations marked with stars

## Future Ideas

Things I might add if I have time:

- [ ] iPhone reminders for selected items
- [ ] Price alerts when bid drops below threshold
- [ ] Automated bidding
- [ ] Deal finder based on MSRP listing


## Notes

**Web scraping considerations:**
- This is for personal use, not commercial
- Includes delays between requests
- Only scrapes publicly available data
- If BidFTA changes their site structure, this will break


## Requirements

```
selenium>=4.15.0
webdriver-manager>=4.0.0
beautifulsoup4>=4.12.0
requests>=2.31.0
lxml>=4.9.0
Pillow>=10.3.0
python-dateutil>=2.8.0
```


## Why Share This?

I built this to solve my own problem, but it makes a decent portfolio piece showing I can:
- Write Python beyond basic scripts
- Build end-to-end automation
- Handle data cleaning and validation
- Actually finish projects

---

Built over a few weekends in October 2025. Works on my machine. 🤷‍♂️