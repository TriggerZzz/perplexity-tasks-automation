#!/usr/bin/env python3
"""
Complete Perplexity Tasks Automation for Telegram
Automatically extracts content from Perplexity Tasks and posts to Telegram channel
with text and images, Monday-Friday at 19:00 PM
"""

import os
import sys
import json
import time
import logging
import requests
import tempfile
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from urllib.parse import urlparse

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('perplexity_automation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class PerplexityTasksExtractor:
    """Extract content from Perplexity Tasks"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def get_task_content(self, query: str) -> Dict[str, Any]:
        """Get content from Perplexity with images enabled"""
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {
                    "role": "user", 
                    "content": query
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.2,
            "return_citations": True,
            "return_images": True
        }
        
        try:
            logger.info(f"Sending request to Perplexity API...")
            response = requests.post(
                self.base_url,
                headers=self.headers, 
                json=payload,
                timeout=60
            )
            
            logger.info(f"Response status code: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"API response content: {response.text}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Perplexity API error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Perplexity request: {e}")
            raise

class TelegramChannelBot:
    """Enhanced Telegram bot for posting to channels with images"""
    
    def __init__(self, bot_token: str, channel_id: str):
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def download_image(self, image_url: str) -> Optional[str]:
        """Download image from URL and return local path"""
        try:
            response = requests.get(image_url, timeout=30, stream=True)
            response.raise_for_status()
            
            parsed_url = urlparse(image_url)
            file_ext = Path(parsed_url.path).suffix or '.jpg'
            
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=file_ext,
                dir=tempfile.gettempdir()
            )
            
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            
            temp_file.close()
            logger.info(f"Downloaded image to: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Failed to download image {image_url}: {e}")
            return None
    
    def send_photo(self, photo_path: str, caption: str = "") -> bool:
        """Send photo with caption to Telegram channel"""
        url = f"{self.base_url}/sendPhoto"
        
        try:
            with open(photo_path, 'rb') as photo_file:
                files = {'photo': photo_file}
                data = {
                    'chat_id': self.channel_id,
                    'caption': caption[:1024] if caption else "",
                    'parse_mode': 'Markdown'
                }
                
                response = requests.post(url, files=files, data=data, timeout=30)
                response.raise_for_status()
                
                logger.info("Photo sent successfully to Telegram channel")
                return True
                
        except Exception as e:
            logger.error(f"Failed to send photo: {e}")
            return False
    
    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Send text message to Telegram channel"""
        url = f"{self.base_url}/sendMessage"
        
        max_length = 4000
        messages = []
        
        if len(text) <= max_length:
            messages.append(text)
        else:
            paragraphs = text.split('\n\n')
            current_message = ""
            
            for paragraph in paragraphs:
                if len(current_message + paragraph) <= max_length:
                    current_message += paragraph + "\n\n"
                else:
                    if current_message:
                        messages.append(current_message.strip())
                    current_message = paragraph + "\n\n"
            
            if current_message:
                messages.append(current_message.strip())
        
        success = True
        for i, message in enumerate(messages):
            payload = {
                "chat_id": self.channel_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            try:
                response = requests.post(url, json=payload, timeout=30)
                response.raise_for_status()
                
                if i < len(messages) - 1:
                    time.sleep(2)
                    
                logger.info(f"Message part {i+1}/{len(messages)} sent successfully")
                
            except Exception as e:
                logger.error(f"Failed to send message part {i+1}: {e}")
                success = False
        
        return success

def format_perplexity_content(response: Dict[str, Any]) -> Tuple[str, List[str]]:
    """Format Perplexity response content and extract image URLs"""
    try:
        content = response['choices'][0]['message']['content']
        citations = response.get('citations', [])
        
        # Extract images from response
        images = []
        if 'images' in response:
            for img in response['images']:
                if isinstance(img, str):
                    images.append(img)
                elif isinstance(img, dict) and 'url' in img:
                    images.append(img['url'])
        
        # Format the main message
        formatted_message = f"📊 **Daily Research Update**\n"
        formatted_message += f"🕒 *{datetime.now().strftime('%B %d, %Y at %H:%M UTC')}*\n\n"
        formatted_message += content
        
        if citations:
            formatted_message += "\n\n📚 **Sources:**\n"
            for i, citation in enumerate(citations[:5], 1):
                formatted_message += f"{i}. {citation}\n"
        
        formatted_message += "\n\n🤖 *Automated via Perplexity AI*"
        
        return formatted_message, images
        
    except Exception as e:
        logger.error(f"Error formatting Perplexity content: {e}")
        return "❌ Error processing today's update. Please check the logs.", []

def get_daily_query() -> str:
    """Generate daily query - customize this for your specific task"""
    weekday = datetime.now().weekday()
    
    queries = {
        0: "What are the most significant tech and AI developments this week? Include recent breakthroughs, product launches, and industry news.",
        1: "What are the latest startup funding rounds, IPOs, and major business news today?", 
        2: "What are the current market trends, economic indicators, and financial news affecting global markets?",
        3: "What are the recent scientific discoveries, research breakthroughs, and medical advances?",
        4: "What are today's most important global news events, political developments, and social trends?"
    }
    
    return queries.get(weekday, "What are the most important developments and news today across technology, business, and current events?")

def cleanup_temp_files(file_paths: List[str]):
    """Clean up temporary downloaded image files"""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {file_path}: {e}")

def is_weekday() -> bool:
    """Check if today is a weekday (Monday-Friday)"""
    return datetime.now().weekday() < 5

def main():
    """Main automation function"""
    logger.info("Starting daily Perplexity automation...")
    logger.info(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    if not is_weekday():
        logger.info("Today is weekend, skipping automation")
        return
    
    perplexity_api_key = os.getenv('PERPLEXITY_API_KEY', '').strip()
    telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
    telegram_channel_id = os.getenv('TELEGRAM_CHANNEL_ID', '').strip()
    
    errors = []
    if not perplexity_api_key:
        errors.append("PERPLEXITY_API_KEY is missing or empty")
    elif not perplexity_api_key.startswith('pplx-'):
        errors.append("PERPLEXITY_API_KEY format appears incorrect (should start with 'pplx-')")
    
    if not telegram_bot_token:
        errors.append("TELEGRAM_BOT_TOKEN is missing or empty")
    elif ':' not in telegram_bot_token:
        errors.append("TELEGRAM_BOT_TOKEN format appears incorrect (should contain ':')")
    
    if not telegram_channel_id:
        errors.append("TELEGRAM_CHANNEL_ID is missing or empty")
    elif not (telegram_channel_id.startswith('@') or telegram_channel_id.startswith('-100')):
        errors.append("TELEGRAM_CHANNEL_ID format appears incorrect (should start with '@' or '-100')")
    
    if errors:
        logger.error("Environment variable validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        logger.error("Please check your GitHub repository secrets")
        sys.exit(1)
    
    logger.info("✅ All environment variables validated successfully")
    
    temp_files = []
    
    try:
        perplexity = PerplexityTasksExtractor(perplexity_api_key)
        telegram = TelegramChannelBot(telegram_bot_token, telegram_channel_id)
        
        query = get_daily_query()
        logger.info(f"Today's query: {query}")
        
        logger.info("Fetching content from Perplexity...")
        response = perplexity.get_task_content(query)
        
        formatted_text, image_urls = format_perplexity_content(response)
        
        downloaded_images = []
        if image_urls:
            logger.info(f"Downloading {len(image_urls)} images...")
            for url in image_urls[:5]:
                image_path = telegram.download_image(url)
                if image_path:
                    downloaded_images.append({'path': image_path, 'url': url})
                    temp_files.append(image_path)
        
        success = True
        
        if downloaded_images:
            if len(downloaded_images) == 1:
                success = telegram.send_photo(
                    downloaded_images[0]['path'], 
                    formatted_text
                )
            else:
                success = telegram.send_message(formatted_text)
        else:
            success = telegram.send_message(formatted_text)
        
        if success:
            logger.info("✅ Daily automation completed successfully!")
            logger.info(f"Posted content with {len(downloaded_images)} images to Telegram channel")
        else:
            logger.error("❌ Failed to post to Telegram channel")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Automation failed: {e}")
        sys.exit(1)
    
    finally:
        cleanup_temp_files(temp_files)

if __name__ == "__main__":
    main()
