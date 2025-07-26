"""
Bot command handlers.

Handles all Telegram bot commands.
"""

import logging

from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
from src.api.freelancehunt import api_client
from src.api.rate_limiter import rate_limiter
from src.utils.user_manager import user_manager
from src.services.project_service import project_service
from src.utils.db_manager import db_manager

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("debug_sent"))
async def cmd_debug_sent(message: Message):
    """Debug command to check sent projects status."""
    user_id = message.from_user.id
    
    # Check if user is active
    if not user_manager.is_user_active(user_id):
        await message.answer("❌ Спочатку активуйте бота командою /start")
        return
    
    # Get sent projects for this user
    user_sent_projects = user_manager.user_sent_projects.get(user_id, set())
    sent_count = len(user_sent_projects)
    
    # Get projects from API for comparison
    projects = await api_client.get_projects()
    if not projects:
        await message.answer("❌ Не вдалося отримати проекти з API")
        return
    
    # Count how many current projects are marked as sent to this user
    api_project_ids = [p.get("id") for p in projects]
    sent_api_projects = [pid for pid in api_project_ids if pid in user_sent_projects]
    
    # Calculate total sent projects across all users
    total_sent_projects = sum(len(projects) for projects in user_manager.user_sent_projects.values())
    
    # Generate report
    report = (
        f"📊 <b>Діагностика відправлених проектів</b>\n\n"
        f"Загальна кількість відправлених проектів (всім користувачам): {total_sent_projects}\n"
        f"Проектів відправлено вам: {sent_count}\n"
        f"Кількість отриманих проектів з API: {len(projects)}\n"
        f"З них відмічено як відправлені вам: {len(sent_api_projects)}\n\n"
    )
    
    # Add information about the first 5 projects
    if projects:
        report += "<b>Останні проекти:</b>\n"
        for i, project in enumerate(projects[:5]):
            project_id = project.get("id")
            name = project.get("attributes", {}).get("name", "Без назви")
            is_sent = "✅" if project_id in user_sent_projects else "❌"
            report += f"{i+1}. {is_sent} ID {project_id}: {name[:30]}...\n"
    
    await message.answer(report)


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command - activate project notifications."""
    user_id = message.from_user.id
    
    # Get user information
    user_info = {
        "first_name": message.from_user.first_name,
        "last_name": message.from_user.last_name,
        "username": message.from_user.username
    }
    
    # Activate user with additional info
    await user_manager.activate_user(user_id, user_info)
    
    await message.answer(
        "✅ Сповіщення про нові проекти активовано!\n\n"
        f"Інтервал перевірки: {user_manager.get_user_interval(user_id)} секунд\n"
        f"Фільтр: {user_manager.get_filter_description(user_id)}\n\n"
        "Використовуйте команди:\n"
        "/filter - обрати фільтр проектів\n"
        "/interval &lt;секунди&gt; - змінити інтервал перевірки\n"
        "/status - статус бота та API\n"
        "/stop - зупинити сповіщення"
    )
    
    # Start the monitoring service if not already running
    if project_service and not project_service.is_running:
        import asyncio
        asyncio.create_task(project_service.start_monitoring())


@router.message(Command("stop"))
async def cmd_stop(message: Message):
    """Handle /stop command - deactivate project notifications."""
    user_id = message.from_user.id
    
    if await user_manager.deactivate_user(user_id):
        await message.answer("❌ Сповіщення про нові проекти зупинено.")
    else:
        await message.answer("Сповіщення вже зупинено.")


@router.message(Command("interval"))
async def cmd_interval(message: Message, command: CommandObject):
    """Handle /interval command - set check interval."""
    user_id = message.from_user.id
    
    if not command.args:
        current_interval = user_manager.get_user_interval(user_id)
        await message.answer(
            f"Поточний інтервал перевірки: {current_interval} секунд\n"
            f"Для зміни використовуйте команду /interval &lt;секунди&gt;\n"
            f"Мінімальний інтервал: {config.MIN_CHECK_INTERVAL} секунд\n"
            f"Максимальний інтервал: {config.MAX_CHECK_INTERVAL} секунд"
        )
        return
    
    try:
        interval = int(command.args)
        
        # Validate and set interval
        if interval < config.MIN_CHECK_INTERVAL:
            await message.answer(f"⚠️ Мінімальний інтервал - {config.MIN_CHECK_INTERVAL} секунд.")
            interval = config.MIN_CHECK_INTERVAL
        elif interval > config.MAX_CHECK_INTERVAL:
            await message.answer(f"⚠️ Максимальний інтервал - {config.MAX_CHECK_INTERVAL} секунд.")
            interval = config.MAX_CHECK_INTERVAL
        
        await user_manager.set_user_interval(user_id, interval)
        await message.answer(f"✅ Інтервал перевірки встановлено на {interval} секунд.")
        
    except ValueError:
        await message.answer("❌ Помилка! Вкажіть число в секундах, наприклад: /interval 120")


@router.message(Command("filter"))
async def cmd_filter(message: Message):
    """Handle /filter command - show filter options."""
    builder = InlineKeyboardBuilder()
    
    # Тимчасово прибрана кнопка "Проекти за моїми навичками" (only_my_skills)
    # оскільки цей фільтр працює тільки з персональним ключем
    # builder.button(text="Проекти за моїми навичками", callback_data="filter:only_my_skills:1")
    builder.button(text="За ID навичок", callback_data="input:skill_id")
    builder.button(text="За ID роботодавця", callback_data="input:employer_id")
    builder.button(text="Тільки для Plus", callback_data="filter:only_for_plus:1")
    builder.button(text="Без фільтрів (усі проекти)", callback_data="filter:clear")
    
    # Adjust to 1 button per row
    builder.adjust(1)
    
    await message.answer(
        "Оберіть фільтр для проектів:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("filter:"))
async def handle_filter_callback(callback: CallbackQuery):
    """Handle filter selection callbacks."""
    user_id = callback.from_user.id
    parts = callback.data.split(":")
    
    if len(parts) == 1:
        await callback.answer("Помилка у форматі фільтра")
        return
    
    # Clear all filters
    if parts[1] == "clear":
        await user_manager.clear_user_filters(user_id)
        await callback.message.edit_text("✅ Фільтри скинуто. Будуть показані всі проекти.")
    else:
        filter_key = parts[1]
        filter_value = parts[2] if len(parts) > 2 else ""
        
        # Set the filter
        current_filters = user_manager.get_user_filters(user_id)
        current_filters[filter_key] = filter_value
        await user_manager.set_user_filters(user_id, current_filters)
        
        await callback.message.edit_text(
            f"✅ Фільтр встановлено: {filter_key}={filter_value}\n\n"
            f"Поточні фільтри: {user_manager.get_filter_description(user_id)}"
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("input:"))
async def handle_input_callback(callback: CallbackQuery):
    """Handle callbacks that require user input."""
    filter_key = callback.data.split(":")[1]
    
    await callback.message.edit_text(
        f"Введіть значення для фільтра {filter_key}.\n\n"
        f"Приклади:\n"
        f"- Для skill_id: 69,99 (через кому)\n"
        f"- Для employer_id: 123\n\n"
        f"Надішліть повідомлення у форматі:\n"
        f"/{filter_key} значення"
    )
    await callback.answer()


@router.message(Command("skill_id"))
async def cmd_skill_id(message: Message, command: CommandObject):
    """Handle /skill_id command - set skill_id filter."""
    user_id = message.from_user.id
    
    if not command.args:
        await message.answer("Вкажіть ID навичок через кому, наприклад: /skill_id 69,99")
        return
    
    # Set the filter
    current_filters = user_manager.get_user_filters(user_id)
    current_filters["skill_id"] = command.args
    await user_manager.set_user_filters(user_id, current_filters)
    
    await message.answer(
        f"✅ Фільтр за навичками встановлено: skill_id={command.args}\n\n"
        f"Поточні фільтри: {user_manager.get_filter_description(user_id)}"
    )


@router.message(Command("employer_id"))
async def cmd_employer_id(message: Message, command: CommandObject):
    """Handle /employer_id command - set employer_id filter."""
    user_id = message.from_user.id
    
    if not command.args:
        await message.answer("Вкажіть ID роботодавця, наприклад: /employer_id 123")
        return
    
    # Set the filter
    current_filters = user_manager.get_user_filters(user_id)
    current_filters["employer_id"] = command.args
    await user_manager.set_user_filters(user_id, current_filters)
    
    await message.answer(
        f"✅ Фільтр за роботодавцем встановлено: employer_id={command.args}\n\n"
        f"Поточні фільтри: {user_manager.get_filter_description(user_id)}"
    )


# Временно отключена команда /myskills так как требует персональный API ключ
# @router.message(Command("myskills"))
# async def cmd_myskills(message: Message):
#     """Handle /myskills command - show user's skills from profile."""
#     try:
#         user_skills = await api_client.get_user_skills()
#         
#         if user_skills:
#             await message.answer(
#                 f"🔧 Ваши навыки (ID): {', '.join(map(str, user_skills))}\n\n"
#                 f"Всего навыков: {len(user_skills)}\n\n"
#                 f"⚠️ Фильтр 'Проекты по моим навыкам' временно недоступен,\n"
#                 f"так как работает только с персональным API ключом.\n"
#                 f"Используйте фильтр 'По ID навыков' для поиска по конкретным навыкам."
#             )
#         else:
#             await message.answer(
#                 "❌ Не удалось получить список ваших навыков.\n"
#                 "Проверьте, что:\n"
#                 "1. API токен корректный\n"
#                 "2. У вас есть навыки в профиле на Freelancehunt\n"
#                 "3. Не превышен лимит API запросов\n\n"
#                 "⚠️ Фильтр 'Проекты по моим навыкам' временно недоступен."
#             )
#     except Exception as e:
#         logger.error(f"Error in myskills command: {e}")
#         await message.answer("❌ Произошла ошибка при получении навыков.")


