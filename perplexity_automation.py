#!/usr/bin/env python3
"""
FREE Crypto Market News Automation for Telegram
Uses Perplexity PRO to generate both crypto news summary AND images
Completely zero-cost solution - Monday-Friday at 19:00 PM
"""

import os
import sys
import json
import time
import logging
import requests
import tempfile
import random
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from urllib.parse import urlparse
from dataclasses import dataclass

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crypto_automation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class PerplexityResponse:
    """Data class to hold Perplexity API response"""
    content: str
    citations: List[str]
    model: str
    usage: Dict[str, int]
    images: List[str] = None

class PerplexityProCryptoGenerator:
    """Generate crypto news and images using Perplexity PRO API"""
    
    def __init__(self, api_key: str):
        """Initialize the Perplexity API client"""
        if not api_key:
            raise ValueError("API key cannot be empty")
            
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Available models
        self.models = {
            "sonar_pro": "sonar-pro",
            "sonar": "sonar",
            "sonar_small": "llama-3.1-sonar-small-128k-online",
            "sonar_large": "llama-3.1-sonar-large-128k-online",
            "sonar_huge": "llama-3.1-sonar-huge-128k-online"
        }
    
    def get_crypto_news_with_images(self) -> Tuple[str, List[str]]:
        """Get crypto news summary with images from Perplexity PRO"""
        
        query = """Summarize today's top global news about crypto market. Include major economic events, market movements, regulatory updates, and highlight any breaking news about future events. Focus on Bitcoin, Ethereum, major altcoins, institutional adoption, and market trends. Please include relevant images showing cryptocurrency charts, trading data, or market visualizations."""
        
        try:
            logger.info("🔍 Fetching crypto news and images from Perplexity PRO...")
            
            # Generate crypto news with images
            response = self.generate_crypto_news(
                query=query,
                model="sonar_pro",
                search_recency_filter="day"
            )
            
            logger.info(f"📰 Content length: {len(response.content)} characters")
            logger.info(f"🖼️ Found {len(response.images or [])} images")
            
            # Format the content
            formatted_content = self.format_crypto_summary(response.content)
            
            return formatted_content, response.images or []
            
        except Exception as e:
            logger.error(f"❌ Failed to get crypto news: {e}")
            raise
    
    def generate_crypto_news(
        self, 
        query: str = None, 
        model: str = "sonar_pro",
        max_tokens: int = 2000,
        temperature: float = 0.3,
        search_domain_filter: List[str] = None,
        search_recency_filter: str = "day"
    ) -> PerplexityResponse:
        """Generate crypto news using Perplexity API"""
        
        # Default crypto news query
        if query is None:
            query = """Provide a comprehensive summary of today's cryptocurrency market developments. 
            Include major price movements, regulatory news, institutional adoption, and breaking developments. 
            Focus on Bitcoin, Ethereum, and other major cryptocurrencies. Make it informative for crypto investors."""
        
        # Default crypto-focused domains
        if search_domain_filter is None:
            search_domain_filter = [
                "coindesk.com",
                "cointelegraph.com", 
                "coinmarketcap.com",
                "crypto.news",
                "decrypt.co",
                "theblock.co"
            ]
        
        payload = {
            "model": self.models.get(model, "sonar-pro"),
            "messages": [
                {
                    "role": "user",
                    "content": query
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "return_citations": True,
            "return_images": True,
            "search_domain_filter": search_domain_filter,
            "search_recency_filter": search_recency_filter
        }
        
        return self.generate_with_retry(payload)
    
    def generate_with_retry(
        self, 
        payload: Dict[str, Any], 
        max_retries: int = 3
    ) -> PerplexityResponse:
        """Make API request with exponential backoff retry logic"""
        retries = 0
        
        while retries < max_retries:
            try:
                return self._make_request(payload)
                
            except requests.exceptions.RequestException as e:
                error_msg = str(e).lower()
                
                if "rate_limit" in error_msg or "429" in error_msg:
                    sleep_time = (2 ** retries) + random.uniform(0, 1)
                    logger.warning(f"Rate limited. Retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                    retries += 1
                elif retries < max_retries - 1:
                    logger.warning(f"Request failed: {e}. Retrying...")
                    retries += 1
                    time.sleep(1)
                else:
                    raise e
            except Exception as e:
                if retries < max_retries - 1:
                    logger.warning(f"Unexpected error: {e}. Retrying...")
                    retries += 1
                    time.sleep(1)
                else:
                    raise e
        
        raise Exception(f"Max retries ({max_retries}) exceeded")
    
    def _make_request(self, payload: Dict[str, Any]) -> PerplexityResponse:
        """Make the actual API request"""
        try:
            response = requests.post(
                self.base_url, 
                headers=self.headers, 
                json=payload,
                timeout=60
            )
            
            logger.info(f"📡 Response status code: {response.status_code}")
            
            response.raise_for_status()
            result = response.json()
            
            # Parse response
            content = result['choices'][0]['message']['content']
            citations = result.get('citations', [])
            model = result.get('model', 'unknown')
            usage = result.get('usage', {})
            
            # Extract images from multiple locations
            images = []
            
            # Method 1: Direct images array
            if 'images' in result:
                for img in result['images']:
                    if isinstance(img, str):
                        images.append(img)
                    elif isinstance(img, dict) and 'url' in img:
                        images.append(img['url'])
            
            # Method 2: From provider metadata
            if 'provider_metadata' in result:
                metadata = result['provider_metadata']
                if 'perplexity' in metadata and 'images' in metadata['perplexity']:
                    for img in metadata['perplexity']['images']:
                        if 'imageUrl' in img:
                            images.append(img['imageUrl'])
                        elif 'url' in img:
                            images.append(img['url'])
            
            return PerplexityResponse(
                content=content,
                citations=citations,
                model=model,
                usage=usage,
                images=images
            )
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise Exception("Invalid API key. Please check your Perplexity API key.")
            elif response.status_code == 429:
                raise Exception("Rate limit exceeded. Please try again later.")
            elif response.status_code >= 500:
                raise Exception(f"Server error: {e}")
            else:
                error_text = ""
                try:
                    error_text = response.text
                except:
                    pass
                raise Exception(f"HTTP error {response.status_code}: {error_text}")
                
        except requests.exceptions.Timeout:
            raise Exception("Request timeout. Please try again.")
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")
            
        except (KeyError, json.JSONDecodeError) as e:
            raise Exception(f"Invalid response format: {e}")
    
    def format_crypto_summary(self, content: str) -> str:
        """Format crypto summary to exactly 1,500 characters without spaces"""
        
        # Clean and structure the content
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        formatted_text = ' '.join(lines)
        
        # Remove markdown formatting that might interfere
        formatted_text = formatted_text.replace('**', '').replace('*', '')
        formatted_text = formatted_text.replace('###', '').replace('##', '').replace('#', '')
        
        # Add professional header
        header = f"📈 CRYPTO MARKET UPDATE - {datetime.now().strftime('%B %d, %Y')}\n\n"
        
        # Add required hashtags
        hashtags = "\n\n#CryptoNews #MarketOverview"
        
        # Calculate available space (1500 chars without spaces)
        header_no_spaces = len(header.replace(' ', ''))
        hashtags_no_spaces = len(hashtags.replace(' ', ''))
        available_chars = 1500 - header_no_spaces - hashtags_no_spaces
        
        # Truncate content to fit exactly
        content_no_spaces = formatted_text.replace(' ', '')
        
        if len(content_no_spaces) > available_chars:
            # Find optimal cut-off point
            temp_content = ''
            for char in formatted_text:
                temp_no_spaces = temp_content.replace(' ', '')
                if len(temp_no_spaces) >= available_chars:
                    break
                temp_content += char
            
            # Try to end at a complete sentence
            sentences = temp_content.split('.')
            if len(sentences) > 1:
                # Keep all complete sentences
                temp_content = '.'.join(sentences[:-1]) + '.'
            
            formatted_text = temp_content.strip()
        
        # Construct final message
        final_text = header + formatted_text + hashtags
        
        # Verify character count
        final_no_spaces = final_text.replace(' ', '')
        char_count = len(final_no_spaces)
        
        logger.info(f"📊 Final article: {char_count} characters (without spaces)")
        logger.info(f"🎯 Target: 1,500 characters {'✅ PERFECT!' if char_count <= 1500 else '⚠️ Over limit'}")
        
        return final_text

class TelegramChannelBot:
    """Enhanced Telegram bot for posting crypto content"""
    
    def __init__(self, bot_token: str, channel_id: str):
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def download_image(self, image_url: str) -> Optional[str]:
        """Download image from URL and return local path"""
        try:
            logger.info(f"⬇️ Downloading image: {image_url[:100]}...")
            
            response = requests.get(image_url, timeout=60, stream=True)
            response.raise_for_status()
            
            # Determine file extension
            parsed_url = urlparse(image_url)
            file_ext = Path(parsed_url.path).suffix
            if not file_ext:
                content_type = response.headers.get('content-type', '')
                if 'jpeg' in content_type or 'jpg' in content_type:
                    file_ext = '.jpg'
                elif 'png' in content_type:
                    file_ext = '.png'
                elif 'webp' in content_type:
                    file_ext = '.webp'
                else:
                    file_ext = '.jpg'  # Default
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=file_ext,
                dir=tempfile.gettempdir()
            )
            
            # Download in chunks
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            
            temp_file.close()
            
            logger.info(f"✅ Image downloaded: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            logger.error(f"❌ Failed to download image {image_url}: {e}")
            return None
    
    def send_photo_with_caption(self, photo_path: str, caption: str) -> bool:
        """Send photo with caption to Telegram channel"""
        url = f"{self.base_url}/sendPhoto"
        
        try:
            with open(photo_path, 'rb') as photo_file:
                files = {'photo': photo_file}
                data = {
                    'chat_id': self.channel_id,
                    'caption': caption,
                    'parse_mode': 'Markdown'
                }
                
                logger.info("📤 Sending photo with caption to Telegram...")
                response = requests.post(url, files=files, data=data, timeout=60)
                response.raise_for_status()
                
                logger.info("🎉 Photo with crypto update sent successfully!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to send photo: {e}")
            return False
    
    def send_message(self, text: str) -> bool:
        """Send text message as fallback"""
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            "chat_id": self.channel_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        
        try:
            logger.info("📤 Sending text message to Telegram...")
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            logger.info("✅ Text message sent successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send message: {e}")
            return False

def cleanup_temp_files(file_paths: List[str]):
    """Clean up temporary image files"""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"🧹 Cleaned up: {file_path}")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup failed {file_path}: {e}")

def is_weekday() -> bool:
    """Check if today is a weekday (Monday-Friday)"""
    return datetime.now().weekday() < 5

def main():
    """Main FREE crypto automation function"""
    logger.info("🚀 Starting FREE crypto automation with Perplexity PRO...")
    logger.info(f"⏰ Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info("💰 Cost: $0.00 - Using Perplexity PRO for everything!")
    
    if not is_weekday():
        logger.info("📅 Weekend detected - skipping automation")
        return
    
    # Get environment variables (only 3 needed!)
    perplexity_api_key = os.getenv('PERPLEXITY_API_KEY', '').strip()
    telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
    telegram_channel_id = os.getenv('TELEGRAM_CHANNEL_ID', '').strip()
    
    # Validate environment variables
    errors = []
    if not perplexity_api_key:
        errors.append("PERPLEXITY_API_KEY is missing")
    if not telegram_bot_token:
        errors.append("TELEGRAM_BOT_TOKEN is missing")
    if not telegram_channel_id:
        errors.append("TELEGRAM_CHANNEL_ID is missing")
    
    if errors:
        logger.error("❌ Environment validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)
    
    logger.info("✅ All environment variables validated")
    
    temp_files = []
    
    try:
        # Initialize services (Perplexity PRO only!)
        perplexity = PerplexityProCryptoGenerator(perplexity_api_key)
        telegram = TelegramChannelBot(telegram_bot_token, telegram_channel_id)
        
        # Generate crypto news and images with Perplexity PRO
        logger.info("🔮 Generating crypto content with Perplexity PRO...")
        crypto_summary, image_urls = perplexity.get_crypto_news_with_images()
        
        # Download images from Perplexity
        downloaded_images = []
        if image_urls:
            logger.info(f"📸 Processing {len(image_urls)} images from Perplexity...")
            for i, url in enumerate(image_urls[:3], 1):  # Limit to 3 images
                logger.info(f"🖼️ Downloading image {i}/{min(len(image_urls), 3)}")
                image_path = telegram.download_image(url)
                if image_path:
                    downloaded_images.append(image_path)
                    temp_files.append(image_path)
        
        # Send to Telegram
        success = False
        
        if len(downloaded_images) >= 1:
            # Send first image with caption
            success = telegram.send_photo_with_caption(downloaded_images[0], crypto_summary)
        else:
            # Text only fallback
            logger.warning("⚠️ No images available, sending text only")
            success = telegram.send_message(crypto_summary)
        
        if success:
            logger.info("🎉 FREE crypto automation completed successfully!")
            logger.info(f"📊 Posted: Text + {len(downloaded_images)} images")
            logger.info("💸 Total cost: $0.00 (Perplexity PRO)")
        else:
            logger.error("❌ Failed to post to Telegram")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Automation failed: {e}")
        sys.exit(1)
    
    finally:
        # Cleanup
        cleanup_temp_files(temp_files)

if __name__ == "__main__":
    main()
