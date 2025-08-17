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
# ENVIRONMENT SETTINGS
# ============================================================================

# Logging level
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

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