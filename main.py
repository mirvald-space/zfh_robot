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
from aiohttp import web
from aiohttp.web_request import Request

from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

import config
from src.handlers.commands import router
from src.services.project_service import ProjectService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=config.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.include_router(router)

# Initialize project service
project_service_instance = ProjectService(bot)

# Make project service available to handlers
import src.services.project_service
src.services.project_service.project_service = project_service_instance


async def on_startup(bot: Bot) -> None:
    """Налаштування webhook при запуску."""
    await bot.set_webhook(f"{config.WEBHOOK_URL}")
    logger.info(f"Webhook встановлено: {config.WEBHOOK_URL}")


async def on_shutdown(bot: Bot) -> None:
    """Видалення webhook при зупинці."""
    await bot.delete_webhook()
    logger.info("Webhook видалено")
    # Stop project monitoring
    project_service_instance.stop_monitoring()


async def health_check(request: Request) -> web.Response:
    """Health check endpoint."""
    return web.json_response({"status": "ok", "service": "freelancehunt-bot"})


def create_app() -> web.Application:
    """Створення веб-додатку з webhook handler."""
    # Create aiohttp application
    app = web.Application()
    
    # Add health check endpoint
    app.router.add_get("/health", health_check)
    
    # Create webhook request handler
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    
    # Register webhook handler
    webhook_requests_handler.register(app, path=config.WEBHOOK_PATH)
    
    # Setup application
    setup_application(app, dp, bot=bot)
    
    return app


async def main():
    """Запуск бота з webhook."""
    if config.DEV_MODE:
        logger.info("Запуск Freelancehunt Telegram Bot (DEV MODE - без webhook)")
    else:
        logger.info("Запуск Freelancehunt Telegram Bot")
        # Set webhook only in production
        await on_startup(bot)
    
    # Create web application
    app = create_app()
    
    # Create and start web server
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, config.WEBAPP_HOST, config.WEBAPP_PORT)
    await site.start()
    
    logger.info(f"Webhook сервер запущено на {config.WEBAPP_HOST}:{config.WEBAPP_PORT}")
    if not config.DEV_MODE:
        logger.info(f"Webhook URL: {config.WEBHOOK_URL}")
    else:
        logger.info("DEV MODE: Webhook не встановлено")
    
    try:
        # Keep the server running
        await asyncio.Future()  # Run forever
    except (KeyboardInterrupt, SystemExit):
        logger.info("Зупинка сервера...")
    finally:
        if not config.DEV_MODE:
            await on_shutdown(bot)
        else:
            project_service_instance.stop_monitoring()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())