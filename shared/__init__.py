"""
Shared utilities for deep research functionality.
All modules are 100% local - no external API calls.
"""

from .local_quality_assessor import LocalQualityAssessor
from .local_query_refiner import LocalQueryRefiner

__all__ = ["LocalQualityAssessor", "LocalQueryRefiner"]
