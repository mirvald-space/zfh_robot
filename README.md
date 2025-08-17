# Freelancehunt Telegram Bot

Telegram бот для моніторингу нових проектів на Freelancehunt.com з автоматичними сповіщеннями та фільтрацією.

## 🚀 Можливості

- **Моніторинг проектів**: Автоматичне відстеження нових проектів на Freelancehunt
- **Розумна фільтрація**: Налаштовувані фільтри за категоріями, бюджетом, навичками
- **Сповіщення в реальному часі**: Миттєві сповіщення про підходящі проекти
- **Polling режим**: Стабільна робота без потреби в вебхуках
- **Rate limiting**: Інтелектуальне управління частотою API запитів

## 📋 Вимоги

- Docker та Docker Compose
- Telegram Bot Token (отримати у [@BotFather](https://t.me/BotFather))
- Freelancehunt API Token (отримати в [налаштуваннях профілю](https://freelancehunt.com/my/api))
- MongoDB база даних (наприклад, MongoDB Atlas)

## 🛠 Встановлення

```bash
# 1. Клонувати проект
git clone <repository-url>
cd zfh_robot

# 2. Створити .env файл
cp .env.example .env

# 3. Заповнити дані в .env файлі
TELEGRAM_BOT_TOKEN=ваш_токен_бота
FREELANCEHUNT_TOKEN=ваш_токен_api
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/database
MONGO_DB_NAME=zfh_robot

# 4. Запустити
docker-compose up -d
```

## 🚀 Запуск

```bash
# Запустити
docker-compose up -d

# Переглянути логи
docker-compose logs -f

# Зупинити
docker-compose down
```

Бот готовий до роботи!