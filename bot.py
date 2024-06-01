import os
import json
import logging
from flask import Flask, request
from telegram import Update, Bot, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE")
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
CALLBACK_URL = os.getenv("CALLBACK_URL")

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Telegram bot initialization
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
    await update.message.reply_text("Please enter the phone number and amount in the format: /pay <phone_number> <amount>")

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

def initiate_mpesa_payment(phone_number: str, amount: str) -> str:
    access_token = get_mpesa_access_token()
    if not access_token:
        logger.error("Failed to obtain MPESA access token.")
        return None

    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": generate_password(),
        "Timestamp": get_timestamp(),
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": "Test123",
        "TransactionDesc": "Payment for goods"
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        logger.info("MPESA payment request initiated successfully.")
        return response.json().get("CheckoutRequestID")
    else:
        logger.error(f"MPESA payment request failed: {response.text}")
        return None

def get_mpesa_access_token() -> str:
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET))
    if response.status_code == 200:
        logger.info("MPESA access token obtained successfully.")
        return response.json().get("access_token")
    logger.error(f"Failed to obtain MPESA access token: {response.text}")
    return None

def generate_password() -> str:
    from base64 import b64encode
    from datetime import datetime
    timestamp = get_timestamp()
    password_str = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
    password = b64encode(password_str.encode()).decode('utf-8')
    return password

def get_timestamp() -> str:
    from datetime import datetime
    return datetime.now().strftime('%Y%m%d%H%M%S')

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


@app.route('/', methods=['GET'])
def defaultRoute():
    return 'Hello, world!'

def main():
    # Initialize Flask app and start it
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

    # Initialize Telegram bot and add handlers
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
    application.run_polling()

if __name__ == '__main__':
    main()