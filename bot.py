import os
import json
import logging
from flask import Flask, request
from telegram import Update, Bot, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
import asyncio
import threading
from mpesa import initiate_mpesa_payment

app = Flask(__name__)

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

def telegram_bot_worker():
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

@app.route('/', methods=['GET'])
def defaultRoute():
    return 'Hello, world!'

@app.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    data = request.json
    logger.info(f"MPESA callback received: {json.dumps(data)}")

    # Extract relevant information from the callback
    callback_data = data.get("Body", {}).get("stkCallback", {})
    result_code = callback_data.get("ResultCode")
    checkout_request_id = callback_data.get("CheckoutRequestID")

    # Notify user if payment was successful
    if result_code == 0:
        chat_id = payment_requests.get(checkout_request_id)
        if chat_id:
            bot.send_message(chat_id, "Payment was successful. Thank you for your purchase!")
            del payment_requests[checkout_request_id]
    return "OK"

def main():
    # Initialize Telegram bot and add handlers
    telegram_bot_thread = threading.Thread(target=telegram_bot_worker)
    telegram_bot_thread.start()

    # Start Flask app
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == '__main__':
    main()