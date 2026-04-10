"""
Local Quality Assessor - 100% Privacy-Focused
No external API calls. All processing happens locally.

Evaluates search result quality using:
- TF-IDF keyword relevance
- Content quality indicators
- Structural completeness
- Credibility signals
- Query intent matching
"""

import re
import logging
from typing import Dict, List, Optional
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class LocalQualityAssessor:
    """
    100% Local quality assessment - no external APIs.
    Evaluates content quality using multi-layered heuristics.
    """

    def __init__(self):
        """Initialize the local quality assessor."""
        self.vectorizer = TfidfVectorizer(
            stop_words="english", max_features=1000, ngram_range=(1, 2)
        )
        logger.info("🔒 LocalQualityAssessor initialized (100% local, no API)")

    def assess_quality(
        self,
        content: str,
        query: str,
        url: Optional[str] = None,
        title: Optional[str] = None,
    ) -> float:
        """
        Assess content quality on a scale of 0.0 to 1.0.

        Args:
            content: The content to evaluate
            query: The search query
            url: Optional URL for credibility checks
            title: Optional title for relevance checks

        Returns:
            Quality score (0.0 = poor, 1.0 = excellent)
        """
        if not content or not query:
            return 0.0

        try:
            scores = []

            # 1. TF-IDF keyword relevance (25%)
            tfidf_score = self._tfidf_relevance(content, query)
            scores.append(tfidf_score * 0.25)

            # 2. Content quality indicators (25%)
            quality_score = self._content_quality(content)
            scores.append(quality_score * 0.25)

            # 3. Structural completeness (20%)
            structure_score = self._structural_completeness(content)
            scores.append(structure_score * 0.20)

            # 4. Credibility signals (15%)
            credibility_score = self._credibility_signals(content, url)
            scores.append(credibility_score * 0.15)

            # 5. Query intent matching (15%)
            intent_score = self._intent_matching(content, query)
            scores.append(intent_score * 0.15)

            total_score = sum(scores)

            logger.debug(
                f"Quality assessment: {total_score:.3f} "
                f"(tfidf={tfidf_score:.2f}, quality={quality_score:.2f}, "
                f"structure={structure_score:.2f}, cred={credibility_score:.2f}, "
                f"intent={intent_score:.2f})"
            )

            return round(total_score, 3)

        except Exception as e:
            logger.error(f"Quality assessment error: {str(e)}")
            return 0.0

    def assess_multiple(self, results: List[Dict], query: str) -> List[Dict]:
        """
        Assess quality for multiple search results.

        Args:
            results: List of result dicts with 'content', 'url', 'title'
            query: The search query

        Returns:
            Results list with added 'quality_score' field
        """
        for result in results:
            content = result.get("content", "")
            url = result.get("url")
            title = result.get("title")

            score = self.assess_quality(content, query, url, title)
            result["quality_score"] = score

        # Sort by quality score (descending)
        results.sort(key=lambda x: x.get("quality_score", 0), reverse=True)

        return results

    def get_average_quality(self, results: List[Dict]) -> float:
        """
        Calculate average quality score across multiple results.

        Args:
            results: List of result dicts with 'quality_score'

        Returns:
            Average quality score (0.0-1.0)
        """
        if not results:
            return 0.0

        scores = [r.get("quality_score", 0) for r in results if r.get("quality_score")]

        if not scores:
            return 0.0

        return round(sum(scores) / len(scores), 3)

    def _tfidf_relevance(self, content: str, query: str) -> float:
        """
        Calculate TF-IDF based keyword relevance.

        Args:
            content: Content text
            query: Search query

        Returns:
            Relevance score (0.0-1.0)
        """
        try:
            # Ensure we have enough text
            if len(content) < 10 or len(query) < 2:
                return 0.0

            # Create TF-IDF vectors
            texts = [query, content[:5000]]  # Limit content for performance
            tfidf_matrix = self.vectorizer.fit_transform(texts)

            # Calculate cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

            return float(similarity)

        except Exception as e:
            logger.debug(f"TF-IDF relevance error: {str(e)}")
            # Fallback to simple keyword matching
            return self._simple_keyword_match(content, query)

    def _simple_keyword_match(self, content: str, query: str) -> float:
        """Fallback: simple keyword matching."""
        content_lower = content.lower()
        query_words = query.lower().split()

        if not query_words:
            return 0.0

        matches = sum(1 for word in query_words if word in content_lower)
        return matches / len(query_words)

    def _content_quality(self, content: str) -> float:
        """
        Evaluate content quality indicators.

        Checks:
        - Length (not too short or too long)
        - Sentence structure
        - Code/technical content
        - Lists/organization

        Returns:
            Quality score (0.0-1.0)
        """
        score = 0.0

        # Length check (500-10000 chars is optimal)
        length = len(content)
        if 500 < length < 10000:
            score += 0.3
        elif 300 < length <= 500:
            score += 0.2
        elif length >= 10000:
            score += 0.15
        elif length < 100:
            return 0.0  # Too short to be useful

        # Sentence structure (complete sentences)
        sentences = content.count(".") + content.count("!") + content.count("?")
        if sentences > 5:
            score += 0.3
        elif sentences > 2:
            score += 0.15

        # Code/technical content detection
        code_markers = [
            "```",
            "<code>",
            "function ",
            "class ",
            "def ",
            "const ",
            "let ",
            "var ",
        ]
        if any(marker in content for marker in code_markers):
            score += 0.2

        # Lists/structure (organized information)
        list_count = content.count("\n-") + content.count("\n*") + content.count("<li>")
        if list_count > 5:
            score += 0.2
        elif list_count > 2:
            score += 0.1

        return min(score, 1.0)

    def _structural_completeness(self, content: str) -> float:
        """
        Evaluate structural completeness.

        Checks:
        - Heading hierarchy
        - Paragraph separation
        - Links/references

        Returns:
            Structure score (0.0-1.0)
        """
        score = 0.0

        # Heading hierarchy (H1-H6 or markdown #)
        headings = (
            content.count("<h1")
            + content.count("<h2")
            + content.count("<h3")
            + content.count("\n# ")
            + content.count("\n## ")
            + content.count("\n### ")
        )
        score += min(headings / 5, 0.4)

        # Paragraph separation
        paragraphs = content.count("\n\n")
        score += min(paragraphs / 10, 0.3)

        # Links/references (shows sourcing)
        links = (
            content.count("http://") + content.count("https://") + content.count("[")
        )
        score += min(links / 5, 0.3)

        return min(score, 1.0)

    def _credibility_signals(self, content: str, url: Optional[str] = None) -> float:
        """
        Detect credibility signals.

        Positive signals:
        - Documentation keywords
        - Recent dates
        - Official sources

        Negative signals:
        - Spam keywords
        - Errors
        - Clickbait

        Returns:
            Credibility score (0.0-1.0)
        """
        score = 0.5  # Start neutral
        content_lower = content.lower()

        # Positive signals
        positive_keywords = [
            "documentation",
            "official",
            "tutorial",
            "guide",
            "reference",
            "published",
            "updated",
            "latest",
            "current",
            "stable",
            "2024",
            "2025",  # Recent dates
        ]

        for keyword in positive_keywords:
            if keyword in content_lower:
                score += 0.05

        # Domain credibility (if URL provided)
        if url:
            url_lower = url.lower()
            trusted_domains = [
                "github.com",
                "stackoverflow.com",
                "developer.mozilla.org",
                "docs.python.org",
                "reactjs.org",
                ".edu",
                ".gov",
                "wikipedia.org",
                "medium.com",
            ]

            if any(domain in url_lower for domain in trusted_domains):
                score += 0.15

        # Negative signals
        negative_keywords = [
            "advertisement",
            "click here",
            "buy now",
            "subscribe now",
            "limited offer",
            "act now",
            "404",
            "not found",
            "error occurred",
            "page not found",
            "access denied",
        ]

        for keyword in negative_keywords:
            if keyword in content_lower:
                score -= 0.15

        return max(0.0, min(score, 1.0))

    def _intent_matching(self, content: str, query: str) -> float:
        """
        Match content against query intent.

        Intent patterns:
        - how to -> steps/instructions
        - what is -> definitions/explanations
        - why -> reasons/causes
        - compare -> comparisons/differences
        - best -> recommendations/rankings
        - error/fix -> solutions/troubleshooting

        Returns:
            Intent match score (0.0-1.0)
        """
        content_lower = content.lower()
        query_lower = query.lower()

        # Define intent patterns
        intent_patterns = {
            "how to": [
                "step",
                "guide",
                "tutorial",
                "instruction",
                "procedure",
                "method",
            ],
            "what is": [
                "definition",
                "overview",
                "introduction",
                "explanation",
                "meaning",
            ],
            "what are": [
                "definition",
                "overview",
                "introduction",
                "explanation",
                "types",
            ],
            "why": ["reason", "because", "due to", "caused by", "purpose"],
            "compare": ["vs", "versus", "compared", "difference", "comparison"],
            "best": ["recommended", "top", "best practice", "optimal", "ideal"],
            "error": ["fix", "solution", "resolve", "troubleshoot", "debug"],
            "install": ["installation", "setup", "download", "install", "configure"],
        }

        # Check which intent matches the query
        for intent_keyword, content_keywords in intent_patterns.items():
            if intent_keyword in query_lower:
                # Count how many expected keywords are in content
                matches = sum(1 for kw in content_keywords if kw in content_lower)
                return matches / len(content_keywords)

        # No specific intent detected - use general relevance
        return 0.5

    def get_quality_label(self, score: float) -> str:
        """
        Convert numeric quality score to human-readable label.

        Args:
            score: Quality score (0.0-1.0)

        Returns:
            Label string
        """
        if score >= 0.8:
            return "Excellent"
        elif score >= 0.7:
            return "Good"
        elif score >= 0.6:
            return "Fair"
        elif score >= 0.4:
            return "Poor"
        else:
            return "Very Poor"
