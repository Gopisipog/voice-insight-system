import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

load_dotenv()

class BotManager:
    def __init__(self, token=None):
        token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found. Please set it in .env")
            
        self.application = ApplicationBuilder().token(token).build()
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not self.chat_id:
            print("Warning: TELEGRAM_CHAT_ID not found. Notifications will not be sent.")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Voice Insight Bot Active!")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Interactively answers questions about the captured insights.
        """
        user_text = update.message.text
        # Logic for AI follow-up would go here
        await update.message.reply_text(f"Interactive mode: You asked '{user_text}'. Logic for AI answers is under development.")

    async def send_notification(self, text):
        """
        Sends a message to the pre-configured chat_id.
        """
        if self.chat_id:
            try:
                await self.application.bot.send_message(
                    chat_id=self.chat_id, 
                    text=text,
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"Failed to send telegram notification: {e}")

if __name__ == "__main__":
    pass
