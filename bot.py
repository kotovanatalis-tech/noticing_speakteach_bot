import os
import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

GROUP_ID = -1001412965575
TOPIC_ID = 205

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    
    # Отвечаем ТОЛЬКО на личные сообщения
    if update.message.chat.type != "private":
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
            "content": f"""You are an English vocabulary helper. The user gives you a word or phrase.
Respond ONLY in this exact format, no asterisks, no markdown symbols:

"[example sentence where the target phrase is wrapped like this: <u><b>phrase</b></u>]"

Definition: [clear definition in English]

Examples:
1. [example sentence with <u><b>{target}</b></u> used naturally]
2. [example sentence with <u><b>{target}</b></u> used naturally]
3. [example sentence with <u><b>{target}</b></u> used naturally]

The phrase to explain: {target}"""
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
            parse_
