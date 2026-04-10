"""
Enhanced Web Crawler with advanced features from mcp-searxng-enhanced
Includes:
- Category-aware search (images, videos, files, map, social media)
- PDF reading with Markdown conversion
- Caching with TTL and validation
- Rate limiting
- Reddit URL conversion
- Enhanced content extraction with Trafilatura
"""

import asyncio
import httpx
import time
import re
import unicodedata
import json
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional, Set
from urllib.parse import urlparse, urljoin
from datetime import datetime, timezone
from cachetools import TTLCache
from dateutil import parser as date_parser
from collections import deque
import trafilatura
import filetype
from charset_normalizer import from_bytes
import pymupdf
import pymupdf4llm
import logging

logger = logging.getLogger(__name__)

# Suppress trafilatura's noisy logging
logging.getLogger("trafilatura.core").setLevel(logging.CRITICAL)
logging.getLogger("trafilatura").setLevel(logging.CRITICAL)

# ========================================
# User-Agent Configuration (with Rotation)
# ========================================
# Rotate User-Agents to avoid bot detection (403 errors)
# Controlled by environment variables:
#   USER_AGENT_ROTATION: true/false (default: true)
#   USER_AGENT_STRATEGY: random/domain-sticky (default: random)
#   CUSTOM_USER_AGENTS: comma-separated custom UAs (optional)

import os
import random

# Built-in User Agent Pool (10 realistic browser UAs)
USER_AGENT_POOL = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    # Chrome Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Firefox Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Safari Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    # Chrome Android
    "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.135 Mobile Safari/537.36",
    # Safari iOS
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    # Samsung Browser
    "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/23.0 Chrome/115.0.0.0 Mobile Safari/537.36",
    # Opera Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/106.0.0.0",
]

# Domain-sticky map (for domain-sticky strategy)
_domain_ua_map: Dict[str, str] = {}


def _get_user_agent_pool() -> List[str]:
    """
    Get User Agent pool from environment or use defaults.
    Supports CUSTOM_USER_AGENTS env variable for adding custom UAs.
    """
    custom_agents = os.getenv("CUSTOM_USER_AGENTS", "").strip()

    if custom_agents:
        # Parse comma-separated custom agents
        custom_list = [ua.strip() for ua in custom_agents.split(",") if ua.strip()]
        if custom_list:
            logger.info(f"[UA] Added {len(custom_list)} custom User Agents to pool")
            return USER_AGENT_POOL + custom_list

    return USER_AGENT_POOL


def get_user_agent(url: str = "") -> str:
    """
    Get User Agent for request based on configured strategy.

    Strategies:
    - random: Random UA for every request (DEFAULT)
    - domain-sticky: Same UA for same domain

    Environment variables:
    - USER_AGENT_ROTATION: true/false (default: true)
    - USER_AGENT_STRATEGY: random/domain-sticky (default: random)

    Args:
        url: URL being requested (used for domain-sticky strategy)

    Returns:
        User Agent string
    """
    # Check if rotation is enabled
    rotation_enabled = os.getenv("USER_AGENT_ROTATION", "true").lower() in (
        "true",
        "1",
        "yes",
    )

    if not rotation_enabled:
        # Rotation disabled, use first UA
        return USER_AGENT_POOL[0]

    # Get strategy
    strategy = os.getenv("USER_AGENT_STRATEGY", "random").lower()

    # Get pool (includes custom UAs if set)
    pool = _get_user_agent_pool()

    if strategy == "domain-sticky" and url:
        # Domain-sticky: Same UA for same domain
        domain = urlparse(url).netloc
        if domain not in _domain_ua_map:
            _domain_ua_map[domain] = random.choice(pool)
            logger.debug(f"[UA] Assigned new UA to domain: {domain}")
        return _domain_ua_map[domain]

    # Random (default)
    return random.choice(pool)


# Legacy constant for backward compatibility (will use first UA in pool)
DEFAULT_USER_AGENT = USER_AGENT_POOL[0]

# Default headers template (User-Agent is set dynamically per request)
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


def get_headers_for_url(url: str = "") -> Dict[str, str]:
    """
    Get complete headers with dynamic User-Agent for a specific URL.

    Args:
        url: URL being requested (used for User-Agent selection)

    Returns:
        Dict of HTTP headers
    """
    ua = get_user_agent(url)
    return {"User-Agent": ua, **DEFAULT_HEADERS}


