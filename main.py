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
import os
import time
from aiohttp import web
from aiohttp.web_request import Request

from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
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

# Application start time
START_TIME = time.time()

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
logger.info("Starting Freelancehunt Bot with settings:")
logger.info(f"WEBHOOK_URL: {config.WEBHOOK_URL}")
logger.info(f"WEBAPP_PORT: {config.WEBAPP_PORT}")
logger.info(f"Environment: {'Development' if config.DEV_MODE else 'Production'}")
logger.info(f"DEV_MODE: {config.DEV_MODE}")
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


async def on_startup(bot: Bot) -> None:
    """Дії при запуску бота"""
    try:
        # Check Telegram token
        if not await check_telegram_token():
            raise ValueError("Invalid Telegram token")
        
        # Check MongoDB connection
        if not await check_mongodb_connection():
            raise ValueError("Failed to connect to MongoDB")
        
        # Check Freelancehunt API connection
        if not await check_freelancehunt_api():
            raise ValueError("Failed to connect to Freelancehunt API")
        
        # Load data from database
        from src.utils.user_manager import user_manager
        await user_manager.load_data_from_db()
        
        # Set webhook only in production mode
        if not config.DEV_MODE:
            await bot.set_webhook(config.WEBHOOK_URL)
            logger.info(f"Webhook set to URL: {config.WEBHOOK_URL}")
        else:
            logger.info("DEV MODE: Webhook not set")
        
        # Start project monitoring
        logger.info("Project monitoring service initialized")
        # Start monitoring in background
        asyncio.create_task(project_service_instance.start_monitoring())
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise


async def on_shutdown(bot: Bot) -> None:
    """Дії при зупинці бота"""
    try:
        # Remove webhook only if it was set
        if not config.DEV_MODE:
            await bot.delete_webhook()
            logger.info("Webhook removed")
        
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


async def get_bot_status():
    """Перевіряє статус бота через Telegram API"""
    try:
        me = await bot.me()
        return {
            "ok": True,
            "username": me.username,
            "bot_id": me.id
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


async def get_freelancehunt_status():
    """Перевіряє підключення до Freelancehunt API"""
    try:
        from src.api.freelancehunt import FreelancehuntAPI
        api = FreelancehuntAPI()
        # Simple API call to check connectivity
        await api.get_projects()
        return {
            "ok": True,
            "connected": True
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


async def get_mongodb_status():
    """Перевіряє статус MongoDB"""
    try:
        if db_manager.db is None:
            await db_manager.connect()
            
        # Simple query to check connection
        await db_manager.db.command("ping")
        
        # Get collection statistics
        users_count = await db_manager.db.users.count_documents({})
        active_users_count = await db_manager.db.users.count_documents({"active": True})
        users_with_username = await db_manager.db.users.count_documents({"username": {"$ne": None}})
        projects_count = await db_manager.db.sent_projects.count_documents({})
        
        # Get new users in last 24 hours
        import datetime
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        new_users_count = await db_manager.db.users.count_documents({
            "created_at": {"$gte": yesterday}
        })
        
        # Get additional info
        stats = {
            "connected": True,
            "database": config.MONGO_DB_NAME,
            "collections": {
                "users": {
                    "total": users_count,
                    "active": active_users_count,
                    "with_username": users_with_username,
                    "new_24h": new_users_count
                },
                "sent_projects": projects_count
            }
        }
        
        return {
            "ok": True,
            **stats
        }
    except Exception as e:
        logger.error(f"MongoDB status check failed: {e}")
        return {
            "ok": False,
            "connected": False,
            "error": str(e)
        }


async def health_check(request: Request) -> web.Response:
    """Розширений health check з інформацією про стан сервісів"""
    try:
        # Collect status of all services
        freelancehunt_status = await get_freelancehunt_status()
        bot_status = await get_bot_status()
        mongodb_status = await get_mongodb_status()
        
        # Calculate uptime
        uptime = int(time.time() - START_TIME)
        
        health_data = {
            "status": "ok" if freelancehunt_status["ok"] and bot_status["ok"] and mongodb_status["ok"] else "error",
            "timestamp": time.time(),
            "uptime_seconds": uptime,
            "environment": "development" if config.DEV_MODE else "production",
            "services": {
                "freelancehunt_api": freelancehunt_status,
                "telegram_bot": bot_status,
                "mongodb": mongodb_status,
                "project_monitoring": {
                    "ok": True,
                    "active": project_service_instance is not None
                }
            },
            "version": "1.0.0"
        }
        
        # Return 200 if all services are working, otherwise 500
        status = 200 if health_data["status"] == "ok" else 500
        return web.json_response(health_data, status=status)
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return web.json_response({
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }, status=500)


def create_app() -> web.Application:
    """Створення веб-додатку з webhook handler."""
    # Create aiohttp application
    app = web.Application()
    
    # Create webhook request handler
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    
    # Register webhook handler
    webhook_requests_handler.register(app, path=config.WEBHOOK_PATH)
    
    # Setup startup and shutdown hooks
    app.on_startup.append(lambda app: on_startup(bot))
    app.on_shutdown.append(lambda app: on_shutdown(bot))
    
    # Add monitoring endpoints
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    app.router.add_get('/ping', lambda r: web.Response(text='pong'))
    
    # Setup application
    setup_application(app, dp, bot=bot)
    
    return app


async def main():
    """Запуск бота з webhook."""
    try:
        logger.info("Starting Freelancehunt Telegram Bot")
        
        # Create web application
        app = create_app()
        
        # Create and start web server
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(
            runner,
            host=config.WEBAPP_HOST,
            port=config.WEBAPP_PORT
        )
        await site.start()
        
        logger.info(f"Bot started on {config.WEBAPP_HOST}:{config.WEBAPP_PORT}")
        if not config.DEV_MODE:
            logger.info(f"Webhook URL: {config.WEBHOOK_URL}")
        else:
            logger.info("DEV MODE: Running without webhook")
        
        # Keep the server running
        await asyncio.Event().wait()
        
    except Exception as e:
        logger.error(f"Error during bot startup: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise