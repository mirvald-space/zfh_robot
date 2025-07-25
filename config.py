import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# ============================================================================
# REQUIRED ENVIRONMENT VARIABLES
# ============================================================================

# Telegram Bot token from BotFather
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Freelancehunt API token
FREELANCEHUNT_TOKEN = os.getenv("FREELANCEHUNT_TOKEN")

# ============================================================================
# MONGODB SETTINGS
# ============================================================================

# MongoDB connection URI
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

# MongoDB database name
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "zfh_robot")

# ============================================================================
# PROJECT MONITORING SETTINGS
# ============================================================================

# Default check interval in seconds (60 seconds = 1 minute)
DEFAULT_CHECK_INTERVAL = int(os.getenv("DEFAULT_CHECK_INTERVAL", "60"))

# Maximum check interval (1 hour)
MAX_CHECK_INTERVAL = int(os.getenv("MAX_CHECK_INTERVAL", "3600"))

# Minimum check interval (30 seconds)
MIN_CHECK_INTERVAL = int(os.getenv("MIN_CHECK_INTERVAL", "30"))

# ============================================================================
# API RATE LIMITING SETTINGS
# ============================================================================

# Minimum interval between API requests (seconds)
MIN_API_REQUEST_INTERVAL = float(os.getenv("MIN_API_REQUEST_INTERVAL", "1.0"))

# Conservative rate limit threshold (when to start being more careful)
RATE_LIMIT_WARNING_THRESHOLD = int(os.getenv("RATE_LIMIT_WARNING_THRESHOLD", "20"))

# Critical rate limit threshold (when to significantly slow down)
RATE_LIMIT_CRITICAL_THRESHOLD = int(os.getenv("RATE_LIMIT_CRITICAL_THRESHOLD", "10"))

# ============================================================================
# WEBHOOK SETTINGS
# ============================================================================

# Webhook host (for production use your domain, for dev use ngrok URL)
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "localhost")

# Webhook path
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")

# Build webhook URL - check if host already has protocol
if WEBHOOK_HOST.startswith(('http://', 'https://')):
    WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
else:
    WEBHOOK_URL = f"https://{WEBHOOK_HOST}{WEBHOOK_PATH}"

# ============================================================================
# WEB APPLICATION SETTINGS
# ============================================================================

# Web app host (0.0.0.0 for production, localhost for dev)
WEBAPP_HOST = os.getenv("WEBAPP_HOST", "0.0.0.0")

# Web app port
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", "3000"))

# ============================================================================
# ENVIRONMENT SETTINGS
# ============================================================================

# Development mode (skip webhook setup, use polling instead)
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

# Production mode detection
IS_PRODUCTION = not DEV_MODE and os.getenv("RENDER_EXTERNAL_URL") is not None

# Logging level
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# ============================================================================
# PRODUCTION OVERRIDES
# ============================================================================

# Override settings for production deployment (e.g., Render.com)
if os.getenv('RENDER_EXTERNAL_URL'):
    # Use Render's external URL for webhook
    WEBHOOK_HOST = os.getenv('RENDER_EXTERNAL_URL').rstrip('/')
    WEBAPP_PORT = 10000  # Render uses port 10000
    IS_PRODUCTION = True
    DEV_MODE = False
    WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
    
    logger.info("Production environment detected (Render)")
    logger.info(f"Using webhook URL: {WEBHOOK_URL}")

# ============================================================================
# VALIDATION
# ============================================================================

def validate_config():
    """Validates configuration settings"""
    errors = []
    
    # Check required environment variables
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is required")
    
    if not FREELANCEHUNT_TOKEN:
        errors.append("FREELANCEHUNT_TOKEN is required")
    
    # Validate intervals
    if MIN_CHECK_INTERVAL >= MAX_CHECK_INTERVAL:
        errors.append("MIN_CHECK_INTERVAL must be less than MAX_CHECK_INTERVAL")
    
    if DEFAULT_CHECK_INTERVAL < MIN_CHECK_INTERVAL or DEFAULT_CHECK_INTERVAL > MAX_CHECK_INTERVAL:
        errors.append("DEFAULT_CHECK_INTERVAL must be between MIN_CHECK_INTERVAL and MAX_CHECK_INTERVAL")
    
    # Validate rate limiting
    if RATE_LIMIT_CRITICAL_THRESHOLD >= RATE_LIMIT_WARNING_THRESHOLD:
        errors.append("RATE_LIMIT_CRITICAL_THRESHOLD must be less than RATE_LIMIT_WARNING_THRESHOLD")
    
    if errors:
        raise ValueError("Configuration errors:\n" + "\n".join(f"- {error}" for error in errors))

# Validate configuration on import
validate_config() 