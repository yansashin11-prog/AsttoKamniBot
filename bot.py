import os
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")

# Шаги диалога
NAME, BIRTHDATE, BIRTHTIME, BIRTHCITY, WISH, PHONE, EMAIL = range(7)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "✨ *Добро пожаловать в Камень & Звёзды!*\n\n"
        "Мы создаём украшения из натуральных камней, подобранных астрологом специально для вас.\n\n"
        "Давайте я соберу немного информации, чтобы астролог смог подготовить идеальное украшение 🌙\n\n"
        "Как вас зовут?",
        parse_mode="Markdown"
    )
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text(
        f"Приятно познакомиться, *{context.user_data['name']}*! ✦\n\n"
        "📅 Укажите вашу *дату рождения*\n\n"
        "Формат: ДД.ММ.ГГГГ\n"
        "Например: 15.03.1990",
        parse_mode="Markdown"
    )
    return BIRTHDATE

async def get_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    parts = text.replace("/", ".").replace("-", ".").split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите дату в формате *ДД.ММ.ГГГГ*\n"
            "Например: 15.03.1990",
            parse_mode="Markdown"
        )
        return BIRTHDATE
    context.user_data["birthdate"] = text
    await update.message.reply_text(
        "🕐 Укажите *время рождения*\n\n"
        "Формат: ЧЧ:ММ, например 14:30\n\n"
        "Если не знаете точное время — напишите *не знаю*",
        parse_mode="Markdown"
    )
    return BIRTHTIME

async def get_birthtime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["birthtime"] = update.message.text.strip()
    await update.message.reply_text(
        "🌍 В каком *городе* вы родились?\n\n"
        "Например: Москва, Санкт-Петербург, Киев...",
        parse_mode="Markdown"
    )
    return BIRTHCITY

async def get_birthcity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["birthcity"] = update.message.text.strip()
    await update.message.reply_text(
        "💫 Расскажите, *что вы хотите от украшения?*\n\n"
        "Например:\n"
        "— Привлечь любовь и гармонию в отношениях\n"
        "— Усилить финансовый поток и карьеру\n"
        "— Защита и ощущение спокойствия\n"
        "— Творческое вдохновение\n\n"
        "Опишите своими словами — чем подробнее, тем точнее подберём камни ✨",
        parse_mode="Markdown"
    )
    return WISH

async def get_wish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["wish"] = update.message.text.strip()
    await update.message.reply_text(
        "📞 Укажите ваш *номер телефона*\n\n"
        "Например: +7 900 123 45 67",
        parse_mode="Markdown"
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text.strip()
    await update.message.reply_text(
        "📧 Укажите вашу *электронную почту*\n\n"
        "Например: example@mail.ru",
        parse_mode="Markdown"
    )
    return EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    # Простая проверка формата email
    if "@" not in email or "." not in email.split("@")[-1]:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите корректный email\n"
            "Например: example@mail.ru",
            parse_mode="Markdown"
        )
        return EMAIL
    context.user_data["email"] = email
    data = context.user_data

    # Благодарим клиента
    await update.message.reply_text(
        f"✦ Спасибо, *{data['name']}*!\n\n"
        "Астролог получил вашу анкету и свяжется с вами в течение *24 часов* для обсуждения деталей.\n\n"
        "🌙 Камень & Звёзды",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

    # Отправляем анкету администратору
    await send_to_admin(data, update.effective_user)
    return ConversationHandler.END

async def send_to_admin(data, user):
    import httpx
    username = f"@{user.username}" if user.username else f"ID: {user.id}"
    msg = (
        f"🌟 *Новая анкета клиента*\n\n"
        f"👤 Имя: {data.get('name', '—')}\n"
        f"📱 Telegram: {username}\n"
        f"📞 Телефон: {data.get('phone', '—')}\n"
        f"📧 Email: {data.get('email', '—')}\n\n"
        f"🎂 Дата рождения: {data.get('birthdate', '—')}\n"
        f"🕐 Время рождения: {data.get('birthtime', '—')}\n"
        f"🌍 Город рождения: {data.get('birthcity', '—')}\n\n"
        f"💫 Пожелания:\n{data.get('wish', '—')}"
    )
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{ADMIN_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Диалог прерван. Напишите /start чтобы начать заново 🌙",
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
            NAME:      [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            BIRTHDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birthdate)],
            BIRTHTIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birthtime)],
            BIRTHCITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birthcity)],
            WISH:      [MessageHandler(filters.TEXT & ~filters.COMMAND, get_wish)],
            PHONE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            EMAIL:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    logger.info("Бот запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
