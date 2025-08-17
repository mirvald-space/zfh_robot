"""
Freelancehunt Telegram Bot - Головна точка входу

ВАЖЛИВО: Перед зміною API запитів вивчіть документацію:
https://apidocs.freelancehunt.com/#0eed992e-18f1-4dc4-892d-22b9d896935b

Усі параметри фільтрації, структура відповідей та ендпоінти описані в офіційній документації.

Rate Limiting:
API обмежує кількість запитів. При перевищенні повертається HTTP 429.
Заголовки відповіді:
- X-Ratelimit-Limit: середня кількість запитів за період
- X-Ratelimit-Remaining: залишкова кількість запитів
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramAPIError

import config
from src.handlers.commands import router
from src.services.project_service import ProjectService
from src.utils.db_manager import db_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Check required environment variables
required_env_vars = {
    'TELEGRAM_BOT_TOKEN': config.TELEGRAM_BOT_TOKEN,
    'FREELANCEHUNT_TOKEN': config.FREELANCEHUNT_TOKEN,
}

for var_name, var_value in required_env_vars.items():
    if not var_value:
        logger.error(f"Missing required environment variable: {var_name}")
        raise ValueError(f"Missing required environment variable: {var_name}")

# Initialize bot and dispatcher
bot = Bot(token=config.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.include_router(router)

# Initialize project service
project_service_instance = ProjectService(bot)

# Make project service available to handlers
import src.services.project_service
src.services.project_service.project_service = project_service_instance

# Log startup settings
logger.info("Starting Freelancehunt Bot")
logger.info(f"MongoDB: {config.MONGO_DB_NAME} on {config.MONGO_URI}")


async def check_telegram_token():
    """Перевіряє валідність токена бота"""
    try:
        bot_info = await bot.me()
        logger.info(f"Bot authorized as @{bot_info.username} (ID: {bot_info.id})")
        return True
    except TelegramAPIError as e:
        logger.error(f"Failed to authorize bot: {e}")
        return False


async def check_freelancehunt_api():
    """Перевіряє доступність Freelancehunt API"""
    try:
        # Import here to avoid circular imports
        from src.api.freelancehunt import FreelancehuntAPI
        api = FreelancehuntAPI()
        # Try to make a simple API call to check connectivity
        await api.get_projects()
        logger.info("Successfully connected to Freelancehunt API")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Freelancehunt API: {e}")
        return False


async def check_mongodb_connection():
    """Перевіряє доступність MongoDB"""
    try:
        # Connect to database
        await db_manager.connect()
        
        # Test connection with a simple command
        if db_manager.db is not None:
            await db_manager.db.command("ping")
            
        logger.info("Successfully connected to MongoDB")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return False


async def startup():
    """Дії при запуску бота"""
    try:
        # Check Telegram token
        if not await check_telegram_token():
            raise ValueError("Invalid Telegram token")
        
        # Remove webhook if exists (required for polling)
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook deleted successfully")
        except Exception as e:
            logger.warning(f"Failed to delete webhook: {e}")
        
        # Check MongoDB connection
        if not await check_mongodb_connection():
            raise ValueError("Failed to connect to MongoDB")
        
        # Check Freelancehunt API connection
        if not await check_freelancehunt_api():
            raise ValueError("Failed to connect to Freelancehunt API")
        
        # Load data from database
        from src.utils.user_manager import user_manager
        await user_manager.load_data_from_db()
        
        # Start project monitoring
        logger.info("Project monitoring service initialized")
        # Start monitoring in background
        asyncio.create_task(project_service_instance.start_monitoring())
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise


async def shutdown():
    """Дії при зупинці бота"""
    try:
        # Stop project monitoring
        project_service_instance.stop_monitoring()
        logger.info("Project monitoring stopped")
        
        # Close MongoDB connection
        await db_manager.close()
        logger.info("MongoDB connection closed")
        
        # Close bot session
        await bot.session.close()
        logger.info("Bot session closed")
        
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


async def main():
    """Запуск бота через polling."""
    try:
        logger.info("Starting Freelancehunt Telegram Bot")
        
        # Startup initialization
        await startup()
        
        logger.info("Bot started in polling mode")
        
        # Start polling
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Error during bot startup: {e}")
        raise
    finally:
        await shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise