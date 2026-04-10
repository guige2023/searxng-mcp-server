import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any, List
import asyncio

# Import User-Agent rotation from enhanced_crawler
from enhanced_crawler import get_user_agent, get_headers_for_url, USER_AGENT_POOL

# Legacy constant for backward compatibility
DEFAULT_USER_AGENT = USER_AGENT_POOL[0]


class WebCrawler:
    """
    Web Crawler with SearXNG search and webpage fetching
    Includes mock mode for testing without SearXNG
    """

    def __init__(self, mock_mode: bool = False):
        self.searxng_url = "http://localhost:32768/search"
        self.mock_mode = mock_mode

        if self.mock_mode:
            import sys

            print(f"   🎭 WebCrawler initialized in MOCK MODE", file=sys.stderr)
        else:
            import sys

            print(f"   🌐 WebCrawler initialized: {self.searxng_url}", file=sys.stderr)

    async def search_searxng(
        self,
        query: str,
        limit: int = 10,
        category: str = "general",
        language: str = "auto",
        time_range: str = "",
        safe_search: int = 1,
    ) -> List[Dict[str, Any]]:
        """Search using SearXNG with multi-page support"""

        if self.mock_mode:
            import sys

            print(f"   🎭 MOCK: Returning fake results for '{query}'", file=sys.stderr)
            return self._generate_mock_results(query, limit)

        try:
            all_results = []
            page = 1
            max_pages = 10  # 최대 10페이지 (충분히 많이)

            import sys

            print(f"   🌐 SearXNG: {self.searxng_url}", file=sys.stderr)
            import sys

            print(f"      Query: {query}, Target limit: {limit}", file=sys.stderr)

            while len(all_results) < limit and page <= max_pages:
                params = {
                    "q": query,
                    "format": "json",
                    "pageno": page,
                    "categories": category,
                    "safesearch": safe_search,
                }

                if language != "auto":
                    params["language"] = language

                if time_range:
                    params["time_range"] = time_range

                for attempt in range(1, 4):
                    try:
                        async with httpx.AsyncClient(
                            timeout=10.0, follow_redirects=True
                        ) as client:
                            import sys

                            print(
                                f"      🔄 Page {page}, Attempt {attempt}/3...",
                                file=sys.stderr,
                            )

                            response = await client.get(
                                self.searxng_url,
                                params=params,
                                headers=get_headers_for_url(self.searxng_url),
                            )

                            import sys

                            print(
                                f"      📡 Status: {response.status_code}",
                                file=sys.stderr,
                            )

                            response.raise_for_status()
                            data = response.json()

                            page_results = data.get("results", [])

                            if not page_results:
                                import sys

                                print(
                                    f"      ⚠️ No more results on page {page}",
                                    file=sys.stderr,
                                )
                                return self._format_results(
                                    all_results, limit, category
                                )

                            all_results.extend(page_results)
                            import sys

                            print(
                                f"      ✅ Got {len(page_results)} results (total: {len(all_results)}/{limit})",
                                file=sys.stderr,
                            )

                            # 목표 달성
                            if len(all_results) >= limit:
                                return self._format_results(
                                    all_results, limit, category
                                )

                            page += 1
                            await asyncio.sleep(0.5)  # 서버 부담 줄이기
                            break  # attempt 루프 탈출

                    except (httpx.ConnectError, httpx.TimeoutException) as e:
                        if attempt < 3:
                            await asyncio.sleep(1)
                            continue
                        raise

                # Attempt 루프 실패 시
                if len(all_results) == 0:
                    raise Exception("Failed to fetch any results")

            # Max pages 도달
            return self._format_results(all_results, limit, category)

        except Exception as e:
            import sys

            print(f"   ⚠️ SearXNG error: {str(e)[:100]}", file=sys.stderr)
            import sys

            print(f"   🎭 Falling back to MOCK results", file=sys.stderr)
            return self._generate_mock_results(query, limit)

    def _format_results(
        self, results: List[Dict], limit: int, category: str
    ) -> List[Dict[str, Any]]:
        """Format and limit search results"""
        results = results[:limit]

        formatted_results = []
        for idx, result in enumerate(results, 1):
            formatted_results.append(
                {
                    "position": idx,
                    "title": result.get("title", "No title"),
                    "url": result.get("url", ""),
                    "content": result.get("content", "No description"),
                    "engine": result.get("engine", "unknown"),
                    "category": result.get("category", category),
                }
            )

        import sys

        print(f"      ✅ Final: {len(formatted_results)} results", file=sys.stderr)
        return formatted_results

    def _generate_mock_results(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Generate mock search results for testing"""

        templates = [
            ("Wikipedia", "wiki", "Wikipedia article"),
            ("Official Site", "site", "Official website"),
            ("Comprehensive Guide", "guide", "Detailed guide"),
            ("Tutorial", "tutorial", "Step-by-step tutorial"),
            ("Latest News", "news", "Breaking news"),
            ("Community Forum", "forum", "Discussion forum"),
            ("Expert Blog", "blog", "Professional blog post"),
            ("Video Tutorial", "video", "Video guide"),
            ("Documentation", "docs", "Official docs"),
            ("Review", "review", "Expert review"),
            ("Research Paper", "research", "Academic research"),
            ("Analysis", "analysis", "In-depth analysis"),
            ("Comparison", "compare", "Detailed comparison"),
            ("FAQ", "faq", "Common questions"),
            ("Tools & Resources", "tools", "Useful tools"),
            ("Case Study", "case", "Real-world example"),
            ("Best Practices", "best", "Industry standards"),
            ("Beginner's Guide", "beginner", "Introduction"),
            ("Advanced Topics", "advanced", "Expert-level"),
            ("Industry Report", "report", "Market analysis"),
            ("Trends", "trends", "Current trends"),
            ("Statistics", "stats", "Data and statistics"),
            ("Infographic", "infographic", "Visual guide"),
            ("Podcast", "podcast", "Audio discussion"),
            ("Webinar", "webinar", "Online seminar"),
            ("Course", "course", "Learning material"),
            ("Template", "template", "Ready-to-use template"),
            ("Checklist", "checklist", "Action checklist"),
            ("Timeline", "timeline", "Historical overview"),
            ("Database", "database", "Resource database"),
        ]

        mock_results = []
        for idx in range(min(limit, len(templates))):
            title_suffix, url_part, content_desc = templates[idx]
            mock_results.append(
                {
                    "position": idx + 1,
                    "title": f"{title_suffix}: {query}",
                    "url": f"https://example.com/{url_part}/{query.replace(' ', '-')}-{idx + 1}",
                    "content": f"Mock result {idx + 1}: {content_desc} about {query}. This is a comprehensive resource with detailed information.",
                    "engine": "mock",
                    "category": "general",
                }
            )

        # If limit > templates, repeat with variations
        if limit > len(templates):
            for idx in range(len(templates), limit):
                template_idx = idx % len(templates)
                title_suffix, url_part, content_desc = templates[template_idx]
                mock_results.append(
                    {
                        "position": idx + 1,
                        "title": f"{title_suffix} #{idx + 1}: {query}",
                        "url": f"https://example.com/{url_part}/{query.replace(' ', '-')}-{idx + 1}",
                        "content": f"Mock result {idx + 1}: Additional {content_desc} about {query}.",
                        "engine": "mock",
                        "category": "general",
                    }
                )

        import sys

        print(f"      🎭 Generated {len(mock_results)} mock results", file=sys.stderr)
        return mock_results

    async def fetch_webpage(
        self, url: str, max_length: int = 10000, timeout: int = 30
    ) -> Dict[str, Any]:
        """Fetch and extract content from webpage"""

        if self.mock_mode:
            import sys

            print(f"   🎭 MOCK: Fetching fake content for {url}", file=sys.stderr)
            return {
                "success": True,
                "url": url,
                "content": f"Mock webpage content for {url}. " * 50,
                "title": f"Mock Page - {url}",
                "description": "Mock description for testing",
                "language": "en",
                "content_length": 1500,
            }

        try:
            async with httpx.AsyncClient(
                timeout=timeout, follow_redirects=True
            ) as client:
                response = await client.get(url, headers=get_headers_for_url(url))
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                # Remove unwanted elements
                for element in soup(
                    ["script", "style", "nav", "footer", "header", "aside"]
                ):
                    element.decompose()

                # Extract text
                text = soup.get_text(separator="\n", strip=True)

                # Clean up text
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                content = "\n".join(lines)[:max_length]

                # Extract metadata
                title = soup.find("title")
                title_text = title.get_text(strip=True) if title else ""

                description = soup.find("meta", attrs={"name": "description"})
                description_text = description.get("content", "") if description else ""

                language = soup.find("html")
                language_code = language.get("lang", "") if language else ""

                return {
                    "success": True,
                    "url": url,
                    "content": content,
                    "title": title_text,
                    "description": description_text,
                    "language": language_code,
                    "content_length": len(content),
                }

        except httpx.TimeoutException:
            return {
                "success": False,
                "url": url,
                "error": f"Request timed out after {timeout}s",
            }

        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "url": url,
                "error": f"HTTP {e.response.status_code}",
            }

        except Exception as e:
            return {
                "success": False,
                "url": url,
                "error": f"{type(e).__name__}: {str(e)}",
            }
