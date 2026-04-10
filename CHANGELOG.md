# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.5] - 2025-01-12

### Fixed 🐛
- **Korean encoding fixes**
  - Force UTF-8 stdio and JSON-RPC output (`ensure_ascii=False`) for Windows clients
  - Added robust charset decoding for webpages and SearXNG JSON (handles EUC-KR/CP949)
  - Added `charset-normalizer` dependency

## [2.1.4] - 2025-01-12

### Fixed 🐛
- **Silenced trafilatura internal logging** - Suppressed noisy ERROR/WARNING logs from trafilatura.core
  - Logs like "empty HTML tree: None" and "discarding data: None" are now hidden
  - Only our own meaningful warnings are shown

## [2.1.3] - 2025-01-12

### Fixed 🐛
- **Improved HTML extraction robustness**
  - Added validation for empty HTML responses
  - Better error handling when trafilatura fails
  - Graceful fallback when content extraction yields nothing
  - Clear error messages for JavaScript-rendered or paywalled pages

## [2.1.2] - 2025-01-12

### Fixed 🐛
- **Auto-install on first run** - `stdio.js` now automatically checks and installs Python dependencies before starting
- Fixed Windows Python detection (prefers `python` over `python3`)
- Improved user experience: zero manual setup required for npx users

## [2.1.1] - 2025-01-12

### Fixed 🐛
- **Auto-install Python dependencies** - Added `postinstall` script to automatically run `pip install -r requirements.txt`
- Fixed `deep_research` plugin not loading due to missing `scikit-learn` dependency when installed via npx

## [2.1.0] - 2025-01-11

### Added 🎉

#### Deep Research Plugin
- **100% Privacy-Focused Deep Research** tool with intelligent search and recursive crawling
  - No external API calls (Gemini, Claude, OpenAI, etc.)
  - All quality assessment happens locally
  - Search queries never leave your machine

#### Local Quality Assessment
- Multi-layered heuristic quality scoring (0.0-1.0)
  - TF-IDF keyword relevance (25%)
  - Content quality indicators (25%)
  - Structural completeness (20%)
  - Credibility signals (15%)
  - Query intent matching (15%)
- Quality labels: Excellent, Good, Fair, Poor, Very Poor

#### Intelligent Query Refinement
- Rule-based query improvement
  - Temporal context (adds current year)
  - Intent clarification (how-to, what-is, etc.)
  - Synonym expansion
  - Negative keyword filtering
  - Specificity enhancement

#### Recursive Web Crawling
- `crawl_with_depth()` method in EnhancedWebCrawler
  - BFS link traversal
  - Configurable depth (0-5)
  - Same-domain filtering
  - Rate limiting integration
  - Automatic link extraction and validation

#### Hybrid Research Strategy
- Adaptive quality control loop:
  1. Initial search (SearXNG)
  2. Local quality assessment
  3. Query refinement if quality < threshold
  4. Recursive crawling on high-quality URLs
  5. Result deduplication and sorting

### Technical Details

#### New Files
```
shared/
├── __init__.py
├── local_quality_assessor.py   # 12.6 KB
└── local_query_refiner.py      # 11.9 KB

plugins/
└── deep_research_plugin.py     # 11.8 KB

test_deep_research.py           # Test suite
DEEP_RESEARCH_README.md         # Documentation
```

#### Dependencies
- Added `scikit-learn>=1.3.0` for TF-IDF vectorization

#### Performance
- Quick search (10 pages): ~5s
- Default settings (25 pages): ~25-30s
- Deep research (50 pages): ~60-90s

### Parameters

```json
{
  "query": "string (required)",
  "search_depth": "integer (1-5, default 2)",
  "crawl_depth": "integer (0-5, default 2)", 
  "max_pages": "integer (5-100, default 25)",
  "quality_threshold": "float (0.0-1.0, default 0.6)",
  "category": "string (default 'general')",
  "language": "string (default 'auto')"
}
```

### Example Usage

```json
{
  "tool": "deep_research",
  "query": "Next.js 15 server actions best practices",
  "search_depth": 2,
  "crawl_depth": 2,
  "max_pages": 25,
  "quality_threshold": 0.6
}
```

### Response Structure

```json
{
  "success": true,
  "query": "...",
  "final_query": "...",
  "search_iterations": 2,
  "crawl_depth_used": 2,
  "total_results": 23,
  "average_quality": 0.68,
  "threshold_met": true,
  "summary": {
    "excellent": 5,
    "good": 10,
    "fair": 6,
    "poor": 2
  },
  "results": [...]
}
```

### Testing
- ✅ All component tests passing
- ✅ Quality assessment validated
- ✅ Query refinement verified
- ✅ Recursive crawling tested
- ✅ Integration tests complete

### Documentation
- Added `DEEP_RESEARCH_README.md` with comprehensive guide
- Added `test_deep_research.py` with examples
- Updated keywords in package.json

---

## [2.0.4] - 2024-XX-XX

### Previous Features
- Enhanced web search with category support
- PDF reading with Markdown conversion
- Caching with TTL and validation
- Rate limiting
- Reddit URL conversion
- Trafilatura content extraction

---

## Migration Guide

### Upgrading from 2.0.x to 2.1.0

1. **Install scikit-learn**:
   ```bash
   pip install scikit-learn>=1.3.0
   ```

2. **Restart MCP server**:
   The new `deep_research` tool will be automatically loaded.

3. **Use the new tool**:
   ```json
   {
     "tool": "deep_research",
     "query": "your research question"
   }
   ```

### Breaking Changes
- None. All existing tools (`search_web`, `get_website`) remain unchanged.

### New Tool Only
- `deep_research` is an additional tool, not a replacement.

---

## Privacy Commitment 🔒

Version 2.1.0 introduces 100% local processing:
- ❌ No external LLM API calls
- ❌ No data collection
- ❌ No telemetry
- ✅ All quality assessment local
- ✅ All query refinement local
- ✅ Search queries never leave your machine

---

## Links

- [GitHub Repository](https://github.com/damin25soka7/hi/tree/main/searxng-mcp-crawl)
- [NPM Package](https://www.npmjs.com/package/@otbossam/searxng-mcp-server)
- [Documentation](./DEEP_RESEARCH_README.md)
- [Test Suite](./test_deep_research.py)
