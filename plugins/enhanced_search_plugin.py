from plugin_base import MCPPlugin
from typing import Dict, Any
import sys
import os
import logging

logger = logging.getLogger(__name__)

# Add parent directory to path to import enhanced_crawler
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from enhanced_crawler import EnhancedWebCrawler


class EnhancedSearchPlugin(MCPPlugin):
    """
    Enhanced Web Search Plugin with category support

    Features:
    - Category-aware search (general, images, videos, files, map, social media)
    - PDF reading with Markdown conversion
    - Enhanced content extraction with Trafilatura
    - Caching with TTL and validation
    - Rate limiting
    """

    def __init__(self):
        try:
            import config

            searxng_url = config.SEARXNG_BASE_URL + "/search"

            self.crawler = EnhancedWebCrawler(
                searxng_url=searxng_url,
                cache_maxsize=100,
                cache_ttl_minutes=5,
                cache_max_age_minutes=30,
                rate_limit_requests_per_minute=60,  # 분당 60개로 제한 (품질 향상)
                rate_limit_timeout_seconds=60,
            )
            logger.info("🔍 EnhancedSearchPlugin: Crawler initialized")
        except Exception as e:
            logger.info(f"⚠️ EnhancedSearchPlugin: Crawler init error: {e}")
            self.crawler = None

    @property
    def name(self) -> str:
        return "search_web"

    @property
    def description(self) -> str:
        return (
            "Enhanced web search with category support and Wikipedia integration. "
            "Categories: general (scrapes content + Wikipedia infoboxes), images, videos, files, map, social media. "
            "Supports PDF reading, caching, and intelligent rate limiting. "
            "Wikipedia infoboxes are automatically included in general search results for better quality."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query string"},
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum number of results (1-60)",
                },
                "category": {
                    "type": "string",
                    "default": "general",
                    "enum": [
                        "general",
                        "images",
                        "videos",
                        "files",
                        "map",
                        "social media",
                    ],
                    "description": "Search category",
                },
                "language": {
                    "type": "string",
                    "default": "auto",
                    "description": "Language preference (e.g., 'en-US', 'auto')",
                },
                "time_range": {
                    "type": "string",
                    "default": "",
                    "enum": ["", "day", "month", "year"],
                    "description": "Filter by time range",
                },
                "safe_search": {
                    "type": "integer",
                    "default": 1,
                    "enum": [0, 1, 2],
                    "description": "Safe search level (0: None, 1: Moderate, 2: Strict)",
                },
                "engines": {
                    "type": "string",
                    "description": "Optional comma-separated list of engines (e.g., 'google,wikipedia')",
                },
            },
            "required": ["query"],
        }

    @property
    def version(self) -> str:
        return "4.0.0"

    @property
    def author(self) -> str:
        return "damin25soka7"

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute enhanced web search with category support.

        Returns structured data based on category:
        - general: Scraped webpage content
        - images: Image URLs with metadata
        - videos: Video information
        - files: File download links
        - map: Location data
        - social media: Social posts
        """
        query = arguments.get("query", "").strip()
        limit = arguments.get("limit", 10)
        category = arguments.get("category", "general")
        language = arguments.get("language", "auto")
        time_range = arguments.get("time_range", "")
        safe_search = arguments.get("safe_search", 1)
        engines = arguments.get("engines")

        # Validation
        if not query:
            return {
                "success": False,
                "error": "Query parameter is required and cannot be empty",
            }

        # Clamp limit
        limit = max(1, min(60, limit))

        logger.info(
            f"Enhanced search_web v4.0.0 - Query: '{query}', Category: {category}, Limit: {limit}"
        )

        try:
            result = await self.crawler.search_with_category(
                query=query,
                limit=limit,
                category=category,
                language=language,
                time_range=time_range,
                safe_search=safe_search,
                engines=engines,
            )

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Search failed: {str(e)}",
                "query": query,
                "category": category,
            }
