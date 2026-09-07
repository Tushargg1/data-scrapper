"""
Configuration for the scraper platform.
Edit API_KEY to your own secret key before sharing with other apps/developers.
"""

# ── API Security ─────────────────────────────────────────────────────────────
# Master admin key — can create/delete profiles and access all data
ADMIN_API_KEY = "admin-secret-key-change-me-2024"

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
