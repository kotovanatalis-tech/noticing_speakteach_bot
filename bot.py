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

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": (
                f"You are an English vocabulary helper. "
                f"The user gives you a word or phrase to explain. "
                f"You MUST follow this format EXACTLY. Do NOT write placeholder text - write REAL sentences. "
                f"Use the exact HTML tags as shown — they will render in Telegram.\n\n"
                f"Format:\n"
                f"\"[REAL example sentence where {target} appears, wrapped as <u><b>{target}</b></u>]\"\n\n"
                f"<b>💡Definition:</b> [clear definition in English]\n\n"
                f"<b>🤓Russian
