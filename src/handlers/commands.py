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
        await message.answer("❌ Спочатку активуйте бота командою /start", parse_mode='HTML', disable_web_page_preview=True)
        return
    
    # Get sent projects for this user
    user_sent_projects = user_manager.user_sent_projects.get(user_id, set())
    sent_count = len(user_sent_projects)
    
    # Get projects from API for comparison
    projects = await api_client.get_projects()
    if not projects:
        await message.answer("❌ Не вдалося отримати проекти з API", parse_mode='HTML', disable_web_page_preview=True)
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
    
    await message.answer(report, parse_mode='HTML', disable_web_page_preview=True)


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
        "🚨 Сповіщення про нові проекти <b>АКТИВОВАНО!</b>\n\n"
        f"Інтервал перевірки: <b>{user_manager.get_user_interval(user_id)} секунд</b>\n"
        f"Фільтр: <b>{user_manager.get_filter_description(user_id)}</b>\n\n"
        "<b>Команди:</b>\n"
        "/start - Запустити сповіщення\n"
        "/filter - обрати фільтр проектів\n"
        "/interval &lt;секунди&gt; - змінити інтервал перевірки\n"
        "/status - статус бота та API\n"
        "/stop - зупинити сповіщення\n"
        "/id_list - Список ID Категорій\n",
        parse_mode='HTML',
        disable_web_page_preview=True
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
        await message.answer("❌ Сповіщення про нові проекти <b>ЗУПИНЕНО!</b>\n\n"
                            "Ви можете знову активувати сповіщення командою <b>/start</b>", parse_mode='HTML', disable_web_page_preview=True)
    else:
        await message.answer("ℹ Сповіщення вже <b>ЗУПИНЕНО!</b>", parse_mode='HTML', disable_web_page_preview=True)


