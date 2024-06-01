import os
import json
import logging
from telegram import Update, Bot, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
import asyncio
from mpesa import initiate_mpesa_payment

load_dotenv()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN)

# Dictionary to store payment requests
payment_requests = {}

# Define menu options
menu_options = [
    ["Pay"],
    ["Help"]
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_markup = ReplyKeyboardMarkup(menu_options, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Welcome to the MPESA Payment Bot. Please choose an option: \n 1. Pay  \n 2. Help",
        reply_markup=reply_markup
    )

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        phone_number = update.message.text.split()[1]
        amount = update.message.text.split()[2]
        chat_id = update.message.chat_id
        request_id = initiate_mpesa_payment(phone_number, amount)
        if request_id:
            payment_requests[request_id] = chat_id
            await update.message.reply_text("Payment initiated successfully. You will receive a prompt on your phone.")
        else:
            await update.message.reply_text("Failed to initiate payment. Please try again.")
    except IndexError:
        await update.message.reply_text("Please provide the phone number and amount. Usage: /pay <phone_number> <amount>")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "To initiate a payment, use the /pay command followed by the phone number and amount. Example: /pay 254712345678 100"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if text == "Pay" or text == "1":
        await pay(update, context)
    elif text == "Help" or text == "2":
        await help_command(update, context)
    else:
        await update.message.reply_text("Invalid option. Please choose from the menu.")

def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    start_handler = CommandHandler('start', start)
    pay_handler = CommandHandler('pay', pay)
    help_handler = CommandHandler('help', help_command)
    message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)

    application.add_handler(start_handler)
    application.add_handler(pay_handler)
    application.add_handler(help_handler)
    application.add_handler(message_handler)

    logger.info("Starting Telegram bot...")
    loop.run_until_complete(application.run_polling())

if __name__ == '__main__':
    main()
