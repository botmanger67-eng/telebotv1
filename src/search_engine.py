import asyncio
import logging
from typing import Optional, List, Dict

from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

# Default safe search setting
DEFAULT_SAFE_SEARCH = "moderate"

# Maximum number of results per query
MAX_RESULTS = 5

# Timeout seconds for each search call
TIMEOUT = 10


def _web_search_sync(
    query: str,
    max_results: int = MAX_RESULTS,
    safe_search: str = DEFAULT_SAFE_SEARCH,
) -> list[dict[str, str]]:
    """Perform synchronous DuckDuckGo web search."""
    if not query or not query.strip():
        raise ValueError("Search query must not be empty.")
    if max_results < 1:
        raise ValueError("max_results must be >= 1")

    try:
        with DDGS(timeout=TIMEOUT) as ddgs:
            results = list(
                ddgs.text(
                    keywords=query,
                    region="wt-wt",
                    safesearch=safe_search,
                    timelimit=None,
                    max_results=max_results,
                )
            )
        return [
            {
                "title": r.get("title", ""),
                "href": r.get("href", ""),
                "body": r.get("body", ""),
            }
            for r in results
        ]
    except Exception as e:
        logger.exception(f"Web search failed for query '{query}': {e}")
        return []


def _news_search_sync(
    query: str,
    max_results: int = MAX_RESULTS,
    safe_search: str = DEFAULT_SAFE_SEARCH,
) -> list[dict[str, str]]:
    """Perform synchronous DuckDuckGo news search."""
    if not query or not query.strip():
        raise ValueError("Search query must not be empty.")
    if max_results < 1:
        raise ValueError("max_results must be >= 1")

    try:
        with DDGS(timeout=TIMEOUT) as ddgs:
            results = list(
                ddgs.news(
                    keywords=query,
                    region="wt-wt",
                    safesearch=safe_search,
                    timelimit=None,
                    max_results=max_results,
                )
            )
        return [
            {
                "title": r.get("title", ""),
                "href": r.get("url", ""),
                "body": r.get("body", ""),
                "date": r.get("date", ""),
                "source": r.get("source", ""),
            }
            for r in results
        ]
    except Exception as e:
        logger.exception(f"News search failed for query '{query}': {e}")
        return []


def _image_search_sync(
    query: str,
    max_results: int = MAX_RESULTS,
    safe_search: str = DEFAULT_SAFE_SEARCH,
) -> list[dict[str, str]]:
    """Perform synchronous DuckDuckGo image search."""
    if not query or not query.strip():
        raise ValueError("Search query must not be empty.")
    if max_results < 1:
        raise ValueError("max_results must be >= 1")

    try:
        with DDGS(timeout=TIMEOUT) as ddgs:
            results = list(
                ddgs.images(
                    keywords=query,
                    region="wt-wt",
                    safesearch=safe_search,
                    size=None,
                    color=None,
                    type_image=None,
                    layout=None,
                    license_image=None,
                    max_results=max_results,
                )
            )
        return [
            {
                "title": r.get("title", ""),
                "image": r.get("image", ""),
                "thumbnail": r.get("thumbnail", ""),
                "url": r.get("url", ""),
                "height": r.get("height", ""),
                "width": r.get("width", ""),
            }
            for r in results
        ]
    except Exception as e:
        logger.exception(f"Image search failed for query '{query}': {e}")
        return []


# ── Async Wrappers ─────────────────────────────────────────────────────

async def web_search(
    query: str,
    max_results: int = MAX_RESULTS,
    safe_search: str = DEFAULT_SAFE_SEARCH,
) -> list[dict[str, str]]:
    """Asynchronously perform DuckDuckGo web search."""
    return await asyncio.to_thread(_web_search_sync, query, max_results, safe_search)


async def news_search(
    query: str,
    max_results: int = MAX_RESULTS,
    safe_search: str = DEFAULT_SAFE_SEARCH,
) -> list[dict[str, str]]:
    """Asynchronously perform DuckDuckGo news search."""
    return await asyncio.to_thread(_news_search_sync, query, max_results, safe_search)


async def image_search(
    query: str,
    max_results: int = MAX_RESULTS,
    safe_search: str = DEFAULT_SAFE_SEARCH,
) -> list[dict[str, str]]:
    """Asynchronously perform DuckDuckGo image search."""
    return await asyncio.to_thread(_image_search_sync, query, max_results, safe_search)


# ── ✅ FIXED: Wrapper Functions (main.py ke imports ke liye) ───────────

async def get_weather(city: str) -> str:
    """Get current weather for a city using DuckDuckGo search.

    Args:
        city: City name to search weather for.

    Returns:
        Formatted weather string.
    """
    try:
        results = await web_search(f"weather {city} today temperature celsius")
        if results:
            return f"🌤 **Weather for {city.title()}:**\n\n{results[0]['body']}\n\n🔗 {results[0]['href']}"
        return f"❌ No weather info found for **{city}**."
    except Exception as e:
        logger.error(f"Weather fetch error for {city}: {e}")
        return "❌ Could not fetch weather data. Please try again."


async def translate_text(text: str, target_lang: str) -> str:
    """Translate text to target language using DuckDuckGo search.

    Args:
        text: Text to translate.
        target_lang: Target language name or code (e.g., 'Spanish', 'French', 'es', 'fr').

    Returns:
        Translated text string.
    """
    try:
        results = await web_search(f"translate '{text}' to {target_lang}")
        if results:
            return f"🌐 **Translation ({target_lang}):**\n\n{results[0]['body']}"
        return "❌ Translation failed. Please check language name and try again."
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return "❌ Translation service unavailable. Please try again later."


async def get_news(category: str = "general") -> List[Dict[str, str]]:
    """Get latest news for a category.

    Args:
        category: News category (e.g., 'technology', 'sports', 'business', 'general').

    Returns:
        List of news article dicts with title, href, body, date, source.
    """
    try:
        if category.lower() == "general":
            query = "latest world news today"
        else:
            query = f"latest {category} news today"
        return await news_search(query, max_results=5)
    except Exception as e:
        logger.error(f"News fetch error for {category}: {e}")
        return []


async def get_image(description: str) -> Optional[str]:
    """Get image URL for a description.

    Args:
        description: Image description to search for.

    Returns:
        Image URL string if found, None otherwise.
    """
    try:
        results = await image_search(description, max_results=1)
        if results:
            return results[0]['image']
        return None
    except Exception as e:
        logger.error(f"Image search error for '{description}': {e}")
        return None
