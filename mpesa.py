
import os
import logging
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment variables
MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE")
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
CALLBACK_URL = os.getenv("CALLBACK_URL")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

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
