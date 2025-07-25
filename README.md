# Freelancehunt Telegram Bot

Telegram бот для моніторингу нових проектів на Freelancehunt.com з автоматичними сповіщеннями та фільтрацією.

## 🚀 Можливості

- **Моніторинг проектів**: Автоматичне відстеження нових проектів на Freelancehunt
- **Розумна фільтрація**: Налаштовувані фільтри за категоріями, бюджетом, навичками
- **Сповіщення в реальному часі**: Миттєві сповіщення про підходящі проекти
- **Webhook підтримка**: Робота через webhook для production або polling для розробки
- **Health monitoring**: Вбудована система моніторингу стану сервісів
- **Rate limiting**: Інтелектуальне управління частотою API запитів

## 📋 Вимоги

- Python 3.8+
- Telegram Bot Token (отримати у [@BotFather](https://t.me/BotFather))
- Freelancehunt API Token (отримати в [налаштуваннях профілю](https://freelancehunt.com/my/api))

## 🛠 Встановлення

### 1. Клонування репозиторію

```bash
git clone <repository-url>
cd freelancehunt-telegram-bot
```

### 2. Створення віртуального середовища

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# або
venv\Scripts\activate     # Windows
```

### 3. Встановлення залежностей

```bash
pip install -r requirements.txt
```

### 4. Налаштування змінних середовища

Скопіюйте `.env.example` в `.env` та заповніть необхідні значення:

```bash
cp .env.example .env
```

Відредагуйте `.env` файл:

```env
# Обов'язкові параметри
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
FREELANCEHUNT_TOKEN=your_freelancehunt_api_token_here

# Webhook налаштування (для production)
WEBHOOK_HOST=https://your-domain.com
WEBHOOK_PATH=/webhook

# Налаштування додатку
WEBAPP_HOST=0.0.0.0
WEBAPP_PORT=3000

# Режим розробки (true для локальної розробки)
DEV_MODE=false
```

## 🚀 Запуск

### Режим розробки (з polling)

```bash
DEV_MODE=true python main.py
```

### Production режим (з webhook)

```bash
python main.py
```

## 📊 Моніторинг

Бот надає кілька endpoints для моніторингу:

- `GET /` - Основний health check з детальною інформацією про сервіси
- `GET /health` - Альтернативний health check endpoint
- `GET /ping` - Проста перевірка доступності (повертає "pong")

### Приклад відповіді health check:

```json
{
  "status": "ok",
  "timestamp": 1640995200.0,
  "uptime_seconds": 3600,
  "environment": "production",
  "services": {
    "freelancehunt_api": {
      "ok": true,
      "connected": true
    },
    "telegram_bot": {
      "ok": true,
      "username": "your_bot_username",
      "bot_id": 123456789
    },
    "project_monitoring": {
      "ok": true,
      "active": true
    }
  },
  "version": "1.0.0"
}
```

## ⚙️ Конфігурація

### Основні параметри

| Параметр | Опис | За замовчуванням |
|----------|------|------------------|
| `DEFAULT_CHECK_INTERVAL` | Інтервал перевірки нових проектів (сек) | 60 |
| `MIN_CHECK_INTERVAL` | Мінімальний інтервал перевірки (сек) | 30 |
| `MAX_CHECK_INTERVAL` | Максимальний інтервал перевірки (сек) | 3600 |
| `MIN_API_REQUEST_INTERVAL` | Мінімальний інтервал між API запитами (сек) | 1.0 |

### Rate Limiting

| Параметр | Опис | За замовчуванням |
|----------|------|------------------|
| `RATE_LIMIT_WARNING_THRESHOLD` | Поріг попередження про ліміти | 20 |
| `RATE_LIMIT_CRITICAL_THRESHOLD` | Критичний поріг лімітів | 10 |

## 🌐 Деплой на Render.com

1. Підключіть репозиторій до Render.com
2. Створіть Web Service
3. Встановіть змінні середовища:
   - `TELEGRAM_BOT_TOKEN`
   - `FREELANCEHUNT_TOKEN`
   - `WEBHOOK_HOST` (буде автоматично встановлено з `RENDER_EXTERNAL_URL`)
4. Встановіть команду запуску: `python main.py`
5. Встановіть порт: `10000`

## 📝 API Документація

### Freelancehunt API

Бот використовує офіційне API Freelancehunt. Документація доступна за адресою:
https://apidocs.freelancehunt.com/

### Rate Limiting

API Freelancehunt має обмеження на кількість запитів. При перевищенні лімітів повертається HTTP 429.

Заголовки відповіді:
- `X-Ratelimit-Limit`: середня кількість запитів за період
- `X-Ratelimit-Remaining`: залишкова кількість запитів

## 🔧 Розробка

### Структура проекту

```
freelancehunt-telegram-bot/
├── main.py                 # Основна точка входу
├── config.py              # Конфігурація додатку
├── requirements.txt       # Python залежності
├── .env.example          # Приклад змінних середовища
├── README.md             # Документація
├── LICENSE               # Ліцензія проекту
└── src/
    ├── handlers/         # Telegram bot handlers
    ├── services/         # Бізнес-логіка
    ├── api/             # API клієнти
    └── utils/           # Утиліти
```

### Лінтинг коду

```bash
flake8 src/
black src/
```

### Git команди

```bash
# Додати всі зміни
git add .

# Зафіксувати зміни
git commit -m "Опис змін українською"

# Відправити на сервер
git push origin main
```

## 🤝 Участь у розробці

1. Зробіть fork репозиторію
2. Створіть гілку для нової функції (`git checkout -b feature/amazing-feature`)
3. Зафіксуйте зміни (`git commit -m 'Додати нову функцію'`)
4. Відправте в гілку (`git push origin feature/amazing-feature`)
5. Відкрийте Pull Request

## 📄 Ліцензія

Цей проект ліцензовано під MIT License - див. файл [LICENSE](LICENSE) для деталей.

## 🆘 Підтримка

Якщо у вас є питання або проблеми:

1. Перевірте [Issues](../../issues) на GitHub
2. Створіть новий Issue з детальним описом проблеми
3. Переконайтеся, що всі змінні середовища налаштовані правильно
4. Перевірте логи додатку для діагностики

## 📈 Моніторинг у Production

Для моніторингу у production рекомендується:

1. Налаштувати моніторинг health check endpoints
2. Налаштувати алерти на основі метрик uptime
3. Моніторити логи на предмет помилок API
4. Відстежувати rate limiting метрики

### Приклад моніторингу з curl:

```bash
# Перевірка стану
curl https://your-domain.com/health

# Проста перевірка доступності
curl https://your-domain.com/ping
```