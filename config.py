import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Bot token from BotFather
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Freelancehunt API token
FREELANCEHUNT_TOKEN = os.getenv("FREELANCEHUNT_TOKEN")

# Default check interval in seconds (60 seconds = 1 minute)
DEFAULT_CHECK_INTERVAL = 60

# Maximum check interval (1 hour)
MAX_CHECK_INTERVAL = 3600

# Minimum check interval (30 seconds)
MIN_CHECK_INTERVAL = 30

# Rate limiting settings
# Minimum interval between API requests (seconds)
MIN_API_REQUEST_INTERVAL = 1.0

# Conservative rate limit threshold (when to start being more careful)
RATE_LIMIT_WARNING_THRESHOLD = 20

# Critical rate limit threshold (when to significantly slow down)
RATE_LIMIT_CRITICAL_THRESHOLD = 10

# Webhook settings
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "localhost")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8080"))
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")

# Build webhook URL - check if host already has protocol
if WEBHOOK_HOST.startswith(('http://', 'https://')):
    WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
else:
    WEBHOOK_URL = f"https://{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Web app settings
WEBAPP_HOST = os.getenv("WEBAPP_HOST", "0.0.0.0")
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", "8080"))

# Development mode (skip webhook setup)
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true" 