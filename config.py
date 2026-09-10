"""
Configuration for the scraper platform.
Edit API_KEY to your own secret key before sharing with other apps/developers.
"""

import os

# ── API Security ─────────────────────────────────────────────────────────────
# Master admin key — reads from Environment Variable ADMIN_API_KEY or uses default
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "admin-secret-key-change-me-2024")

# Data deletion verification password (required for any data wipe or profile deletion)
DATA_DELETE_PASSWORD = os.getenv("DATA_DELETE_PASSWORD", "Tushar@123delete")

# Legacy single key (kept for backward compat)
API_KEY = ADMIN_API_KEY

# ── Server Ports ─────────────────────────────────────────────────────────────
STREAMLIT_PORT = 8501
API_PORT = 8000

# ── Scraper Defaults ─────────────────────────────────────────────────────────
DEFAULT_MAX_SCROLLS = 3
REQUEST_DELAY_SECONDS = 1.8

# ── App Info ─────────────────────────────────────────────────────────────────
APP_NAME = "India Beauty Biz Scraper"
APP_VERSION = "2.0.0"
