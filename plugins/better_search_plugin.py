from plugin_base import MCPPlugin
from typing import Dict, Any, List
import sys
import os
import logging
import asyncio

logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from enhanced_crawler import EnhancedWebCrawler
from shared.local_quality_assessor import LocalQualityAssessor
from shared.local_query_refiner import LocalQueryRefiner


class BetterSearchPlugin(MCPPlugin):
    """
    Better Search Plugin - 100% Privacy-Focused

    Combines intelligent search with recursive crawling for deep content exploration.
    Features:
    - Hybrid strategy (parallel search + recursive crawl)
    - Local quality assessment (no external APIs)
    - Automatic query refinement
    - Adaptive depth adjustment
    - Privacy-preserving (all processing local)

    Strategies:
    - hybrid: Search and crawl in parallel, dynamically adjust based on quality
    """

    def __init__(self):
        try:
            import config

            searxng_url = config.SEARXNG_BASE_URL + "/search"

            # Initialize components
            self.crawler = EnhancedWebCrawler(
                searxng_url=searxng_url,
                cache_maxsize=100,
                cache_ttl_minutes=5,
                cache_max_age_minutes=30,
                rate_limit_requests_per_minute=300,
                rate_limit_timeout_seconds=60,
            )

            self.quality_assessor = LocalQualityAssessor()
            self.query_refiner = LocalQueryRefiner()

            logger.info(
                "🔬 BetterSearchPlugin initialized (100% local, privacy-focused)"
            )
        except Exception as e:
            logger.error(f"❌ BetterSearchPlugin init error: {e}")
            self.crawler = None
            self.quality_assessor = None
            self.query_refiner = None

    @property
    def name(self) -> str:
        return "better_search"

    @property
    def description(self) -> str:
        return (
            "Better search with intelligent search and recursive crawling. "
            "Automatically refines queries based on quality assessment. "
            "100% privacy-focused - no external APIs."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Research query"},
                "search_depth": {
                    "type": "integer",
                    "default": 2,
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Maximum search refinement iterations (1-5)",
                },
                "crawl_depth": {
                    "type": "integer",
                    "default": 2,
                    "minimum": 0,
                    "maximum": 5,
                    "description": "Recursive crawl depth for URLs (0=no recursion, 5=max)",
                },
                "max_pages": {
                    "type": "integer",
                    "default": 25,
                    "minimum": 5,
                    "maximum": 100,
                    "description": "Maximum total pages to collect (5-100)",
                },
                "quality_threshold": {
                    "type": "number",
                    "default": 0.6,
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Minimum quality score to stop refining (0.0-1.0)",
                },
                "category": {
                    "type": "string",
                    "default": "general",
                    "enum": ["general", "it", "science", "news"],
                    "description": "Search category focus",
                },
                "language": {
                    "type": "string",
                    "default": "auto",
                    "description": "Language preference (e.g., 'en-US', 'auto')",
                },
            },
            "required": ["query"],
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute deep research."""
        if not self.crawler or not self.quality_assessor or not self.query_refiner:
            return {"success": False, "error": "Plugin not properly initialized"}

        # Extract parameters
        query = args.get("query", "")
        search_depth = args.get("search_depth", 2)
        crawl_depth = args.get("crawl_depth", 2)
        max_pages = args.get("max_pages", 25)
        quality_threshold = args.get("quality_threshold", 0.6)
        category = args.get("category", "general")
        language = args.get("language", "auto")

        if not query:
            return {"success": False, "error": "Query is required"}

        logger.info(
            f"🔬 Better Search: '{query}' | search_depth={search_depth}, crawl_depth={crawl_depth}, max_pages={max_pages}"
        )

        # Execute hybrid strategy
        return await self._execute_hybrid(
            query=query,
            search_depth=search_depth,
            crawl_depth=crawl_depth,
            max_pages=max_pages,
            quality_threshold=quality_threshold,
            category=category,
            language=language,
        )

    async def _execute_hybrid(
        self,
        query: str,
        search_depth: int,
        crawl_depth: int,
        max_pages: int,
        quality_threshold: float,
        category: str,
        language: str,
    ) -> Dict[str, Any]:
        """
        Hybrid strategy: Parallel search and recursive crawl with adaptive quality control.

        Flow:
        1. Initial search
        2. Assess quality
        3. If insufficient: refine query + search again (parallel)
        4. Extract URLs from high-quality results
        5. Recursive crawl on those URLs (if crawl_depth > 0)
        6. Continue until quality threshold met or max iterations
        """
        all_results = []
        search_iterations = 0
        current_query = query

        for iteration in range(1, search_depth + 1):
            search_iterations = iteration
            logger.info(
                f"🔄 Iteration {iteration}/{search_depth}: Query='{current_query}'"
            )

            # Search
            search_results = await self.crawler.search_with_category(
                query=current_query,
                limit=min(10, max_pages),
                category=category,
                language=language,
            )

            if not search_results.get("success"):
                logger.error(f"❌ Search failed: {search_results.get('error')}")
                break

            results = search_results.get("results", [])

            if not results:
                logger.warning(f"⚠️ No results for '{current_query}'")
                break

            # Assess quality
            results_with_scores = self.quality_assessor.assess_multiple(
                results, current_query
            )
            avg_quality = self.quality_assessor.get_average_quality(results_with_scores)

            logger.info(
                f"📊 Quality: {avg_quality:.3f} (threshold: {quality_threshold})"
            )

            # Add to collection
            all_results.extend(results_with_scores)

            # Check if quality is sufficient
            if avg_quality >= quality_threshold:
                logger.info(
                    f"✅ Quality threshold met ({avg_quality:.3f} >= {quality_threshold})"
                )
                break

            # Refine query for next iteration
            if iteration < search_depth:
                current_query = self.query_refiner.refine_query(
                    original_query=current_query, iteration=iteration
                )
                logger.info(f"🔄 Query refined: '{current_query}'")

        # Deduplicate results by URL
        unique_results = self._deduplicate_by_url(all_results)
        logger.info(f"📑 Collected {len(unique_results)} unique results from search")

        # Recursive crawling (if enabled and we need more content)
        if crawl_depth > 0 and len(unique_results) < max_pages:
            logger.info(f"🕷️ Starting recursive crawl (depth={crawl_depth})")

            # Extract top URLs for crawling
            top_results = sorted(
                unique_results, key=lambda x: x.get("quality_score", 0), reverse=True
            )[:5]  # Top 5 high-quality URLs

            crawl_urls = [r.get("url") for r in top_results if r.get("url")]

            if crawl_urls:
                remaining_pages = max_pages - len(unique_results)
                crawl_results = await self.crawler.crawl_with_depth(
                    start_urls=crawl_urls,
                    max_depth=crawl_depth,
                    max_pages=remaining_pages,
                    same_domain_only=True,
                )

                # Assess quality of crawled content
                crawl_results_with_scores = self.quality_assessor.assess_multiple(
                    crawl_results, query
                )

                unique_results.extend(crawl_results_with_scores)
                logger.info(
                    f"🕷️ Added {len(crawl_results_with_scores)} pages from recursive crawl"
                )

        # Final deduplication and sorting
        final_results = self._deduplicate_by_url(unique_results)
        final_results.sort(key=lambda x: x.get("quality_score", 0), reverse=True)

        # Limit to max_pages
        final_results = final_results[:max_pages]

        # Calculate final statistics
        final_avg_quality = self.quality_assessor.get_average_quality(final_results)

        logger.info(
            f"✅ Better Search Complete: {len(final_results)} pages, avg_quality={final_avg_quality:.3f}"
        )

        return {
            "success": True,
            "query": query,
            "final_query": current_query,
            "search_iterations": search_iterations,
            "crawl_depth_used": crawl_depth,
            "total_results": len(final_results),
            "average_quality": final_avg_quality,
            "quality_threshold": quality_threshold,
            "threshold_met": final_avg_quality >= quality_threshold,
            "results": final_results,
            "summary": {
                "excellent": sum(
                    1 for r in final_results if r.get("quality_score", 0) >= 0.8
                ),
                "good": sum(
                    1 for r in final_results if 0.7 <= r.get("quality_score", 0) < 0.8
                ),
                "fair": sum(
                    1 for r in final_results if 0.6 <= r.get("quality_score", 0) < 0.7
                ),
                "poor": sum(
                    1 for r in final_results if r.get("quality_score", 0) < 0.6
                ),
            },
        }

    def _deduplicate_by_url(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate results by URL, keeping the highest quality version.

        Args:
            results: List of result dicts with 'url' and 'quality_score'

        Returns:
            Deduplicated list
        """
        seen_urls = {}

        for result in results:
            url = result.get("url")
            if not url:
                continue

            quality = result.get("quality_score", 0)

            if url not in seen_urls or quality > seen_urls[url].get("quality_score", 0):
                seen_urls[url] = result

        return list(seen_urls.values())


# Export plugin
def create_plugin() -> MCPPlugin:
    """Factory function for plugin creation."""
    return BetterSearchPlugin()
