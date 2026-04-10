from plugin_base import MCPPlugin
from typing import Dict, Any
import sys
import os
import logging

logger = logging.getLogger(__name__)

# Add parent directory to path to import enhanced_crawler
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from enhanced_crawler import EnhancedWebCrawler


class EnhancedCrawlPlugin(MCPPlugin):
    """
    Enhanced Web Page Fetching Plugin

    Features:
    - PDF reading with Markdown conversion
    - Caching with TTL and validation
    - Rate limiting
    - Reddit URL conversion (old.reddit.com)
    - Enhanced content extraction with Trafilatura
    """

    def __init__(self):
        try:
            import config

            searxng_url = config.SEARXNG_BASE_URL + "/search"

            self.crawler = EnhancedWebCrawler(
                searxng_url=searxng_url,
                cache_maxsize=100,
                cache_ttl_minutes=10,
                cache_max_age_minutes=30,
                rate_limit_requests_per_minute=300,  # 사실상 무제한
                rate_limit_timeout_seconds=60,
            )
            logger.info("🕷️ EnhancedCrawlPlugin: Crawler initialized")
        except Exception as e:
            logger.info(f"⚠️ EnhancedCrawlPlugin: Crawler init error: {e}")
            self.crawler = None

    @property
    def name(self) -> str:
        return "get_website"

    @property
    def description(self) -> str:
        return (
            "Fetch and extract content from webpages with enhanced features. "
            "Supports HTML and PDF files (converts PDF to Markdown). "
            "Uses caching for performance and rate limiting for politeness. "
            "Automatically converts Reddit URLs to old.reddit.com."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL of the webpage to fetch"},
                "max_length": {
                    "type": "integer",
                    "default": 60000,
                    "description": "Maximum content length in characters",
                },
                "timeout": {
                    "type": "integer",
                    "default": 30,
                    "description": "Request timeout in seconds",
                },
                "use_cache": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to use caching",
                },
            },
            "required": ["url"],
        }

    @property
    def version(self) -> str:
        return "4.0.0"

    @property
    def author(self) -> str:
        return "damin25soka7"

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch and extract content from a webpage.

        Returns:
        {
            "success": bool,
            "url": str,
            "title": str,
            "content": str,
            "excerpt": str,
            "date_accessed": str,
            "content_length": int
        }
        """
        url = arguments.get("url", "").strip()
        max_length = arguments.get("max_length", 10000)
        timeout = arguments.get("timeout", 30)
        use_cache = arguments.get("use_cache", True)

        # Validation
        if not url:
            return {"success": False, "error": "URL parameter is required"}

        # Add https:// if no scheme
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            logger.info(f"ℹ️ Added https:// prefix to URL")

        # Clamp parameters
        max_length = max(100, min(50000, max_length))
        timeout = max(5, min(120, timeout))

        logger.info(
            f"Enhanced get_website v4.0.0 - URL: {url}, Max length: {max_length}, Use cache: {use_cache}"
        )

        try:
            result = await self.crawler.fetch_webpage_enhanced(
                url=url, max_length=max_length, timeout=timeout, use_cache=use_cache
            )

            return result

        except Exception as e:
            return {
                "success": False,
                "url": url,
                "error": f"Failed to fetch webpage: {str(e)}",
            }
