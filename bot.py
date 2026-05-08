import os
import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phrase = update.message.text.strip()
    
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"""You are an English vocabulary helper. The user gives you a word or phrase.
Respond ONLY in this exact format, no asterisks, no markdown:

"[example sentence where the target phrase is wrapped like this: <u><b>phrase</b></u>]"

Definition: [clear definition in English]

Examples:
1. [example sentence with <u><b>{phrase}</b></u> used naturally]
2. [example sentence with <u><b>{phrase}</b></u> used naturally]
3. [example sentence with <u><b>{phrase}</b></u> used naturally]

The phrase to explain: {phrase}"""
        }]
    )
    
    await update.message.reply_text(message.content[0].text, parse_mode="HTML")

app = ApplicationBuilder().token(os.environ["TELEGRAM_TOKEN"]).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling()
