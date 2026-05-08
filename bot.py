import os
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

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"You are an English vocabulary helper. Respond ONLY in this format, no asterisks:\n\n\"[example sentence with <u><b>{target}</b></u>]\"\n\nDefinition: [clear definition]\n\nExamples:\n1. [sentence with <u><b>{target}</b></u>]\n2. [sentence with <u><b>{target}</b></u>]\n3. [sentence with <u><b>{target}</b></u>]"
        }]
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
