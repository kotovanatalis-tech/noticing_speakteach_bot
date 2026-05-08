import os
import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phrase = update.message.text.strip()
    
    message = ANTHROPIC_CLIENT.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"""You are an English vocabulary helper. The user gives you a word or phrase. 
Respond ONLY in this exact format:

"[example sentence with the phrase in **bold**]"

**Definition:** [clear definition in English]

**Examples:**
1. [example sentence]
2. [example sentence]
3. [example sentence]

The phrase to explain: {phrase}"""
        }]
    )
    
    await update.message.reply_text(message.content[0].text)

app = ApplicationBuilder().token(os.environ["TELEGRAM_TOKEN"]).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling()
