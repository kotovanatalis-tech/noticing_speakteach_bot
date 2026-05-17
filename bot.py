import os
import re
import anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ← вставьте Telegram ID разрешённых пользователей (Шаг 2 инструкции)
ALLOWED_USERS = [555619608, 244153970]

# ← вставьте данные ваших групп (Шаг 6 инструкции)
GROUPS = {
    "Группа SpeakTeach": {"chat_id": -1001412965575, "thread_id": 205},
    "Группа test": {"chat_id": -1003971082024, "thread_id": 2},
}

# Временное хранилище пока пользователь выбирает группу
pending = {}

async def handle_message(update, context):
    if update.message:
        print(f"chat_id: {update.message.chat.id}, thread_id: {update.message.message_thread_id}")
    if not update.message:
        return
    if update.message.chat.type != "private":
        return
    if update.message.from_user.id not in ALLOWED_USERS:
        return

    phrase = update.message.text.strip() if update.message.text else None
    photo = update.message.photo[-1] if update.message.photo else None
    caption = update.message.caption.strip() if update.message.caption else None

    target = phrase or caption
    if not target:
        await update.message.reply_text("Напиши фразу или отправь фото с подписью!")
        return

    clarification = ""
    match = re.search(r'\[([^\]]+)\]', target)
    if match:
        clarification = match.group(1)
        target = target[:match.start()].strip()

    hint = ""
    if clarification:
        hint = "\nContext hint (use this to give the correct definition, but do NOT mention it in your response): " + clarification

    prompt = (
        "You are an English vocabulary helper. "
        "The user gives you a word or phrase to explain. "
        "You MUST follow this format EXACTLY. Do NOT write placeholder text - write REAL sentences. "
        "Use the exact HTML tags as shown — they will render in Telegram.\n\n"
        "Format:\n"
        '"[REAL example sentence where TARGET appears, wrapped as <u><b>TARGET</b></u>]"\n\n'
        "<b>\U0001f4a1Definition:</b> [clear definition in English]\n\n"
        "<b>\U0001f913Russian equivalent:</b> [closest equivalent in Russian]\n\n"
        "<b>\U0001f58aExamples:</b>\n"
        "1. [REAL sentence with <u><b>TARGET</b></u>]\n"
        "2. [REAL sentence with <u><b>TARGET</b></u>]\n"
        "3. [REAL sentence with <u><b>TARGET</b></u>]\n\n"
        "The phrase to explain: TARGET"
    ).replace("TARGET", target) + hint

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    text = message.content[0].text

    # Сохраняем данные пока пользователь выбирает группу
    user_id = update.message.from_user.id
    pending[user_id] = {
        "text": text,
        "photo_id": photo.file_id if photo else None
    }

    # Показываем кнопки выбора группы
    keyboard = [[InlineKeyboardButton(name, callback_data=name)] for name in GROUPS]
    await update.message.reply_text(
        "Куда отправить?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_choice(update, context):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if user_id not in pending:
        await query.edit_message_text("Что-то пошло не так, попробуй снова.")
        return

    group_name = query.data
    group = GROUPS[group_name]
    data = pending.pop(user_id)

    if data["photo_id"]:
        await context.bot.send_photo(
            chat_id=group["chat_id"],
            message_thread_id=group["thread_id"],
            photo=data["photo_id"],
            caption=data["text"],
            parse_mode="HTML"
        )
    else:
        await context.bot.send_message(
            chat_id=group["chat_id"],
            message_thread_id=group["thread_id"],
            text=data["text"],
            parse_mode="HTML"
        )

    await query.edit_message_text(f"✅ Отправлено в {group_name}!")

app = ApplicationBuilder().token(os.environ["TELEGRAM_TOKEN"]).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(MessageHandler(filters.PHOTO, handle_message))
app.add_handler(CallbackQueryHandler(handle_choice))
app.run_polling()
