import os
import re
import base64
import anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes

GROUP_ID = -1001412965575
TOPIC_ID = 205
ALLOWED_USER_ID = 555619608

GAP_FILL_GROUPS = {
    "Teacherpreneurs": {
        "chat_id": -1001742887248,
        "thread_id": 379,
        "doc_url": "https://docs.google.com/document/d/1mwsIsbwzmG4gRbBxznaHeiMTXJOy2SFJuIFMKErjUx4/edit?usp=sharing"
    },
    "Smart cookies": {
        "chat_id": -1001757128185,
        "thread_id": 411,
        "doc_url": "https://docs.google.com/document/d/1zU4IcoV5WqsdAYvlkPtD9UBKfujes1jRImOewIWyWnc/edit?usp=sharing"
    },
    "Social butterflies": {
        "chat_id": -1001170324655,
        "thread_id": 118,
        "doc_url": "https://docs.google.com/document/d/1Gsstk5lRXxt68D9v-StzlJ6ISBx6x21QeQ0piKCQbB4/edit?usp=sharing"
    },
}

pending_gapfill = {}

async def handle_gapfill_command(update, context):
    if not update.message:
        return
    if update.message.chat.type != "private":
        return
    if update.message.from_user.id != ALLOWED_USER_ID:
        return

    await update.message.reply_text("Отправь фото со списком лексики!")
    context.user_data["waiting_for_gapfill"] = True

