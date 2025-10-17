import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime
from typing import List, Dict
import os

from config import EMAIL_CONFIG, PRIORITY_1_LOCATIONS, PRIORITY_2_LOCATIONS, SEARCH_TERMS

class EmailSender:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def get_location_priority(self, location: str) -> int:
        """Get location priority (2=highest, 1=medium, 0=normal)"""
        location_lower = location.lower()
        
        # Check Priority 2 (⭐⭐)
        for prio2_location in PRIORITY_2_LOCATIONS:
            if prio2_location.lower() in location_lower:
                return 2
                
        # Check Priority 1 (⭐)
        for prio1_location in PRIORITY_1_LOCATIONS:
            if prio1_location.lower() in location_lower:
                return 1
                
        # Normal priority
        return 0
        
    def format_search_summary(self, grouped_auctions: Dict[str, List[Dict]]) -> str:
        """Format the search summary showing count per search term"""
        summary_parts = []
        for search_term, auctions in grouped_auctions.items():
            count = len(auctions)
            summary_parts.append(f"{search_term}: {count}")
        return " • ".join(summary_parts)
    
    def sort_auctions_by_end_time(self, auctions: List[Dict]) -> List[Dict]:
        """Sort auctions by end time (soonest first)"""
        def parse_end_time(auction):
            """Extract sortable time from end time string"""
            end_time = auction.get('end_time', '').lower()
            
            # Priority order: today > tomorrow > days of week > dates
            if 'today' in end_time:
                return 0
            elif 'tomorrow' in end_time:
                return 1
            elif 'sunday' in end_time:
                return 2
            elif 'monday' in end_time:
                return 3
            elif 'tuesday' in end_time:
                return 4
            elif 'wednesday' in end_time:
                return 5
            elif 'thursday' in end_time:
                return 6
            elif 'friday' in end_time:
                return 7
            elif 'saturday' in end_time:
                return 8
            else:
                # For specific dates, put them at the end
                return 9
        
        return sorted(auctions, key=parse_end_time)
        
    def group_auctions_by_search_term(self, auctions: List[Dict]) -> Dict[str, List[Dict]]:
        """Group auctions by search term and sort each group by end time"""
        grouped = {}
        for auction in auctions:
            search_term = auction.get('search_term', 'Unknown')
            if search_term not in grouped:
                grouped[search_term] = []
            grouped[search_term].append(auction)
        
        # Sort each group by end time (soonest first)
        for search_term in grouped:
            grouped[search_term] = self.sort_auctions_by_end_time(grouped[search_term])
            
        return grouped
        
    def generate_html_email(self, auctions: List[Dict]) -> str:
        """Generate mobile-optimized HTML email content"""
        if not auctions:
            return self.generate_empty_email()
            
        grouped_auctions = self.group_auctions_by_search_term(auctions)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                    line-height: 1.4;
                    color: #333;
                    margin: 0;
                    padding: 10px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    background-color: #2c3e50;
                    color: white;
                    padding: 20px 15px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0 0 5px 0;
                    font-size: 20px;
                    font-weight: 600;
                }}
                .header p {{
                    margin: 0;
                    font-size: 14px;
                    opacity: 0.9;
                }}
                .summary {{
                    background-color: #ecf0f1;
                    padding: 15px;
                    font-size: 14px;
                }}
                .summary h3 {{
                    margin: 0 0 8px 0;
                    font-size: 16px;
                }}
                .summary p {{
                    margin: 4px 0;
                }}
                .summary .search-count {{
                    font-weight: 600;
                    color: #2c3e50;
                }}
                .search-section {{
                    margin-bottom: 20px;
                    border-bottom: 1px solid #eee;
                }}
                .search-header {{
                    background-color: #3498db;
                    color: white;
                    padding: 12px 15px;
                    font-size: 16px;
                    font-weight: 600;
                }}
                .auction-item {{
                    padding: 15px;
                    border-bottom: 1px solid #f0f0f0;
                    display: flex;
                    align-items: flex-start;
                    gap: 12px;
                }}
                .auction-item:last-child {{
                    border-bottom: none;
                }}
                
                /* Mobile-optimized clickable image */
                .image-link {{
                    display: block;
                    width: 80px;
                    height: 80px;
                    flex-shrink: 0;
                    text-decoration: none;
                    border-radius: 6px;
                    overflow: hidden;
                }}
                .auction-image {{
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                    display: block;
                    border: none;
                }}
                .no-image {{
                    width: 100%;
                    height: 100%;
                    background-color: #ecf0f1;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: #7f8c8d;
                    font-size: 10px;
                    text-align: center;
                    text-decoration: none;
                }}
                
                /* Mobile-optimized content */
                .auction-details {{
                    flex: 1;
                    min-width: 0; /* Prevents flex item from overflowing */
                }}
                .auction-title {{
                    font-size: 15px;
                    font-weight: 600;
                    margin-bottom: 8px;
                    line-height: 1.3;
                }}
                .auction-title a {{
                    color: #2c3e50;
                    text-decoration: none;
                    word-wrap: break-word;
                }}
                .auction-title a:hover {{
                    color: #3498db;
                    text-decoration: underline;
                }}
                
                /* Mobile-friendly two-column layout */
                .auction-info {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 8px 12px;
                    font-size: 13px;
                }}
                .info-item {{
                    display: flex;
                    flex-direction: column;
                    gap: 2px;
                }}
                .info-label {{
                    font-weight: 600;
                    color: #7f8c8d;
                    font-size: 11px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                .info-value {{
                    color: #2c3e50;
                    font-weight: 500;
                    word-wrap: break-word;
                }}
                
                /* Highlighted current bid */
                .current-bid {{
                    font-size: 16px;
                    font-weight: 700;
                    color: #27ae60;
                }}
                
                /* Priority location badges */
                .priority-badge {{
                    display: inline-block;
                    padding: 2px 6px;
                    border-radius: 10px;
                    font-size: 10px;
                    font-weight: 600;
                    margin-left: 4px;
                    vertical-align: middle;
                }}
                .priority-2 {{
                    background-color: #e74c3c;
                    color: white;
                }}
                .priority-1 {{
                    background-color: #f39c12;
                    color: white;
                }}
                
                .footer {{
                    margin-top: 20px;
                    padding: 20px 15px;
                    background-color: #ecf0f1;
                    text-align: center;
                    color: #7f8c8d;
                    font-size: 12px;
                }}
                
                /* iOS Mail app specific optimizations */
                @media screen and (max-width: 480px) {{
                    .container {{
                        margin: 0;
                        border-radius: 0;
                    }}
                    .image-link {{
                        width: 70px;
                        height: 70px;
                    }}
                    .auction-item {{
                        padding: 12px;
                        gap: 10px;
                    }}
                    .auction-info {{
                        gap: 6px 10px;
                        font-size: 12px;
                    }}
                    .auction-title {{
                        font-size: 14px;
                    }}
                    .current-bid {{
                        font-size: 15px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏷️ Weekly BidFTA Report</h1>
                    <p>{datetime.now().strftime('%B %d, %Y')}</p>
                </div>
                
                <div class="summary">
                    <h3>📊 Summary</h3>
                    <p><strong>{len(auctions)}</strong> auctions found ending this week</p>
                    <div class="search-count">
                        {self.format_search_summary(grouped_auctions)}
                    </div>
                </div>
        """
        
        # Add each search section
        for search_term, term_auctions in grouped_auctions.items():
            html += f"""
                <div class="search-section">
                    <div class="search-header">
                        🔍 {search_term} - {len(term_auctions)} items
                    </div>
            """
            
            for auction in term_auctions:
                # Image handling with clickable link
                image_html = ""
                auction_url_safe = auction.get('url', '#')
                
                if auction.get('image_path') and os.path.exists(auction['image_path']):
                    image_html = f'''
                    <a href="{auction_url_safe}" class="image-link">
                        <img src="cid:image_{hash(auction.get("url", ""))}" class="auction-image" alt="Auction item">
                    </a>'''
                elif auction.get('image_url'):
                    # For external images, make sure they're properly formatted
                    img_url = auction['image_url']
                    if img_url and not img_url.startswith(('http://', 'https://')):
                        img_url = f"https:{img_url}" if img_url.startswith('//') else f"https://www.bidft.auction{img_url}"
                    
                    image_html = f'''
                    <a href="{auction_url_safe}" class="image-link">
                        <img src="{img_url}" class="auction-image" alt="Auction item">
                    </a>'''
                else:
                    image_html = f'''
                    <a href="{auction_url_safe}" class="image-link">
                        <div class="no-image">View Item</div>
                    </a>'''
                
                # Location with priority
                location = auction.get('location', 'Unknown')
                location_priority = self.get_location_priority(location)
                
                location_html = location
                if location_priority == 2:
                    location_html += '<span class="priority-badge priority-2">⭐⭐</span>'
                elif location_priority == 1:
                    location_html += '<span class="priority-badge priority-1">⭐</span>'
                
                # Truncate title if too long for mobile
                title = auction.get('title', 'No title')
                if len(title) > 60:
                    title = title[:57] + '...'
                
                html += f"""
                <div class="auction-item">
                    {image_html}
                    <div class="auction-details">
                        <div class="auction-title">
                            <a href="{auction.get('url', '#')}" target="_blank">
                                {title}
                            </a>
                        </div>
                        <div class="auction-info">
                            <div class="info-item">
                                <span class="info-label">Current Bid</span>
                                <span class="info-value current-bid">{auction.get('current_bid', 'N/A')}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">End Time</span>
                                <span class="info-value">{auction.get('end_time', 'Unknown')}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Location</span>
                                <span class="info-value">{location_html}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Condition</span>
                                <span class="info-value">{auction.get('condition', 'Unknown')}</span>
                            </div>
                        </div>
                    </div>
                </div>
                """
            
            html += "</div>"  # Close search-section
        
        html += f"""
                <div class="footer">
                    <p>Generated on {datetime.now().strftime('%Y-%m-%d at %I:%M %p')}</p>
                    <p>Auctions ending Sunday-Saturday this week</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
        
    def generate_empty_email(self) -> str:
        """Generate mobile-optimized email when no auctions found"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                    line-height: 1.4;
                    color: #333;
                    margin: 0;
                    padding: 10px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    background-color: #2c3e50;
                    color: white;
                    padding: 20px 15px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0 0 5px 0;
                    font-size: 20px;
                    font-weight: 600;
                }}
                .header p {{
                    margin: 0;
                    font-size: 14px;
                    opacity: 0.9;
                }}
                .content {{
                    padding: 30px 20px;
                    text-align: center;
                }}
                .content h2 {{
                    color: #2c3e50;
                    margin-bottom: 15px;
                    font-size: 18px;
                }}
                .content p {{
                    margin: 8px 0;
                    font-size: 14px;
                    color: #7f8c8d;
                }}
                @media screen and (max-width: 480px) {{
                    .container {{
                        margin: 0;
                        border-radius: 0;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏷️ Weekly BidFTA Report</h1>
                    <p>{datetime.now().strftime('%B %d, %Y')}</p>
                </div>
                
                <div class="content">
                    <h2>No Auctions Found</h2>
                    <p>No auctions matching your criteria were found this week.</p>
                    <p><strong>Search terms:</strong> {', '.join(SEARCH_TERMS)}</p>
                    <p>Better luck next week! 🤞</p>
                </div>
            </div>
        </body>
        </html>
        """

    def send_failure_notification(self, error_message: str) -> bool:
        """Send email notification when the scraper fails"""
        try:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_CONFIG['sender_email']
            msg['To'] = EMAIL_CONFIG['recipient_email']
            msg['Subject'] = "❌ BidFTA Scraper Failed"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; }}
                    .header {{ background-color: #e74c3c; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background-color: #f9f9f9; }}
                    .error {{ background-color: #fff; border-left: 4px solid #e74c3c; padding: 15px; margin: 10px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>❌ BidFTA Scraper Failed</h1>
                        <p>{datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                    </div>
                    <div class="content">
                        <h3>Error Details:</h3>
                        <div class="error">
                            <pre>{error_message}</pre>
                        </div>
                        <p>Please check the log file and fix any issues before the next scheduled run.</p>
                        <p>Log file location: auction_scraper.log</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
                server.starttls()
                server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send failure notification: {str(e)}")
            return False
        
    def send_email(self, auctions: List[Dict]) -> bool:
        """Send the weekly auction report email"""
        try:
            # Create message
            msg = MIMEMultipart('related')
            msg['From'] = EMAIL_CONFIG['sender_email']
            msg['To'] = EMAIL_CONFIG['recipient_email']
            
            auction_count = len(auctions)
            if auction_count == 0:
                msg['Subject'] = f"🏷️ Weekly BidFTA Report - No Auctions Found"
            else:
                msg['Subject'] = f"🏷️ Weekly BidFTA Report - {auction_count} Auctions Found"
            
            # Generate HTML content
            html_content = self.generate_html_email(auctions)
            msg.attach(MIMEText(html_content, 'html'))
            
            # Attach images
            for auction in auctions:
                image_path = auction.get('image_path')
                if image_path and os.path.exists(image_path):
                    try:
                        with open(image_path, 'rb') as f:
                            img_data = f.read()
                        image = MIMEImage(img_data)
                        image.add_header('Content-ID', f'<image_{hash(auction.get("url", ""))}>')
                        msg.attach(image)
                    except Exception as e:
                        self.logger.warning(f"Failed to attach image {image_path}: {str(e)}")
            
            # Send email
            with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
                server.starttls()
                server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
                server.send_message(msg)
            
            self.logger.info(f"Email sent successfully with {auction_count} auctions")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {str(e)}")
            return False

if __name__ == "__main__":
    # Test email sending
    test_auctions = [
        {
            'title': 'Brand New Cat Litter Box with Automatic Cleaning System',
            'url': 'https://example.com/auction/123',
            'current_bid': '$25.50',
            'end_time': 'Sunday 8:00 PM',
            'location': 'Cincinnati - West Seymour Ave',
            'condition': 'Brand New',
            'search_term': 'cat'
        },
        {
            'title': 'Heavy Duty Outdoor Trash Can 32 Gallon',
            'url': 'https://example.com/auction/456',
            'current_bid': '$15.00',
            'end_time': 'Saturday 6:30 PM',
            'location': 'Springdale - Commons Drive',
            'condition': 'Appears New',
            'search_term': 'trash'
        }
    ]
    
    sender = EmailSender()
    success = sender.send_email(test_auctions)
    print(f"Email test: {'Success' if success else 'Failed'}")