# Камень & Звёзды — Telegram Бот

## Что делает бот
1. Приветствует клиента
2. Собирает данные: имя, дата/время/город рождения, цель
3. Генерирует рекомендацию по камням через Claude AI
4. Отправляет анкету администратору

## Запуск на Railway

### 1. Зарегистрируйся на railway.app

### 2. Создай новый проект
- New Project → Deploy from GitHub repo
- Загрузи файлы этой папки

### 3. Добавь переменные окружения (Variables):
```
BOT_TOKEN=твой_токен_нового_бота
ADMIN_TOKEN=8530508120:AAEwIxPYt1zdKsZvat7-NTvPBFG6uZg7IO0
ADMIN_CHAT_ID=416666742
ANTHROPIC_API_KEY=твой_ключ_claude (необязательно)
```

### 4. Deploy — бот заработает автоматически!

## Без Railway (локально)
```bash
pip install -r requirements.txt
python bot.py
```
