# config.py
import os

# Telegram API details
API_ID = int(os.getenv("API_ID", 12345))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")

# RG Vikramjeet API configuration
API_KEY = os.getenv("API_KEY", "appxapi")
API_BASE = "https://rgvikramjeetapi.classx.co.in"

# Default headers
DEFAULT_HEADERS = {
    "Auth-Key": API_KEY,
    "User-Id": "-2",
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "okhttp/4.9.1"
}