class RateLimiter:
    """Domain-based rate limiting for web requests."""

    def __init__(self, requests_per_minute: int = 10, timeout_seconds: int = 60):
        self.requests_per_minute = requests_per_minute
        self.timeout_seconds = timeout_seconds
        self.domain_requests: dict = {}

    def can_request(self, url: str) -> bool:
        """Check if a request to the given URL is allowed under rate limits."""
        domain = urlparse(url).netloc
        if not domain:
            return True

        now = time.time()

        # Clean up old entries for this domain
        if domain in self.domain_requests:
            cutoff = now - 60  # 1 minute window
            self.domain_requests[domain] = [
                t for t in self.domain_requests[domain] if t > cutoff
            ]
        else:
            self.domain_requests[domain] = []

        # Check if we're under the limit
        return len(self.domain_requests[domain]) < self.requests_per_minute

    def record_request(self, url: str) -> None:
        """Record a request to a URL for rate limiting purposes."""
        domain = urlparse(url).netloc
        if not domain:
            return

        now = time.time()
        if domain not in self.domain_requests:
            self.domain_requests[domain] = []
        self.domain_requests[domain].append(now)

    def get_remaining_time(self, url: str) -> float:
        """Get remaining wait time in seconds before next request is allowed."""
        domain = urlparse(url).netloc
        if not domain or domain not in self.domain_requests:
            return 0.0

        now = time.time()
        cutoff = now - 60
        timestamps = [t for t in self.domain_requests[domain] if t > cutoff]

        if len(timestamps) < self.requests_per_minute:
            return 0.0

        # Need to wait until oldest request expires
        oldest = min(timestamps)
        return max(0.0, (oldest + 60) - now)


class CacheValidator:
    """Validates cached web content freshness."""

    @staticmethod
    def is_valid(cached_result: Dict[str, Any], max_age_minutes: int = 30) -> bool:
        """Check if a cached result is still valid."""
        if not cached_result:
            return False

        if "date_accessed" not in cached_result:
            return False

        try:
            date_accessed = date_parser.parse(cached_result["date_accessed"])
            now = datetime.now(timezone.utc)
            age_td = now - date_accessed
            return age_td.total_seconds() < (max_age_minutes * 60)
        except (ValueError, TypeError):
            return False


class HelperFunctions:
    """Helper utilities for content processing."""

    @staticmethod
    def decode_response_content(response: httpx.Response) -> str:
        """Decode response content with robust charset detection.

        Many Korean sites still serve `euc-kr`/`cp949` or incorrect headers.
        This attempts: declared encoding -> charset detection -> UTF-8 fallback.
        """
        raw = response.content or b""
        if not raw:
            return ""

        # 1) If httpx detected an encoding, try it first
        enc = (response.encoding or "").strip()
        if enc:
            try:
                return raw.decode(enc, errors="replace")
            except Exception:
                pass

        # 2) Charset detection (works well for EUC-KR/CP949)
        try:
            best = from_bytes(raw).best()
            if best is not None and best.encoding:
                return str(best)
        except Exception:
            pass

        # 3) Fallback
        try:
            return raw.decode("utf-8", errors="replace")
        except Exception:
            return raw.decode(errors="replace")

    @staticmethod
    def remove_emojis(text: str) -> str:
        """Remove emoji characters from text."""
        return "".join(c for c in text if not unicodedata.category(c).startswith("So"))

    @staticmethod
    def format_text_with_trafilatura(html_content: str, timeout: int = 15) -> str:
        """Extract clean text from HTML using Trafilatura."""
        # Validate input
        if not html_content or not html_content.strip():
            logger.warning("Empty HTML content received")
            return ""

        try:
            extracted_text = trafilatura.extract(
                html_content,
                favor_readability=True,
                include_comments=False,
                include_tables=True,
                timeout=timeout,
            )
        except Exception as e:
            logger.warning(f"Trafilatura extraction failed: {e}")
            extracted_text = None

        if not extracted_text:
            soup = BeautifulSoup(html_content, "html.parser")
            extracted_text = soup.get_text(separator="\n", strip=True)
            if not extracted_text:
                logger.warning(
                    "Both Trafilatura and BeautifulSoup failed to extract text"
                )
                return ""
            logger.debug("Trafilatura failed, used BeautifulSoup fallback")

        lines = [
            unicodedata.normalize("NFKC", line).strip()
            for line in extracted_text.splitlines()
        ]
        cleaned_lines = [re.sub(r"\s{2,}", " ", line) for line in lines if line]
        formatted_text = "\n".join(cleaned_lines)

        return HelperFunctions.remove_emojis(formatted_text).strip()

    @staticmethod
    def truncate_to_n_words(text: str, word_limit: int) -> str:
        """Truncate text to a specified number of words."""
        tokens = text.split()
        if len(tokens) <= word_limit:
            return text
        return " ".join(tokens[:word_limit]) + "..."

    @staticmethod
    def generate_excerpt(content: str, max_length: int = 200) -> str:
        """Generate a short excerpt from content."""
        lines = content.splitlines()
        excerpt = ""
        for line in lines:
            if len(excerpt) + len(line) + 1 < max_length:
                excerpt += line + "\n"
            else:
                remaining_len = max_length - len(excerpt) - 4
                if remaining_len > 0:
                    excerpt += line[:remaining_len] + " ..."
                break
        return excerpt.strip() if excerpt else content[:max_length] + "..."

    @staticmethod
    def modify_reddit_url(url: str) -> str:
        """Convert Reddit URLs to old.reddit.com for better scraping."""
        match = re.match(r"^(https?://)(www\.)?(reddit\.com)(.*)$", url, re.IGNORECASE)
        if match:
            protocol = match.group(1)
            path_and_query = match.group(4)
            return f"{protocol}old.reddit.com{path_and_query}"
        return url


