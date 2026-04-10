"""
SearXNG MCP Server - Configuration Module

Loads configuration from environment variables.
Priority: Environment Variables > ~/.searxng-mcp/.env > Default Values

Note: The .env file at ~/.searxng-mcp/.env is loaded by env-loader.js (Node.js)
before the Python process starts. This module simply reads from os.environ.
"""

import os
from dotenv import load_dotenv

# Load .env file (fallback for direct Python execution)
# Note: When running via stdio.js, env-loader.js already loads the .env file
load_dotenv()

# ==========================================
# SearXNG Configuration
# ==========================================
SEARXNG_BASE_URL = os.getenv("SEARXNG_BASE_URL", "http://localhost:32768")

# ==========================================
# API Configuration
# ==========================================
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "32769"))

# ==========================================
# Crawler Configuration
# ==========================================
CONTENT_MAX_LENGTH = int(os.getenv("CONTENT_MAX_LENGTH", "10000"))
SEARCH_RESULT_LIMIT = int(os.getenv("SEARCH_RESULT_LIMIT", "10"))

# ==========================================
# User Agent Configuration
# ==========================================
# These are read directly from environment in enhanced_crawler.py
# Documented here for reference:
#
# USER_AGENT_ROTATION: true/false (default: true)
#   Enable/disable User-Agent rotation for bot detection bypass
#
# USER_AGENT_STRATEGY: random/domain-sticky (default: random)
#   - random: Different UA for every request
#   - domain-sticky: Same UA for same domain
#
# CUSTOM_USER_AGENTS: comma-separated list of custom UAs (optional)
#   Example: "Mozilla/5.0 ..., Mozilla/5.0 ..."

USER_AGENT_ROTATION = os.getenv("USER_AGENT_ROTATION", "true").lower() in (
    "true",
    "1",
    "yes",
)
USER_AGENT_STRATEGY = os.getenv("USER_AGENT_STRATEGY", "random")
CUSTOM_USER_AGENTS = os.getenv("CUSTOM_USER_AGENTS", "")

# ==========================================
# Search Settings (SearXNG request parameters)
# ==========================================
# Language: ko, en, ja, auto, etc.
SEARXNG_LANGUAGE = os.getenv("SEARXNG_LANGUAGE", "auto")

# Safe Search: 0=off, 1=moderate, 2=strict
SEARXNG_SAFE_SEARCH = int(os.getenv("SEARXNG_SAFE_SEARCH", "0"))

# Time Range: day, week, month, year (empty = all time)
SEARXNG_TIME_RANGE = os.getenv("SEARXNG_TIME_RANGE", "")

# Result limit per search
SEARXNG_RESULT_LIMIT = int(os.getenv("SEARXNG_RESULT_LIMIT", "10"))

# ==========================================
# Rate Limiting
# ==========================================
RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "300"))
RATE_LIMIT_TIMEOUT = int(os.getenv("RATE_LIMIT_TIMEOUT", "60"))

# ==========================================
# Legacy User Agent (for backward compatibility)
# ==========================================
# Note: This is deprecated. Use enhanced_crawler.get_user_agent() instead.
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
