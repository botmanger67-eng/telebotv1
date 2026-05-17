import asyncio
import logging
from typing import Optional

from duckduckgo_search import DDGS  # type: ignore

logger = logging.getLogger(__name__)

# Default safe search setting. Can be overridden via config or environment.
DEFAULT_SAFE_SEARCH = "moderate"  # "off", "moderate", "strict"

# Maximum number of results per query
MAX_RESULTS = 5

# Timeout seconds for each search call
TIMEOUT = 10


def _web_search_sync(
    query: str,
    max_results: int = MAX_RESULTS,
    safe_search: str = DEFAULT_SAFE_SEARCH,
) -> list[dict[str, str]]:
    """Perform synchronous DuckDuckGo web search.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.
        safe_search: Safe search setting ('off', 'moderate', 'strict').

    Returns:
        List of dicts with keys 'title', 'href', 'body' (snippet).
        Returns empty list on error.

    Raises:
        ValueError: If query is empty or max_results invalid.
    """
    if not query or not query.strip():
        raise ValueError("Search query must not be empty.")
    if max_results < 1:
        raise ValueError("max_results must be >= 1")

    try:
        with DDGS(timeout=TIMEOUT) as ddgs:
            results = list(
                ddgs.text(
                    keywords=query,
                    region="wt-wt",  # worldwide
                    safesearch=safe_search,
                    timelimit=None,  # no time limit
                    max_results=max_results,
                )
            )
        # Normalize keys: 'href' is the URL, 'body' is the snippet.
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
    """Perform synchronous DuckDuckGo news search.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.
        safe_search: Safe search setting (same as web).

    Returns:
        List of dicts with keys 'title', 'href', 'body', 'date', 'source'.
        Returns empty list on error.

    Raises:
        ValueError: If query is empty or max_results invalid.
    """
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
    """Perform synchronous DuckDuckGo image search.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.
        safe_search: Safe search setting.

    Returns:
        List of dicts with keys 'title', 'image', 'thumbnail', 'url', 'height', 'width'.
        Returns empty list on error.

    Raises:
        ValueError: If query is empty or max_results invalid.
    """
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


async def web_search(
    query: str,
    max_results: int = MAX_RESULTS,
    safe_search: str = DEFAULT_SAFE_SEARCH,
) -> list[dict[str, str]]:
    """Asynchronously perform DuckDuckGo web search.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.
        safe_search: Safe search setting.

    Returns:
        List of dicts with title, href, body.
    """
    return await asyncio.to_thread(_web_search_sync, query, max_results, safe_search)


async def news_search(
    query: str,
    max_results: int = MAX_RESULTS,
    safe_search: str = DEFAULT_SAFE_SEARCH,
) -> list[dict[str, str]]:
    """Asynchronously perform DuckDuckGo news search.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.
        safe_search: Safe search setting.

    Returns:
        List of dicts with title, href, body, date, source.
    """
    return await asyncio.to_thread(_news_search_sync, query, max_results, safe_search)


async def image_search(
    query: str,
    max_results: int = MAX_RESULTS,
    safe_search: str = DEFAULT_SAFE_SEARCH,
) -> list[dict[str, str]]:
    """Asynchronously perform DuckDuckGo image search.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.
        safe_search: Safe search setting.

    Returns:
        List of dicts with title, image, thumbnail, url, height, width.
    """
    return await asyncio.to_thread(_image_search_sync, query, max_results, safe_search)