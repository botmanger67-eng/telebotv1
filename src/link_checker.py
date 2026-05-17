import asyncio
import logging
import re
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

import aiohttp
from aiohttp import ClientTimeout, ClientError

from src.config import Config
from src.ai_chat import get_ai_response  # Assuming this function exists
from src.github_tools import process_github_url  # Assuming this function exists
from src.database import log_link_activity  # Assuming this function exists

logger = logging.getLogger(__name__)

# Compile regex for URL detection (supports http/https/ftp)
URL_PATTERN = re.compile(
    r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*',
    re.IGNORECASE
)

# Maximum content size to fetch (500 KB)
MAX_CONTENT_SIZE = 500 * 1024
# Timeout for HTTP requests
HTTP_TIMEOUT = ClientTimeout(total=10)


class LinkChecker:
    """Detects URLs in messages, fetches content, and analyzes it."""

    def __init__(self, config: Config):
        self.config = config
        self.user_agent = config.get('user_agent', 'TelegramBot/1.0')

    async def extract_urls(self, text: str) -> List[str]:
        """Extract all URLs from the given text.

        Args:
            text: Input text possibly containing URLs.

        Returns:
            List of extracted URL strings.
        """
        return URL_PATTERN.findall(text)

    async def fetch_url_content(self, url: str) -> Optional[str]:
        """Fetch content from a URL asynchronously.

        Args:
            url: URL to fetch.

        Returns:
            Content as text if successful, None otherwise.
        """
        try:
            async with aiohttp.ClientSession(
                headers={'User-Agent': self.user_agent},
                timeout=HTTP_TIMEOUT
            ) as session:
                async with session.get(url, allow_redirects=True) as response:
                    if response.status != 200:
                        logger.warning("HTTP %d for URL %s", response.status, url)
                        return None
                    content_type = response.headers.get('Content-Type', '')
                    # Only fetch text-based content (HTML, plain text, etc.)
                    if 'text' not in content_type and 'json' not in content_type:
                        logger.info("Skipping non-text content: %s", content_type)
                        return None
                    # Read limited amount
                    content = await response.content.read(MAX_CONTENT_SIZE)
                    # Try to decode; fallback to utf-8, ignore errors
                    try:
                        decoded = content.decode('utf-8')
                    except UnicodeDecodeError:
                        decoded = content.decode('latin-1', errors='ignore')
                    return decoded
        except asyncio.TimeoutError:
            logger.error("Timeout fetching URL: %s", url)
        except ClientError as e:
            logger.error("HTTP client error for URL %s: %s", url, str(e))
        except Exception as e:
            logger.exception("Unexpected error fetching URL %s: %s", url, str(e))
        return None

    async def analyze_with_ai(self, url: str, content: str) -> Optional[str]:
        """Analyze fetched content using AI.

        Args:
            url: Original URL (for context).
            content: Fetched content as string.

        Returns:
            AI-generated analysis response, or None.
        """
        # Truncate content to avoid token limits (approx 4000 chars)
        truncated_content = content[:4000]
        # Build a prompt for the AI
        prompt = (
            f"Analyze the content from URL: {url}\n\n"
            f"Content:\n{truncated_content}\n\n"
            "Provide a concise summary and identify key information "
            "(e.g., weather data, translations, calculations, GitHub info). "
            "If the URL is a GitHub repository, mention that special handling exists."
        )
        try:
            # Use the ai_chat module to get response
            response = await get_ai_response(prompt)
            return response
        except Exception as e:
            logger.exception("AI analysis failed for URL %s: %s", url, str(e))
            return None

    async def handle_github_url(self, url: str) -> Optional[str]:
        """Process a GitHub URL using dedicated github_tools module.

        Args:
            url: A GitHub URL.

        Returns:
            String with GitHub information, or None.
        """
        try:
            result = await process_github_url(url)
            return result
        except Exception as e:
            logger.exception("Failed to process GitHub URL %s: %s", url, str(e))
            return None

    async def process_url(self, url: str) -> Optional[str]:
        """Process a single URL: fetch content and analyze.

        Args:
            url: URL to process.

        Returns:
            Analysis response string, or None if failed.
        """
        # Normalize URL (e.g., fix missing scheme)
        parsed = urlparse(url)
        if not parsed.scheme:
            url = 'https://' + url.lstrip('/')

        # Check if it's a GitHub URL
        if 'github.com' in url.lower():
            logger.info("Detected GitHub URL: %s", url)
            github_response = await self.handle_github_url(url)
            if github_response:
                return github_response
            # Fallback to general content fetch if github_tools fails

        # Fetch content
        content = await self.fetch_url_content(url)
        if content is None:
            logger.warning("No content fetched from %s", url)
            return None

        # Analyze with AI
        analysis = await self.analyze_with_ai(url, content)
        return analysis

    async def process_message_links(self, text: str) -> Optional[str]:
        """Extract and process all URLs in a message, returning combined analysis.

        Args:
            text: The user's message text.

        Returns:
            String with analysis results for all found URLs, or None.
        """
        urls = await self.extract_urls(text)
        if not urls:
            return None

        # Process each URL sequentially to avoid overwhelming
        results = []
        for url in urls:
            result = await self.process_url(url)
            if result:
                results.append(result)
            # Small delay to be polite
            await asyncio.sleep(0.5)

        if not results:
            return None

        combined = "\n\n---\n\n".join(results)
        # Log the activity
        try:
            await log_link_activity(user_id=None, urls=urls, result_summary=combined[:200])
        except Exception as e:
            logger.warning("Failed to log link activity: %s", str(e))

        return combined


# Module-level convenience functions using default config
_default_checker = None


def get_default_checker() -> LinkChecker:
    """Get or create the default LinkChecker instance using global Config."""
    global _default_checker
    if _default_checker is None:
        from src.config import get_config
        config = get_config()
        _default_checker = LinkChecker(config)
    return _default_checker


async def extract_urls(text: str) -> List[str]:
    """Convenience function to extract URLs from text."""
    checker = get_default_checker()
    return await checker.extract_urls(text)


async def process_message_links(text: str) -> Optional[str]:
    """Convenience function to process links in a message."""
    checker = get_default_checker()
    return await checker.process_message_links(text)