import os
import json
import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
import anthropic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токены
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8601952102:AAH3B4tQnElUJW5XaCKg1S8xOd38mDqRl4Q")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "8530508120:AAEwIxPYt1zdKsZvat7-NTvPBFG6uZg7IO0")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "416666742")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Шаги диалога
NAME, BIRTHDATE, BIRTHTIME, BIRTHCITY, GOAL = range(5)

GOALS = ["💼 Карьера и деньги", "💕 Любовь и отношения", "🌿 Здоровье и энергия", "🛡 Защита и покой", "🎨 Творчество и вдохновение"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "✨ *Добро пожаловать в Камень & Звёзды*\n\n"
        "Я помогу подобрать украшение из натуральных камней специально для вас — "
        "на основе вашей натальной карты и жизненных целей.\n\n"
        "Это займёт всего 2 минуты 🌙\n\n"
        "Как вас зовут?",
        parse_mode="Markdown"
    )
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text(
        f"Приятно познакомиться, *{context.user_data['name']}*! ✦\n\n"
        "Укажите дату рождения в формате *ДД.ММ.ГГГГ*\n"
        "Например: 15.03.1990",
        parse_mode="Markdown"
    )
    return BIRTHDATE

async def get_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    # Простая проверка формата
    parts = text.replace("/", ".").replace("-", ".").split(".")
    if len(parts) != 3:
        await update.message.reply_text("Пожалуйста, введите дату в формате ДД.ММ.ГГГГ\nНапример: 15.03.1990")
        return BIRTHDATE
    context.user_data["birthdate"] = text
    await update.message.reply_text(
        "🕐 Укажите *время рождения* (если знаете)\n\n"
        "Формат: ЧЧ:ММ, например 14:30\n"
        "Если не знаете — напишите *не знаю*",
        parse_mode="Markdown"
    )
    return BIRTHTIME

async def get_birthtime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["birthtime"] = update.message.text.strip()
    await update.message.reply_text(
        "🌍 В каком *городе* вы родились?",
        parse_mode="Markdown"
    )
    return BIRTHCITY