async def handle_message(update, context):
    if not update.message:
        return
    if update.message.chat.type != "private":
        return
    if update.message.from_user.id != ALLOWED_USER_ID:
        return

    photo = update.message.photo[-1] if update.message.photo else None
    caption = update.message.caption.strip() if update.message.caption else None
    phrase = update.message.text.strip() if update.message.text else None

    # GAP-FILL режим
    if context.user_data.get("waiting_for_gapfill") and photo:
        context.user_data["waiting_for_gapfill"] = False

        await update.message.reply_text("⏳ Генерирую gap-fill...")

        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()
        image_b64 = base64.b64encode(photo_bytes).decode("utf-8")

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

        gapfill_prompt = (
            "You are an English teacher assistant. "
            "Look at this image with a list of vocabulary items. "
            "First, find the TOPIC of the lesson — it is usually written in bold and highlighted. "
            "Then extract all vocabulary items that are written in BOLD. "
            "Create a gap-fill exercise:\n\n"
            "RULES:\n"
            "- Start with the topic: <b>\U0001f5c2 Topic: [topic]</b>\n"
            "- Then an empty line\n"
            "- Create one NATURAL, grammatically correct sentence per vocabulary item\n"
            "- Place the answer AS A SPOILER directly in the sentence where the gap would be\n"
            "- Do NOT put ___ — instead put the spoiler tag with the answer right there\n"
            "- Wrap the answer in: <tg-spoiler><b>answer</b></tg-spoiler>\n"
            "- Shuffle sentences in random order\n"
            "- Use ONLY HTML formatting, never markdown\n"
            "- Double-check grammar — every sentence must be 100% correct\n"
            "- IMPORTANT: adapt the vocabulary item to fit the sentence naturally — "
            "change pronouns, possessives, verb forms, tense as needed. "
            "For example: 'give my students some slack' should become 'give her some slack' "
            "or 'give the team some slack' — never copy pronouns from the original list\n"
            "- Each sentence must be a completely new, realistic context — "
            "do not reuse the same subject or situation across sentences\n\n"
            "Format exactly like this:\n"
            "<b>\U0001f5c2 Topic: Small Talk</b>\n\n"
            "1. Please <tg-spoiler><b>go easy on</b></tg-spoiler> her — she is going through a difficult time.\n"
            "2. His rude comment was <tg-spoiler><b>the last straw</b></tg-spoiler> — I finally quit the project.\n"
            "3. The company is <tg-spoiler><b>hanging by a thread</b></tg-spoiler> after losing its biggest client.\n\n"
            "Output ONLY the topic line and numbered list, nothing else."
        )

        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_b64
                        }
                    },
                    {
                        "type": "text",
                        "text": gapfill_prompt
                    }
                ]
            }]
        )

        gapfill_text = message.content[0].text

        pending_gapfill[update.message.from_user.id] = gapfill_text

        keyboard = [[InlineKeyboardButton(name, callback_data=f"gapfill_{name}")] for name in GAP_FILL_GROUPS]
        await update.message.reply_text("Куда отправить gap-fill?", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ОБЫЧНЫЙ режим
    target = phrase or caption
    if not target:
        await update.message.reply_text("Напиши фразу или отправь фото с подписью!\nДля gap-fill напиши /gap_fill")
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
        "You MUST use ONLY HTML tags for formatting: <b> for bold, <u> for underline. "
        "NEVER use markdown symbols like **, __, *, or _. ONLY HTML tags. "
        "The output will be sent via Telegram with parse_mode HTML. "
        "You MUST follow this format EXACTLY. Do NOT write placeholder text - write REAL sentences.\n\n"
        "FORMATTING RULES for examples:\n"
        "- In each sentence, identify the natural chunk containing TARGET — "
        "a ready-made block of language that a native speaker would lift and reuse as a whole unit\n"
        "- Wrap the whole chunk in <b>bold</b>\n"
        "- Wrap TARGET itself inside the chunk in <u>underline</u> as well\n"
        "- Example: I can't be <b>at your <u>beck and call</u></b> all the time.\n\n"
        "Format:\n"
        '"[REAL example sentence with TARGET formatted as above]"\n\n'
        "<b>\U0001f4a1Definition:</b> [clear definition in English]\n\n"
        "<b>\U0001f913Russian equivalent:</b> [closest equivalent in Russian]\n\n"
        "<b>\U0001f58aExamples:</b>\n"
        "1. [REAL sentence with TARGET formatted as above]\n"
        "2. [REAL sentence with TARGET formatted as above]\n"
        "3. [REAL sentence with TARGET formatted as above]\n\n"
        "The phrase to explain: TARGET"
    ).replace("TARGET", target) + hint

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1536,
        messages=[{"role": "user", "content": prompt}]
    )
    text = message.content[0].text
    text = text.replace("**", "").replace("__", "")

    if photo:
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()
        await context.bot.send_photo(
            chat_id=GROUP_ID,
            message_thread_id=TOPIC_ID,
            photo=bytes(photo_bytes),
        )
        await context.bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=TOPIC_ID,
            text=text,
            parse_mode="HTML"
        )
    else:
        await context.bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=TOPIC_ID,
            text=text,
            parse_mode="HTML"
        )

    await update.message.reply_text("✅ Отправлено в Speak&Teach!")

async def handle_callback(update, context):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data.startswith("gapfill_"):
        group_name = query.data.replace("gapfill_", "")
        group = GAP_FILL_GROUPS[group_name]

        if user_id not in pending_gapfill:
            await query.edit_message_text("Что-то пошло не так, попробуй снова.")
            return

        gapfill_text = pending_gapfill.pop(user_id)
        doc_url = group["doc_url"]

        full_text = (
            f"{gapfill_text}\n\n"
            f"\U0001f4ce <b>OUR LANGUAGE BOX</b>\n<a href='{doc_url}'>CLICK HERE</a>"
        )

        await context.bot.send_message(
            chat_id=group["chat_id"],
            message_thread_id=group["thread_id"],
            text=full_text,
            parse_mode="HTML"
        )

        await query.edit_message_text(f"✅ Отправлено в {group_name}!")

app = ApplicationBuilder().token(os.environ["TELEGRAM_TOKEN"]).build()
app.add_handler(CommandHandler("gap_fill", handle_gapfill_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(MessageHandler(filters.PHOTO, handle_message))
app.add_handler(CallbackQueryHandler(handle_callback))
app.run_polling()
