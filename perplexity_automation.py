#!/usr/bin/env python3
"""
Daily Perplexity Task Automation for Telegram
Automated Python script to fetch Perplexity AI research and send to Telegram group
"""

import os
import sys
import logging
import requests
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class PerplexityClient:
    """Client for interacting with Perplexity API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def search(self, query: str, model: str = "sonar-pro") -> Dict[str, Any]:
        """Perform a search query using Perplexity AI"""
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": query}],
            "max_tokens": 1000,
            "temperature": 0.7,
            "return_citations": True,
            "return_images": False
        }
        
        try:
            response = requests.post(
                self.base_url, headers=self.headers, json=payload, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Perplexity API error: {e}")
            raise

class TelegramBot:
    """Client for sending messages to Telegram"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Send a message to the Telegram chat"""
        url = f"{self.base_url}/sendMessage"
        
        # Split message if too long (4096 char limit)
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
                "chat_id": self.chat_id,
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
                logger.error(f"Telegram error for part {i+1}: {e}")
                success = False
        
        return success

def format_perplexity_response(response: Dict[str, Any]) -> str:
    """Format Perplexity API response for Telegram"""
    try:
        content = response['choices']['message']['content']
        citations = response.get('citations', [])
        
        formatted_message = f"📊 **Daily AI Research Update**\n"
        formatted_message += f"🕒 *{datetime.now().strftime('%B %d, %Y at %H:%M UTC')}*\n\n"
        formatted_message += content
        
        if citations:
            formatted_message += "\n\n📚 **Sources:**\n"
            for i, citation in enumerate(citations[:5], 1):
                formatted_message += f"{i}. {citation}\n"
        
        formatted_message += "\n\n🤖 *Powered by Perplexity AI*"
        return formatted_message
        
    except Exception as e:
        logger.error(f"Error formatting response: {e}")
        return "❌ Error formatting the research update."

def get_daily_query() -> str:
    """Customize this to match your exact Perplexity Task"""
    
    # Replace this with your actual task query
    return """

- "Summarize today's top global news about crypto market. Include major economic events, and highlight any breaking news about future events. Make an article no more than 1,500 characters (without spaces).
At the end of the article include these two hashtags "#CryptoNews #MarketOverview""

- "Create an image as well to post it with this article.
do your best!
cinematic scene, fx, HDR, epic composition, cinematic photo, hyper - realistic, hyper - detailed, cinematic lighting, particle effects, action photography, 
hyper realistic, 8k resolution, unreal engine, photorealistic masterpiece, smooth, real photography, full hd, Megapixel, Pro Photo RGB, VR, Good, Massive, 
Half rear Lighting, Backlight, Incandescent, Optical Fiber, Moody Lighting, Studio Lighting, Soft Lighting, Volumetric, Conte - Jour, Beautiful Lighting, 
Accent Lighting, Screen, Ray Tracing Global Illumination, Optics, Scattering, Glowing, Shadows, Rough, Shimmering, Ray Tracing Reflections, Lumen Reflections, 
Screen Space Reflections, Diffraction Grading, Chromatic Aberration, GB Displacement, Scan Lines, Ray Traced."
    """


def main():
    """Main automation function"""
    logger.info("Starting daily Perplexity automation...")
    
# Get environment variables
perplexity_api_key = os.getenv('PERPLEXITY_API_KEY')
telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
telegram_channel_id = os.getenv('TELEGRAM_CHANNEL_ID')

# Debug logging (will show *** in logs for security)
logger.info(f"PERPLEXITY_API_KEY present: {bool(perplexity_api_key)}")
logger.info(f"TELEGRAM_BOT_TOKEN present: {bool(telegram_bot_token)}")
logger.info(f"TELEGRAM_CHANNEL_ID present: {bool(telegram_channel_id)}")

# More specific validation
if not perplexity_api_key:
    logger.error("PERPLEXITY_API_KEY environment variable not set or empty")
    sys.exit(1)

if not telegram_bot_token:
    logger.error("TELEGRAM_BOT_TOKEN environment variable not set or empty")
    sys.exit(1)

if not telegram_channel_id:
    logger.error("TELEGRAM_CHANNEL_ID environment variable not set or empty")
    sys.exit(1)

logger.info("All environment variables validated successfully")
    
    try:
        # Initialize clients
        perplexity = PerplexityClient(perplexity_api_key)
        telegram = TelegramBot(telegram_bot_token, telegram_chat_id)
        
        # Get today's query
        query = get_daily_query()
        logger.info(f"Today's query: {query}")
        
        # Perform search and send
        response = perplexity.search(query)
        formatted_message = format_perplexity_response(response)
        success = telegram.send_message(formatted_message)
        
        if success:
            logger.info("✅ Daily automation completed successfully!")
        else:
            logger.error("❌ Failed to send message")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Automation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