@router.message(Command("status"))
async def cmd_status(message: Message):
    """Handle /status command - show bot and API status."""
    user_id = message.from_user.id
    
    # Get user status
    is_active = user_manager.is_user_active(user_id)
    current_interval = user_manager.get_user_interval(user_id)
    filter_desc = user_manager.get_filter_description(user_id)
    
    # Get user details from database
    user_details = await db_manager.get_user(user_id)
    
    # Format user details
    created_at = user_details.get("created_at", "невідомо") if user_details else "немає в БД"
    if isinstance(created_at, str):
        created_at_str = created_at
    else:
        # Format datetime
        created_at_str = created_at.strftime("%d.%m.%Y %H:%M:%S")
    
    # Get username from DB or current message
    username = user_details.get("username") if user_details else None
    if not username:
        username = message.from_user.username or "не вказано"
    
    # Get user's name from DB or current message
    if user_details and "first_name" in user_details:
        first_name = user_details.get("first_name", "")
        last_name = user_details.get("last_name", "")
        name = f"{first_name} {last_name}".strip() or "не вказано"
    else:
        first_name = message.from_user.first_name or ""
        last_name = message.from_user.last_name or ""
        name = f"{first_name} {last_name}".strip() or "не вказано"
    
    # Get stats
    stats = await user_manager.get_stats()
    new_users_24h = stats.get("new_users_24h", 0)
    
    status_text = (
        f"📊 <b>Статус бота</b>\n\n"
        f"👤 <b>Користувач:</b> {name}\n"
        f"🆔 <b>Username:</b> @{username}\n"
        f"🔔 Сповіщення: {'✅ Активні' if is_active else '❌ Зупинено'}\n"
        f"⏱ Інтервал перевірки: {current_interval} секунд\n"
        f"🔍 Фільтр: {filter_desc}\n"
        f"📅 Дата реєстрації: {created_at_str}\n\n"
        f"📡 <b>Загальна статистика</b>\n"
        f"👥 Активних користувачів: {stats['active_users']}\n"
        f"👤 Нових користувачів за 24г: {new_users_24h}\n"
        f"📝 Надіслано проектів: {stats['sent_projects']}"
    )
    
    await message.answer(status_text)