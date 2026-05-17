import os
import re
import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

GROUP_ID = -1001412965575
TOPIC_ID = 205
ALLOWED_USER_ID = 555619608

async def handle_message(update, context):
    if not update.message:
        return
    if update.message.chat.type != "private":
        return
    if update.message.from_user.id != ALLOWED_USER_ID:
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

    if photo:
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()
        await context.bot.send_photo(
            chat_id=GROUP_ID,
            message_thread_id=TOPIC_ID,
            photo=bytes(photo_bytes),
            caption=text,
            parse_mode="HTML"
        )
    else:
        await context.bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=TOPIC_ID,
            text=text,
            parse_mode="HTML"
        )

    await update.message.reply_text("✅ Отправлено в группу!")

app = ApplicationBuilder().token(os.environ["TELEGRAM_TOKEN"]).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(MessageHandler(filters.PHOTO, handle_message))
app.run_polling()