@router.message(Command("interval"))
async def cmd_interval(message: Message, command: CommandObject):
    """Handle /interval command - set check interval."""
    user_id = message.from_user.id
    
    if not command.args:
        current_interval = user_manager.get_user_interval(user_id)
        await message.answer(
            f"Поточний інтервал перевірки: <b>{current_interval} секунд</b>\n"
            f"Для зміни використовуйте команду: <b>/interval &lt;секунди&gt;</b>\n"
            f"Мінімальний інтервал: <b>{config.MIN_CHECK_INTERVAL} секунд</b>\n"
            f"Максимальний інтервал: <b>{config.MAX_CHECK_INTERVAL} секунд</b>",
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        return
    
    try:
        interval = int(command.args)
        
        # Validate and set interval
        if interval < config.MIN_CHECK_INTERVAL:
            await message.answer(f"⚠️ Мінімальний інтервал - {config.MIN_CHECK_INTERVAL} секунд.", parse_mode='HTML', disable_web_page_preview=True)
            interval = config.MIN_CHECK_INTERVAL
        elif interval > config.MAX_CHECK_INTERVAL:
            await message.answer(f"⚠️ Максимальний інтервал - {config.MAX_CHECK_INTERVAL} секунд.", parse_mode='HTML', disable_web_page_preview=True)
            interval = config.MAX_CHECK_INTERVAL
        
        await user_manager.set_user_interval(user_id, interval)
        await message.answer(f"✅ Інтервал перевірки встановлено на {interval} секунд.", parse_mode='HTML', disable_web_page_preview=True)
        
    except ValueError:
        await message.answer("❌ Помилка! Вкажіть число в секундах, наприклад: /interval 120", parse_mode='HTML', disable_web_page_preview=True)


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
        reply_markup=builder.as_markup(),
        parse_mode='HTML',
        disable_web_page_preview=True
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
        await callback.message.edit_text("✅ Фільтри скинуто. Будуть показані всі проекти.", parse_mode='HTML', disable_web_page_preview=True)
    else:
        filter_key = parts[1]
        filter_value = parts[2] if len(parts) > 2 else ""
        
        # Set the filter
        current_filters = user_manager.get_user_filters(user_id)
        current_filters[filter_key] = filter_value
        await user_manager.set_user_filters(user_id, current_filters)
        
        await callback.message.edit_text(
            f"✅ Фільтр встановлено: {filter_key}={filter_value}\n\n"
            f"Поточні фільтри: {user_manager.get_filter_description(user_id)}",
            parse_mode='HTML',
            disable_web_page_preview=True
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
        f"/{filter_key} значення",
        parse_mode='HTML',
        disable_web_page_preview=True
    )
    await callback.answer()


@router.message(Command("skill_id"))
async def cmd_skill_id(message: Message, command: CommandObject):
    """Handle /skill_id command - set skill_id filter."""
    user_id = message.from_user.id
    
    if not command.args:
        await message.answer("Вкажіть ID навичок через кому, наприклад: /skill_id 69,99", parse_mode='HTML', disable_web_page_preview=True)
        return
    
    # Set the filter
    current_filters = user_manager.get_user_filters(user_id)
    current_filters["skill_id"] = command.args
    await user_manager.set_user_filters(user_id, current_filters)
    
    await message.answer(
        f"✅ Фільтр за навичками встановлено: skill_id={command.args}\n\n"
        f"Поточні фільтри: {user_manager.get_filter_description(user_id)}",
        parse_mode='HTML',
        disable_web_page_preview=True
    )


@router.message(Command("employer_id"))
async def cmd_employer_id(message: Message, command: CommandObject):
    """Handle /employer_id command - set employer_id filter."""
    user_id = message.from_user.id
    
    if not command.args:
        await message.answer("Вкажіть ID роботодавця, наприклад: /employer_id 123", parse_mode='HTML', disable_web_page_preview=True)
        return
    
    # Set the filter
    current_filters = user_manager.get_user_filters(user_id)
    current_filters["employer_id"] = command.args
    await user_manager.set_user_filters(user_id, current_filters)
    
    await message.answer(
        f"✅ Фільтр за роботодавцем встановлено: employer_id={command.args}\n\n"
        f"Поточні фільтри: {user_manager.get_filter_description(user_id)}",
        parse_mode='HTML',
        disable_web_page_preview=True
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


@router.message(Command("id_list"))
async def cmd_id_list(message: Message):
    """Show list of all category IDs."""
    user_id = message.from_user.id
    
    # Check if user is active
    if not user_manager.is_user_active(user_id):
        await message.answer("❌ Спочатку активуйте бота командою /start", parse_mode='HTML', disable_web_page_preview=True)
        return
    
    # Category IDs list
    categories = [
        "1 - PHP",
        "2 - C & C++",
        "6 - Linux & Unix",
        "7 - Windows",
        "13 - Java",
        "14 - Search Engine Optimization (SEO)",
        "17 - Logo Design",
        "18 - Photo Processing",
        "22 - Python",
        "24 - C#",
        "28 - Javascript and Typescript",
        "37 - Text Translation",
        "38 - Articles & Blog Posts",
        "39 - System & Network Administration",
        "41 - Banners",
        "42 - Interface Design (UI/UX)",
        "43 - Web Design",
        "45 - Website Maintenance",
        "57 - Testing & QA",
        "58 - Vector Graphics",
        "59 - 3D Modeling",
        "64 - Object Design",
        "65 - Cybersecurity & Data Protection",
        "68 - Online Stores & E-commerce",
        "75 - Print Design",
        "76 - Copywriting",
        "77 - Corporate Style",
        "78 - Content Management Systems",
        "79 - English",
        "80 - German",
        "83 - Software & Server Configuration",
        "84 - Spanish",
        "86 - Databases & SQL",
        "88 - Gaming Apps",
        "89 - Project Management",
        "90 - Illustrations & Drawings",
        "91 - Animation",
        "93 - Icons & Pixel Graphics",
        "94 - Marketing Research",
        "95 - Tuition",
        "96 - Website Development",
        "97 - Technical Documentation",
        "99 - Web Programming",
        "100 - Music",
        "101 - Video Processing",
        "102 - Audio Processing",
        "103 - Desktop Apps",
        "104 - Content Management",
        "106 - Interior Design",
        "107 - Landscape Projects & Design",
        "108 - Architectural Design",
        "109 - Outdoor Advertising",
        "113 - Audio & Video Editing",
        "114 - Presentations",
        "117 - Packaging and label design",
        "120 - Apps for iOS (iPhone and iPad)",
        "121 - App Development for Android",
        "122 - Transcribing",
        "123 - Naming & Slogans",
        "124 - HTML & CSS",
        "125 - Rewriting",
        "127 - Contextual Advertising",
        "129 - Payment Systems Integration",
        "131 - Social Media Marketing (SMM)",
        "132 - Exhibition Booth Design",
        "133 - Social Media Advertising",
        "134 - Website SEO Audit",
        "135 - Search Engine Reputation Management (SERM)",
        "136 - Email Marketing",
        "138 - Advertising",
        "139 - Photography",
        "140 - Poems, Songs & Prose",
        "141 - Artwork",
        "143 - Speaker & Voice Services",
        "144 - Video Advertising",
        "145 - Teaser Advertisements",
        "147 - Drawings & Diagrams",
        "148 - Engineering",
        "149 - Accounting Services",
        "150 - Client Management & CRM",
        "151 - Social Media Page Design",
        "152 - Type & Font Design",
        "153 - Legal Services",
        "154 - Consulting",
        "156 - Business Card Design",
        "157 - Software, Website & Game Localization",
        "158 - French",
        "159 - Recruitment (HR)",
        "161 - Video Recording",
        "162 - Lead Generation & Sales",
        "163 - Script Writing",
        "164 - Industrial Design",
        "168 - Text Editing & Proofreading",
        "169 - Data Parsing",
        "170 - Information Gathering",
        "171 - Customer Support",
        "172 - Infographics",
        "175 - AI & Machine Learning",
        "176 - Embedded Systems & Microcontrollers",
        "178 - Data Processing",
        "179 - Mobile Apps Design",
        "180 - Bot Development",
        "181 - DevOps",
        "182 - Cryptocurrency & Blockchain",
        "183 - Hybrid Mobile Apps",
        "184 - Link Building",
        "185 - AR & VR Development",
        "186 - AI Art",
        "187 - VR & AR Design",
        "188 - Mechanical Engineering & Instrument Making",
        "189 - Enterprise Resource Planning (ERP)",
        "190 - AI Consulting",
        "191 - AI Speech & Audio Generation",
        "192 - Video Creation by Artificial Intelligence",
        "193 - App Store Optimization (ASO)",
        "194 - Public Relations (PR)",
        "195 - Polish",
        "196 - Ukrainian",
        "197 - AI Content Creation",
        "198 - Clothing design"
    ]
    
    # Split categories into chunks to avoid message length limit
    chunk_size = 30
    chunks = [categories[i:i + chunk_size] for i in range(0, len(categories), chunk_size)]
    
    # Send header message
    await message.answer(
        "📋 <b>Список ID категорій FreelanceHunt:</b>\n\n"
        "Використовуйте ці ID для команди /skill_id\n"
        "Наприклад: <code>/skill_id 22</code> для Python",
        parse_mode='HTML',
        disable_web_page_preview=True
    )
    
    # Send categories in chunks
    for i, chunk in enumerate(chunks, 1):
        chunk_text = "\n".join(chunk)
        header = f"📄 <b>Частина {i}/{len(chunks)}:</b>\n\n"
        
        await message.answer(
            f"{header}<code>{chunk_text}</code>",
            parse_mode='HTML',
            disable_web_page_preview=True
        )


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
        f"Користувач: <b>{name}</b>\n"
        f"Username: <b>@{username}</b>\n"
        f"Сповіщення: <b>{'✅ Активні' if is_active else '❌ Зупинено'}</b>\n"
        f"Інтервал перевірки: <b>{current_interval} секунд</b>\n"
        f"Фільтр: <b>{filter_desc}</b>\n"
        f"Дата реєстрації: <b>{created_at_str}</b>\n\n"
        f"📡 <b>Загальна статистика</b>\n"
        f"Активних користувачів: <b>{stats['active_users']}</b>\n"
        f"Нових користувачів за 24г: <b>{new_users_24h}</b>\n"
        f"Всього надіслано проектів: <b>{stats['sent_projects']}</b>"
    )
    
    await message.answer(status_text, parse_mode='HTML', disable_web_page_preview=True)