class EnhancedWebCrawler:
    """
    Enhanced Web Crawler with advanced features:
    - Category-aware search
    - PDF reading with Markdown conversion
    - Caching with TTL
    - Rate limiting
    - Enhanced content extraction
    """

    def __init__(
        self,
        searxng_url: str = "http://localhost:32768/search",
        cache_maxsize: int = 100,
        cache_ttl_minutes: int = 5,
        cache_max_age_minutes: int = 30,
        rate_limit_requests_per_minute: int = 10,
        rate_limit_timeout_seconds: int = 60,
        mock_mode: bool = False,
    ):
        self.searxng_url = searxng_url
        self.mock_mode = mock_mode
        self.cache_max_age_minutes = cache_max_age_minutes

        # Initialize cache
        self.website_cache = TTLCache(maxsize=cache_maxsize, ttl=cache_ttl_minutes * 60)

        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            requests_per_minute=rate_limit_requests_per_minute,
            timeout_seconds=rate_limit_timeout_seconds,
        )

        logger.info(f"EnhancedWebCrawler initialized: {self.searxng_url}")
        logger.info(
            f"Cache: maxsize={cache_maxsize}, ttl={cache_ttl_minutes}min, max_age={cache_max_age_minutes}min"
        )
        logger.info(f"Rate limit: {rate_limit_requests_per_minute} req/min per domain")

    async def search_with_category(
        self,
        query: str,
        limit: int = 10,
        category: str = "general",
        language: str = "auto",
        time_range: str = "",
        safe_search: int = 1,
        engines: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search with category support (general, images, videos, files, map, social media).
        Returns structured data appropriate for the category.
        """
        try:
            # Clean query: remove site: operators that break infobox retrieval
            import re

            clean_query = re.sub(
                r"\s*site:\S+\s*", " ", query, flags=re.IGNORECASE
            ).strip()
            # Also remove common noise words that break infobox retrieval
            clean_query = re.sub(
                r"\b(infobox|wikipedia)\b", "", clean_query, flags=re.IGNORECASE
            ).strip()
            # Clean up multiple spaces
            clean_query = re.sub(r"\s+", " ", clean_query).strip()

            if clean_query != query:
                logger.info(f"🧹 Query cleaned: '{query}' → '{clean_query}'")

            params = {
                "q": clean_query,
                "format": "json",
                "pageno": 1,
                "categories": category.lower(),
                "safesearch": safe_search,
            }

            if engines:
                params["engines"] = engines

            if language != "auto":
                params["language"] = language

            if time_range:
                params["time_range"] = time_range

            logger.info(f"🔍 Category Search: '{query}' in '{category}'")

            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                http2=False,  # Disable HTTP/2 to avoid Wikipedia 403
                verify=True,
            ) as client:
                response = await client.get(
                    self.searxng_url,
                    params=params,
                    headers=get_headers_for_url(self.searxng_url),
                )

                response.raise_for_status()

                # Decode safely (handles EUC-KR/CP949 or bad headers)
                json_text = HelperFunctions.decode_response_content(response)
                data = json.loads(json_text) if json_text else {}
                results = data.get("results", [])
                infoboxes = data.get("infoboxes", [])

                logger.info(
                    f"✅ Got {len(results)} raw results, {len(infoboxes)} infoboxes"
                )

                # Process results based on category
                if category.lower() == "images":
                    return await self._process_image_results(results, limit)
                elif category.lower() == "videos":
                    return await self._process_video_results(results, limit)
                elif category.lower() == "files":
                    return await self._process_file_results(results, limit)
                elif category.lower() == "map":
                    return await self._process_map_results(results, limit)
                elif category.lower() == "social media":
                    return await self._process_social_results(results, limit)
                else:
                    # General category - scrape content and include infoboxes
                    return await self._process_general_results(
                        results, limit, infoboxes if infoboxes else []
                    )

        except Exception as e:
            logger.error(f" Search error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "category": category,
                "results": [],
            }

    async def _process_image_results(
        self, results: List[Dict], limit: int
    ) -> Dict[str, Any]:
        """Process image search results."""
        processed = []
        for result in results[:limit]:
            processed.append(
                {
                    "type": "image",
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "img_src": result.get("img_src", ""),
                    "thumbnail": result.get("thumbnail_src", ""),
                }
            )

        return {
            "success": True,
            "category": "images",
            "count": len(processed),
            "results": processed,
        }

    async def _process_video_results(
        self, results: List[Dict], limit: int
    ) -> Dict[str, Any]:
        """Process video search results."""
        processed = []
        for result in results[:limit]:
            processed.append(
                {
                    "type": "video",
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "iframe_src": result.get("iframe_src", ""),
                    "thumbnail": result.get("thumbnail", ""),
                }
            )

        return {
            "success": True,
            "category": "videos",
            "count": len(processed),
            "results": processed,
        }

    async def _process_file_results(
        self, results: List[Dict], limit: int
    ) -> Dict[str, Any]:
        """Process file search results."""
        processed = []
        for result in results[:limit]:
            processed.append(
                {
                    "type": "file",
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "format": result.get("format", ""),
                    "size": result.get("size", ""),
                }
            )

        return {
            "success": True,
            "category": "files",
            "count": len(processed),
            "results": processed,
        }

    async def _process_map_results(
        self, results: List[Dict], limit: int
    ) -> Dict[str, Any]:
        """Process map/location search results."""
        processed = []
        for result in results[:limit]:
            processed.append(
                {
                    "type": "map",
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "address": result.get("address", ""),
                    "latitude": result.get("latitude"),
                    "longitude": result.get("longitude"),
                    "content": result.get("content", ""),
                }
            )

        return {
            "success": True,
            "category": "map",
            "count": len(processed),
            "results": processed,
        }

    async def _process_social_results(
        self, results: List[Dict], limit: int
    ) -> Dict[str, Any]:
        """Process social media search results."""
        processed = []
        for result in results[:limit]:
            processed.append(
                {
                    "type": "social",
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                }
            )

        return {
            "success": True,
            "category": "social media",
            "count": len(processed),
            "results": processed,
        }

    async def _process_general_results(
        self, results: List[Dict], limit: int, infoboxes: List[Dict] = None
    ) -> Dict[str, Any]:
        """Process general web search results with content scraping, including Wikipedia infoboxes."""
        processed = []

        # First, add Wikipedia infoboxes from SearXNG (no API calls needed)
        if infoboxes:
            for infobox in infoboxes[:3]:  # Limit to 3 infoboxes
                # Extract primary URL
                urls = infobox.get("urls", [])
                primary_url = urls[0].get("url") if urls else infobox.get("id", "")

                # Use infobox content directly from SearXNG (API is blocked)
                content = infobox.get("content", "")
                processed.append(
                    {
                        "type": "infobox",
                        "source": "wikipedia",
                        "title": infobox.get("infobox", ""),
                        "url": primary_url,
                        "content": content,
                        "excerpt": content[:500] + "..."
                        if len(content) > 500
                        else content,
                        "img_src": infobox.get("img_src"),
                        "date_accessed": datetime.now(timezone.utc).isoformat(),
                        "content_length": len(content),
                    }
                )
                logger.info(
                    f"📚 Added Wikipedia infobox: {infobox.get('infobox', '')[:50]} ({len(content)} chars)"
                )

        for result in results[:limit]:
            url = result.get("url", "")
            if not url:
                continue

            # Skip Wikipedia URLs - direct access is blocked (403)
            # Wikipedia content should come from SearXNG infoboxes
            if "wikipedia.org/wiki/" in url:
                if infoboxes:
                    logger.info(f"⏭️  Skipping Wikipedia URL (have infobox): {url[:60]}")
                else:
                    # No infobox, but still can't scrape - add snippet only
                    logger.info(f"⏭️  Skipping Wikipedia URL (API blocked): {url[:60]}")
                    processed.append(
                        {
                            "type": "webpage",
                            "title": result.get("title", ""),
                            "url": url,
                            "snippet": result.get("content", ""),
                            "error": "Wikipedia direct access blocked",
                        }
                    )
                continue

            # Check rate limit
            if not self.rate_limiter.can_request(url):
                logger.warning(f"⚠️  Rate limit exceeded for {urlparse(url).netloc}")
                # Still add the result with snippet only
                processed.append(
                    {
                        "type": "webpage",
                        "title": result.get("title", ""),
                        "url": url,
                        "snippet": result.get("content", ""),
                        "error": "Rate limit exceeded, showing snippet only",
                    }
                )
                continue

            # Try to scrape content
            content_data = await self.fetch_webpage_enhanced(url, max_length=20000)

            if content_data.get("success"):
                processed.append(
                    {
                        "type": "webpage",
                        "title": content_data.get("title", result.get("title", "")),
                        "url": url,
                        "content": content_data.get("content", ""),
                        "excerpt": content_data.get("excerpt", ""),
                        "snippet": result.get("content", ""),
                        "date_accessed": content_data.get("date_accessed", ""),
                    }
                )
            else:
                # If fetch failed, still provide snippet
                processed.append(
                    {
                        "type": "webpage",
                        "title": result.get("title", ""),
                        "url": url,
                        "snippet": result.get("content", ""),
                        "error": content_data.get("error", "Failed to fetch"),
                    }
                )

        return {
            "success": True,
            "category": "general",
            "count": len(processed),
            "infoboxes_included": len(infoboxes) if infoboxes else 0,
            "results": processed,
        }

    async def _process_news_results(
        self, results: List[Dict[str, Any]], limit: int = 10
    ) -> Dict[str, Any]:
        """Process news results with simplified fetching."""
        processed = []

        for result in results[:limit]:
            url = result.get("url", "")
            if not url:
                continue

            # Skip Wikipedia URLs - direct access is blocked (403)
            if "wikipedia.org/wiki/" in url:
                logger.info(f"⏭️  Skipping Wikipedia URL (API blocked): {url[:60]}")
                processed.append(
                    {
                        "type": "webpage",
                        "title": result.get("title", ""),
                        "url": url,
                        "snippet": result.get("content", ""),
                        "error": "Wikipedia direct access blocked",
                    }
                )
                continue

            # Check rate limit
            if not self.rate_limiter.can_request(url):
                logger.warning(f"⚠️  Rate limit exceeded for {urlparse(url).netloc}")
                # Still add the result with snippet only
                processed.append(
                    {
                        "type": "webpage",
                        "title": result.get("title", ""),
                        "url": url,
                        "snippet": result.get("content", ""),
                        "error": "Rate limit exceeded, showing snippet only",
                    }
                )
                continue

            # Try to scrape content
            content_data = await self.fetch_webpage_enhanced(url, max_length=20000)

            if content_data.get("success"):
                processed.append(
                    {
                        "type": "webpage",
                        "title": content_data.get("title", result.get("title", "")),
                        "url": url,
                        "content": content_data.get("content", ""),
                        "excerpt": content_data.get("excerpt", ""),
                        "snippet": result.get("content", ""),
                        "date_accessed": content_data.get("date_accessed", ""),
                    }
                )
            else:
                # If fetch failed, still provide snippet
                processed.append(
                    {
                        "type": "webpage",
                        "title": result.get("title", ""),
                        "url": url,
                        "snippet": result.get("content", ""),
                        "error": content_data.get("error", "Failed to fetch"),
                    }
                )

        return {
            "success": True,
            "category": "general",
            "count": len(processed),
            "infoboxes_included": len(infoboxes) if infoboxes else 0,
            "results": processed,
        }

    async def fetch_webpage_enhanced(
        self,
        url: str,
        max_length: int = 10000,
        timeout: int = 30,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Fetch webpage with enhanced features:
        - Caching with TTL and validation
        - PDF reading with Markdown conversion
        - Reddit URL conversion
        - Trafilatura content extraction
        - Wikipedia API for Wikipedia URLs (avoids 403)
        """
        # Check cache first
        if use_cache and url in self.website_cache:
            cached = self.website_cache[url]
            if CacheValidator.is_valid(cached, self.cache_max_age_minutes):
                logger.info(f"💾 Cache hit: {url[:60]}")
                return cached
            else:
                logger.info(f"🔄 Cache stale: {url[:60]}")

        # Check if this is a Wikipedia URL - skip direct fetching (403 blocked)
        # Wikipedia content should come from SearXNG infoboxes instead
        if "wikipedia.org/wiki/" in url:
            logger.info(
                f"⏭️  Skipping Wikipedia URL (use SearXNG infobox instead): {url[:60]}"
            )
            return {
                "success": False,
                "url": url,
                "error": "Wikipedia direct access blocked - use SearXNG infobox data",
                "skip_reason": "wikipedia_blocked",
            }

        try:
            # Modify Reddit URLs
            url_to_fetch = HelperFunctions.modify_reddit_url(url)

            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                http2=False,  # Disable HTTP/2 to avoid Wikipedia 403
                verify=True,
            ) as client:
                response = await client.get(
                    url_to_fetch, headers=get_headers_for_url(url_to_fetch)
                )
                response.raise_for_status()

                # Check if it's a PDF
                raw_content = response.content
                kind = filetype.guess(raw_content)

                if kind is not None and kind.mime == "application/pdf":
                    # Process PDF
                    logger.info(f"📄 PDF detected: {url[:60]}")
                    doc = pymupdf.open(stream=raw_content, filetype="pdf")
                    md_text = pymupdf4llm.to_markdown(doc)

                    content = md_text
                    truncated_content = HelperFunctions.truncate_to_n_words(
                        content, max_length // 5
                    )
                    excerpt = HelperFunctions.generate_excerpt(content)
                    title = "PDF Document (converted to Markdown)"
                else:
                    # Process HTML
                    html_content = HelperFunctions.decode_response_content(response)

                    # Validate HTML content
                    if not html_content or not html_content.strip():
                        logger.warning(f"⚠️  Empty response from {url[:60]}")
                        return {
                            "success": False,
                            "url": url,
                            "error": "Server returned empty response",
                        }

                    soup = BeautifulSoup(html_content, "html.parser")

                    # Extract title
                    title_tag = soup.find("title")
                    title = title_tag.string if title_tag else "No title"
                    title = unicodedata.normalize("NFKC", title.strip())
                    title = HelperFunctions.remove_emojis(title)

                    # Extract content
                    content = HelperFunctions.format_text_with_trafilatura(
                        html_content, timeout=15
                    )

                    # Check if extraction yielded anything
                    if not content or not content.strip():
                        logger.warning(f"⚠️  No extractable content from {url[:60]}")
                        return {
                            "success": False,
                            "url": url,
                            "error": "No readable content found (may be JavaScript-rendered or paywalled)",
                        }

                    truncated_content = HelperFunctions.truncate_to_n_words(
                        content, max_length // 5
                    )
                    excerpt = HelperFunctions.generate_excerpt(content)

                result = {
                    "success": True,
                    "url": url,
                    "title": title,
                    "content": truncated_content,
                    "excerpt": excerpt,
                    "date_accessed": datetime.now(timezone.utc).isoformat(),
                    "content_length": len(truncated_content),
                }

                # Cache the result
                if use_cache:
                    self.website_cache[url] = result

                return result

        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "url": url,
                "error": f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
            }
        except httpx.RequestError as e:
            return {"success": False, "url": url, "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {
                "success": False,
                "url": url,
                "error": f"Unexpected error: {str(e)}",
            }

    async def search_searxng(
        self,
        query: str,
        limit: int = 10,
        category: str = "general",
        language: str = "auto",
        time_range: str = "",
        safe_search: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Backward compatible search method.
        For general category, returns list of results.
        For other categories, returns structured data.
        """
        result = await self.search_with_category(
            query=query,
            limit=limit,
            category=category,
            language=language,
            time_range=time_range,
            safe_search=safe_search,
        )

        if result.get("success"):
            return result.get("results", [])
        else:
            return []

    async def fetch_webpage(
        self, url: str, max_length: int = 10000, timeout: int = 30
    ) -> Dict[str, Any]:
        """Backward compatible fetch method."""
        return await self.fetch_webpage_enhanced(url, max_length, timeout)

    async def crawl_with_depth(
        self,
        start_urls: List[str],
        max_depth: int = 2,
        max_pages: int = 25,
        same_domain_only: bool = True,
        max_length: int = 10000,
    ) -> List[Dict[str, Any]]:
        """
        Recursively crawl webpages following links up to max_depth.

        Args:
            start_urls: List of URLs to start crawling from
            max_depth: Maximum depth to follow links (0 = only start URLs)
            max_pages: Maximum total pages to crawl
            same_domain_only: Only follow links within same domain
            max_length: Max content length per page

        Returns:
            List of crawled page results with content
        """
        if not start_urls:
            return []

        logger.info(
            f"🕷️ Starting recursive crawl: {len(start_urls)} seeds, max_depth={max_depth}, max_pages={max_pages}"
        )

        visited_urls: Set[str] = set()
        results: List[Dict[str, Any]] = []

        # BFS queue: (url, current_depth)
        from collections import deque

        queue = deque([(url, 0) for url in start_urls])

        while queue and len(results) < max_pages:
            url, depth = queue.popleft()

            # Skip if already visited
            if url in visited_urls:
                continue

            # Skip if depth exceeded
            if depth > max_depth:
                continue

            # Normalize URL
            url = url.strip()
            if not url.startswith("http"):
                continue

            # Check domain restriction
            if same_domain_only and depth > 0:
                start_domain = urlparse(start_urls[0]).netloc
                current_domain = urlparse(url).netloc
                if start_domain != current_domain:
                    continue

            # Check rate limit
            if not self.rate_limiter.can_request(url):
                wait_time = self.rate_limiter.get_remaining_time(url)
                logger.warning(
                    f"⏳ Rate limit: waiting {wait_time:.1f}s for {urlparse(url).netloc}"
                )
                await asyncio.sleep(wait_time)

            # Mark as visited
            visited_urls.add(url)

            # Fetch page
            logger.info(f"📄 Crawling [{depth}/{max_depth}]: {url[:80]}")
            page_data = await self.fetch_webpage_enhanced(url, max_length=max_length)

            if not page_data.get("success"):
                logger.warning(
                    f"❌ Failed to fetch: {url[:60]} - {page_data.get('error')}"
                )
                continue

            # Add to results
            page_data["depth"] = depth
            page_data["crawled_at"] = datetime.now(timezone.utc).isoformat()
            results.append(page_data)

            # Extract links if depth allows
            if depth < max_depth:
                links = await self._extract_links_from_page(url)

                # Add links to queue
                for link in links:
                    if link not in visited_urls:
                        queue.append((link, depth + 1))

                logger.info(f"🔗 Found {len(links)} links at depth {depth}")

            # Progress update
            if len(results) % 5 == 0:
                logger.info(f"📊 Progress: {len(results)}/{max_pages} pages crawled")

        logger.info(
            f"✅ Crawling complete: {len(results)} pages, {len(visited_urls)} visited"
        )

        return results

    async def _extract_links_from_page(self, url: str) -> List[str]:
        """
        Extract all valid links from a webpage.

        Args:
            url: URL of the page

        Returns:
            List of absolute URLs found on page
        """
        try:
            async with httpx.AsyncClient(
                timeout=15.0, follow_redirects=True, http2=False, verify=True
            ) as client:
                response = await client.get(url, headers=get_headers_for_url(url))
                response.raise_for_status()

                html_content = HelperFunctions.decode_response_content(response)
                soup = BeautifulSoup(html_content, "html.parser")

                links = []
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]

                    # Convert relative URLs to absolute
                    from urllib.parse import urljoin

                    absolute_url = urljoin(url, href)

                    # Filter out invalid URLs
                    if self._is_valid_link(absolute_url):
                        links.append(absolute_url)

                return links

        except Exception as e:
            logger.debug(f"Link extraction error for {url[:60]}: {str(e)}")
            return []

    def _is_valid_link(self, url: str) -> bool:
        """
        Check if a link is valid for crawling.

        Args:
            url: URL to validate

        Returns:
            True if link is valid
        """
        # Must be HTTP/HTTPS
        if not url.startswith(("http://", "https://")):
            return False

        # Filter out common non-content URLs
        excluded_extensions = [
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".svg",
            ".ico",
            ".css",
            ".js",
            ".xml",
            ".json",
            ".zip",
            ".tar",
            ".gz",
            ".mp4",
            ".mp3",
            ".avi",
            ".mov",
            ".wav",
        ]

        url_lower = url.lower()
        if any(url_lower.endswith(ext) for ext in excluded_extensions):
            return False

        # Filter out common non-content paths
        excluded_paths = [
            "/login",
            "/signin",
            "/signup",
            "/register",
            "/logout",
            "/admin",
            "/wp-admin",
            "/user",
            "/account",
            "/cart",
            "/checkout",
            "/payment",
        ]

        parsed = urlparse(url)
        if any(excluded in parsed.path.lower() for excluded in excluded_paths):
            return False

        return True

    async def _fetch_wikipedia_via_api(
        self, url: str, max_length: int = 10000, use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Fetch Wikipedia content using the Wikipedia API to avoid 403 errors.

        Args:
            url: Wikipedia article URL
            max_length: Maximum content length
            use_cache: Whether to use caching

        Returns:
            Dict with success, title, content, etc.
        """
        try:
            # Extract article title from URL
            # https://en.wikipedia.org/wiki/Article_Title -> Article_Title
            parts = url.split("/wiki/")
            if len(parts) < 2:
                return {"success": False, "url": url, "error": "Invalid Wikipedia URL"}

            article_title = parts[1].split("#")[0]  # Remove anchor
            article_title = article_title.split("?")[0]  # Remove query params

            # Extract language from URL (e.g., 'en' from 'en.wikipedia.org')
            lang = "en"
            if "://" in url:
                domain = url.split("://")[1].split("/")[0]
                if domain.startswith(
                    tuple(
                        f"{l}."
                        for l in ["en", "ko", "ja", "zh", "de", "fr", "es", "it", "ru"]
                    )
                ):
                    lang = domain.split(".")[0]

            # Wikipedia API endpoint
            api_url = f"https://{lang}.wikipedia.org/w/api.php"

            params = {
                "action": "query",
                "format": "json",
                "titles": article_title,
                "prop": "extracts|info",
                "explaintext": True,  # Plain text, not HTML
                "exintro": False,  # Get full article, not just intro
                "inprop": "url",
                "redirects": 1,
            }

            logger.info(f"📡 Calling Wikipedia API for: {article_title}")

            async with httpx.AsyncClient(
                timeout=30.0, follow_redirects=True, http2=False, verify=True
            ) as client:
                response = await client.get(api_url, params=params)
                response.raise_for_status()

                data = response.json()
                pages = data.get("query", {}).get("pages", {})

                if not pages:
                    return {
                        "success": False,
                        "url": url,
                        "error": "No content found in Wikipedia API response",
                    }

                # Get first (and usually only) page
                page = list(pages.values())[0]

                if "missing" in page:
                    return {
                        "success": False,
                        "url": url,
                        "error": "Wikipedia article not found (404)",
                    }

                title = page.get("title", "Unknown Title")
                extract = page.get("extract", "")

                if not extract:
                    return {
                        "success": False,
                        "url": url,
                        "error": "Wikipedia article has no content",
                    }

                # Truncate content
                truncated_content = HelperFunctions.truncate_to_n_words(
                    extract, max_length // 5
                )
                excerpt = HelperFunctions.generate_excerpt(extract)

                result = {
                    "success": True,
                    "url": url,
                    "title": title,
                    "content": truncated_content,
                    "excerpt": excerpt,
                    "date_accessed": datetime.now(timezone.utc).isoformat(),
                    "content_length": len(truncated_content),
                    "source": "wikipedia_api",
                }

                # Cache the result
                if use_cache:
                    self.website_cache[url] = result

                logger.info(f"✅ Wikipedia API success: {title}")
                return result

        except Exception as e:
            logger.error(f"❌ Wikipedia API error: {str(e)}")
            return {
                "success": False,
                "url": url,
                "error": f"Wikipedia API request failed: {str(e)}",
            }
