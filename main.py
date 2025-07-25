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


async def main():
    """Запуск бота та створення завдання для перевірки проектів."""
    logger.info("Запуск Freelancehunt Telegram Bot")
    
    try:
        # Start polling
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот зупинено")
    finally:
        # Stop project monitoring
        project_service_instance.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())