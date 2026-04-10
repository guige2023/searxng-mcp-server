"""
Local Query Refiner - 100% Privacy-Focused
No external API calls. All processing happens locally.

Refines search queries using:
- Rule-based query expansion
- Synonym mapping
- Negative keyword filtering
- Intent clarification
- Temporal enhancement (add current year)
"""

import re
import logging
from typing import List, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class LocalQueryRefiner:
    """
    100% Local query refinement - no external APIs.
    Generates improved search queries using rule-based heuristics.
    """

    def __init__(self):
        """Initialize the local query refiner."""
        # Technical term synonyms (manually curated)
        self.tech_synonyms = {
            "javascript": ["js", "ecmascript", "node.js", "nodejs"],
            "python": ["py", "python3"],
            "error": ["exception", "bug", "issue", "problem"],
            "function": ["method", "procedure", "subroutine"],
            "variable": ["var", "let", "const"],
            "database": ["db", "datastore", "data store"],
            "framework": ["library", "toolkit"],
            "install": ["installation", "setup", "configure"],
            "tutorial": ["guide", "walkthrough", "how-to"],
            "documentation": ["docs", "reference", "manual"],
        }

        # Common noise words to filter
        self.noise_keywords = {
            "advertisement",
            "ads",
            "sponsored",
            "promotion",
            "click here",
            "sign up",
            "subscribe",
            "newsletter",
        }

        logger.info("🔒 LocalQueryRefiner initialized (100% local, no API)")

    def refine_query(
        self,
        original_query: str,
        failed_results: Optional[List[str]] = None,
        iteration: int = 1,
    ) -> str:
        """
        Refine a search query to improve results.

        Args:
            original_query: The original search query
            failed_results: Optional list of low-quality result snippets
            iteration: Current iteration number (for progressive refinement)

        Returns:
            Refined search query
        """
        if not original_query:
            return original_query

        refined = original_query

        # Apply refinement strategies based on iteration
        if iteration == 1:
            # First refinement: basic enhancements
            refined = self._add_temporal_context(refined)
            refined = self._clarify_intent(refined)
        elif iteration == 2:
            # Second refinement: add specificity
            refined = self._add_specificity(refined)
            refined = self._add_synonyms(refined)
        else:
            # Third+ refinement: aggressive filtering
            refined = self._add_negative_keywords(refined, failed_results)
            refined = self._expand_technical_terms(refined)

        # Clean up the refined query
        refined = self._cleanup_query(refined)

        logger.info(
            f"🔄 Query refined (iter {iteration}): '{original_query}' -> '{refined}'"
        )

        return refined

    def generate_alternative_queries(
        self, original_query: str, num_alternatives: int = 3
    ) -> List[str]:
        """
        Generate multiple alternative query formulations.

        Args:
            original_query: The original search query
            num_alternatives: Number of alternatives to generate

        Returns:
            List of alternative queries
        """
        alternatives = []

        # Alternative 1: Add specificity
        alt1 = self._add_specificity(original_query)
        if alt1 != original_query:
            alternatives.append(alt1)

        # Alternative 2: Rephrase with synonyms
        alt2 = self._add_synonyms(original_query)
        if alt2 != original_query:
            alternatives.append(alt2)

        # Alternative 3: Clarify intent
        alt3 = self._clarify_intent(original_query)
        if alt3 != original_query:
            alternatives.append(alt3)

        # Alternative 4: Expand technical terms
        alt4 = self._expand_technical_terms(original_query)
        if alt4 != original_query:
            alternatives.append(alt4)

        return alternatives[:num_alternatives]

    def _add_temporal_context(self, query: str) -> str:
        """
        Add temporal context (current year) if not present.

        Args:
            query: Original query

        Returns:
            Query with temporal context
        """
        current_year = str(datetime.now().year)
        query_lower = query.lower()

        # Check if year is already mentioned
        if re.search(r"\b20\d{2}\b", query):
            return query

        # Check if query is about recent/current topics
        recent_indicators = ["latest", "current", "new", "recent", "today", "now"]
        if any(indicator in query_lower for indicator in recent_indicators):
            return f"{query} {current_year}"

        # For technology queries, add year
        tech_indicators = [
            "python",
            "javascript",
            "react",
            "node",
            "framework",
            "library",
            "api",
        ]
        if any(indicator in query_lower for indicator in tech_indicators):
            return f"{query} {current_year}"

        return query

    def _clarify_intent(self, query: str) -> str:
        """
        Clarify query intent if ambiguous.

        Args:
            query: Original query

        Returns:
            Query with clarified intent
        """
        query_lower = query.lower()

        # Already has clear intent
        intent_words = ["how", "what", "why", "when", "where", "who"]
        if any(word in query_lower for word in intent_words):
            return query

        # Detect implicit intent patterns

        # Pattern: "react hooks" -> "how to use react hooks"
        if re.match(r"^[a-z]+ [a-z]+$", query_lower):
            return f"how to use {query}"

        # Pattern: "error: ..." -> "how to fix error: ..."
        if query_lower.startswith("error"):
            return f"how to fix {query}"

        # Pattern: "X vs Y" -> keep as is (comparison intent clear)
        if " vs " in query_lower or " versus " in query_lower:
            return query

        # Pattern: single word -> "what is X"
        if len(query.split()) == 1:
            return f"what is {query}"

        return query

    def _add_specificity(self, query: str) -> str:
        """
        Add specificity to vague queries.

        Args:
            query: Original query

        Returns:
            More specific query
        """
        query_lower = query.lower()

        # Add "tutorial" for how-to queries without it
        if "how to" in query_lower and "tutorial" not in query_lower:
            return f"{query} tutorial"

        # Add "documentation" for what-is queries
        if "what is" in query_lower and "documentation" not in query_lower:
            return f"{query} documentation"

        # Add "best practices" for general technology queries
        tech_terms = ["python", "javascript", "react", "node", "api", "database"]
        if any(term in query_lower for term in tech_terms):
            if "best" not in query_lower and "practice" not in query_lower:
                return f"{query} best practices"

        return query

    def _add_synonyms(self, query: str) -> str:
        """
        Add synonyms for technical terms.

        Args:
            query: Original query

        Returns:
            Query with synonyms
        """
        query_lower = query.lower()

        # Find matching technical terms
        for term, synonyms in self.tech_synonyms.items():
            if term in query_lower:
                # Add first synonym
                synonym = synonyms[0]
                if synonym not in query_lower:
                    return f"{query} OR {synonym}"

        return query

    def _add_negative_keywords(
        self, query: str, failed_results: Optional[List[str]] = None
    ) -> str:
        """
        Add negative keywords to filter out noise.

        Args:
            query: Original query
            failed_results: Optional list of low-quality snippets

        Returns:
            Query with negative keywords
        """
        # Detect noise from failed results
        noise_words = self._detect_noise_from_results(failed_results)

        if not noise_words:
            # Use default noise keywords
            noise_words = ["advertisement", "sponsored"]

        # Add negative keywords (Google-style)
        negative_terms = " ".join(f"-{word}" for word in noise_words[:3])

        return f"{query} {negative_terms}"

    def _detect_noise_from_results(
        self, failed_results: Optional[List[str]]
    ) -> List[str]:
        """
        Detect common noise words from failed results.

        Args:
            failed_results: List of low-quality result snippets

        Returns:
            List of noise words to exclude
        """
        if not failed_results:
            return []

        noise_words = set()

        for result in failed_results:
            result_lower = result.lower()

            # Check for noise keywords
            for keyword in self.noise_keywords:
                if keyword in result_lower:
                    noise_words.add(keyword.split()[0])  # First word only

        return list(noise_words)[:5]  # Max 5 noise words

    def _expand_technical_terms(self, query: str) -> str:
        """
        Expand technical abbreviations.

        Args:
            query: Original query

        Returns:
            Query with expanded terms
        """
        query_lower = query.lower()

        # Expand common abbreviations
        expansions = {
            r"\bjs\b": "javascript",
            r"\bpy\b": "python",
            r"\bdb\b": "database",
            r"\bapi\b": "API application programming interface",
            r"\bcli\b": "command line interface",
            r"\bui\b": "user interface",
        }

        for abbrev, expansion in expansions.items():
            if re.search(abbrev, query_lower):
                query = re.sub(abbrev, expansion, query, flags=re.IGNORECASE)
                break  # Only expand one term per refinement

        return query

    def _cleanup_query(self, query: str) -> str:
        """
        Clean up refined query (remove duplicates, extra spaces, etc.).

        Args:
            query: Query to clean

        Returns:
            Cleaned query
        """
        # Remove duplicate words
        words = query.split()
        seen = set()
        unique_words = []

        for word in words:
            word_lower = word.lower()
            if word_lower not in seen or word.startswith("-") or word == "OR":
                unique_words.append(word)
                seen.add(word_lower)

        # Join and clean up spaces
        cleaned = " ".join(unique_words)
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = cleaned.strip()

        return cleaned

    def should_refine(
        self, query: str, average_quality: float, threshold: float = 0.6
    ) -> bool:
        """
        Determine if query should be refined based on result quality.

        Args:
            query: Current query
            average_quality: Average quality score of results
            threshold: Quality threshold

        Returns:
            True if query should be refined
        """
        if average_quality >= threshold:
            logger.info(
                f"✅ Quality sufficient ({average_quality:.2f} >= {threshold}), no refinement needed"
            )
            return False

        logger.info(
            f"⚠️ Quality insufficient ({average_quality:.2f} < {threshold}), refinement recommended"
        )
        return True