async def get_birthcity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["birthcity"] = update.message.text.strip()
    keyboard = [[g] for g in GOALS]
    await update.message.reply_text(
        "✦ Последний вопрос!\n\n"
        "Какая *главная цель* сейчас для вас?\n"
        "Выберите или напишите своё:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return GOAL

async def get_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["goal"] = update.message.text.strip()
    await update.message.reply_text(
        "🔮 Анализирую вашу натальную карту...\n\nЭто займёт несколько секунд ✨",
        reply_markup=ReplyKeyboardRemove()
    )

    # Получаем данные пользователя
    data = context.user_data
    name = data.get("name", "")
    birthdate = data.get("birthdate", "")
    birthtime = data.get("birthtime", "не указано")
    birthcity = data.get("birthcity", "")
    goal = data.get("goal", "")

    # Генерируем рекомендацию через Claude API
    recommendation = await get_ai_recommendation(name, birthdate, birthtime, birthcity, goal)

    # Отправляем рекомендацию клиенту
    await update.message.reply_text(
        f"✨ *Ваша персональная рекомендация*\n\n{recommendation}\n\n"
        "─────────────────\n"
        "Хотите заказать украшение? Наш астролог свяжется с вами в течение 24 часов.\n\n"
        "👉 Оставьте контакт для связи (Telegram username или телефон):",
        parse_mode="Markdown"
    )

    # Уведомляем администратора
    await notify_admin(name, birthdate, birthtime, birthcity, goal, recommendation, update.effective_user)

    return ConversationHandler.END

async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем контакт после рекомендации"""
    contact = update.message.text.strip()
    name = context.user_data.get("name", "Клиент")

    await update.message.reply_text(
        f"Спасибо, *{name}*! ✦\n\n"
        "Астролог свяжется с вами в течение 24 часов.\n\n"
        "Если хотите узнать больше о наших украшениях:\n"
        "🌐 kamni-zvezdy.ru",
        parse_mode="Markdown"
    )

    # Обновляем уведомление администратора с контактом
    import httpx
    msg = f"📱 Контакт клиента *{name}*: {contact}"
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{ADMIN_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        )

async def get_ai_recommendation(name, birthdate, birthtime, birthcity, goal):
    """Генерируем рекомендацию через Claude API"""
    if not ANTHROPIC_API_KEY:
        # Фоллбек если нет API ключа
        return get_fallback_recommendation(goal)

    try:
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            messages=[{
                "role": "user",
                "content": f"""Ты астролог-эксперт по натуральным камням. 
Клиент: {name}
Дата рождения: {birthdate}
Время рождения: {birthtime}
Город рождения: {birthcity}
Главная цель: {goal}

Составь персональную рекомендацию по камням для украшения (браслет/кулон). 
Укажи:
1. Знак зодиака и его особенности
2. 2-3 камня которые подойдут именно этому человеку с учётом цели
3. Почему именно эти камни
4. Как носить

Пиши тепло, образно, мистично. Без лишних технических деталей. До 300 слов."""
            }]
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return get_fallback_recommendation(goal)

def get_fallback_recommendation(goal):
    """Рекомендация без API"""
    recs = {
        "💼 Карьера и деньги": "🪨 *Тигровый глаз* — камень воли и финансового успеха. Активирует Солнце и Марс, помогает достигать целей и привлекает материальное благополучие.\n\n🪨 *Лазурит* — камень мудрости и ясного ума. Усиливает Юпитер, помогает в переговорах и принятии верных решений.\n\n🪨 *Цитрин* — камень изобилия. Притягивает удачу и финансовые возможности.",
        "💕 Любовь и отношения": "🪨 *Розовый кварц* — камень безусловной любви. Открывает сердечную чакру и притягивает гармоничные отношения.\n\n🪨 *Лунный камень* — камень женственности и интуиции. Усиливает Луну, делает вас магнетичной и притягательной.\n\n🪨 *Малахит* — камень Венеры. Помогает открыться любви и исцелить сердечные раны.",
        "🌿 Здоровье и энергия": "🪨 *Сердолик* — камень жизненной силы. Наполняет энергией, укрепляет тело и дух.\n\n🪨 *Горный хрусталь* — универсальный очиститель. Гармонизирует энергетику и усиливает другие камни.\n\n🪨 *Аметист* — камень покоя. Снимает стресс, улучшает сон и восстанавливает силы.",
        "🛡 Защита и покой": "🪨 *Аметист* — мощный защитный камень. Создаёт энергетический щит и отражает негативные энергии.\n\n🪨 *Чёрный турмалин* — заземляет и защищает. Поглощает негатив и создаёт ощущение безопасности.\n\n🪨 *Лазурит* — камень истины. Защищает от обмана и помогает видеть ситуацию ясно.",
        "🎨 Творчество и вдохновение": "🪨 *Сердолик* — камень творческого огня. Пробуждает вдохновение и помогает воплощать идеи в жизнь.\n\n🪨 *Лунный камень* — камень интуиции и воображения. Открывает творческий поток.\n\n🪨 *Аметист* — камень высшего сознания. Связывает с источником вдохновения и духовной мудростью.",
    }
    # Ищем совпадение по ключевым словам
    for key, rec in recs.items():
        if any(word in goal for word in key.split()):
            return rec
    return recs["🌿 Здоровье и энергия"]

async def notify_admin(name, birthdate, birthtime, birthcity, goal, recommendation, user):
    """Отправляем анкету администратору"""
    import httpx
    username = f"@{user.username}" if user.username else f"ID: {user.id}"
    msg = (
        f"🌟 *Новая анкета клиента*\n\n"
        f"👤 Имя: {name}\n"
        f"📱 Telegram: {username}\n"
        f"🎂 Дата рождения: {birthdate}\n"
        f"🕐 Время рождения: {birthtime}\n"
        f"🌍 Город рождения: {birthcity}\n"
        f"🎯 Цель: {goal}\n\n"
        f"─────────────────\n"
        f"🔮 *Рекомендация бота:*\n{recommendation[:500]}..."
    )
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{ADMIN_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Диалог прерван. Напишите /start чтобы начать заново.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Напишите /start чтобы начать подбор украшения ✨"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            BIRTHDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birthdate)],
            BIRTHTIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birthtime)],
            BIRTHCITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birthcity)],
            GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_goal)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    # После диалога ловим контакт
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact))

    logger.info("Бот запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
