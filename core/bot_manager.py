import logging
import os
from dotenv import load_dotenv

load_dotenv()


class BotManager:
    def __init__(self, token=None):
        # Lazy import - telegram might not be installed
        try:
            from telegram import Update
            from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
            self.Update = Update
            self.ApplicationBuilder = ApplicationBuilder
            self.ContextTypes = ContextTypes
        except ImportError:
            raise ImportError("python-telegram-bot not installed. Install with: pip install python-telegram-bot")

        token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found. Please set it in .env")

        self.application = self.ApplicationBuilder().token(token).build()
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not self.chat_id:
            print("Warning: TELEGRAM_CHAT_ID not found. Notifications will not be sent.")

    async def start(self, update, context):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Voice Insight Bot Active!")

    async def handle_message(self, update, context):
        user_text = update.message.text
        await update.message.reply_text(f"Interactive mode: You asked '{user_text}'. Logic for AI answers is under development.")

    async def send_notification(self, text):
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
