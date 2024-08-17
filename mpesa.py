
import os, time, json
import logging
import requests
import datetime
import base64
from dotenv import load_dotenv
import requests

STATUS_FILE = 'transaction_statuses.json'

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

def save_transaction_status(checkout_request_id: str, status: str):
    if not os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, 'w') as f:
            json.dump({}, f)  

    with open(STATUS_FILE, 'r') as f:
        statuses = json.load(f)

    statuses[checkout_request_id] = status

    with open(STATUS_FILE, 'w') as f:
        json.dump(statuses, f, indent=4)

def get_transaction_status(checkout_request_id: str) -> str:
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, 'r') as f:
            statuses = json.load(f)
        return statuses.get(checkout_request_id, None)
    return None

def initiate_mpesa_payment(phone_number: str, amount: str) -> str:
    access_token = get_mpesa_access_token()
    if not access_token:
        logger.error("Failed to obtain MPESA access token.")
        return None

    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "BusinessShortCode": os.getenv("MPESA_SHORTCODE"),
        "Password": generate_password(),
        "Timestamp": get_timestamp(),
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": os.getenv("MPESA_SHORTCODE"),
        "PhoneNumber": phone_number,
        "CallBackURL": os.getenv("CALLBACK_URL"),
        "AccountReference": "Test123",
        "TransactionDesc": "Payment for goods"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            logger.info("Payment initiated successfully.")
            CheckoutRequestID = response.json().get('CheckoutRequestID')
            logger.info(f"CheckoutRequestID: {CheckoutRequestID}")

            payment_status_response = query_transaction_status(CheckoutRequestID)
            logger.info(f"Payment status response: {payment_status_response}")

            if payment_status_response.get('status') == 'success':
                transaction_status = payment_status_response.get('data')

                if transaction_status.get('ResultCode') == '0':
                    logger.info("Payment successful.")
                    return {
                        'id': CheckoutRequestID,
                        'status': 'success',
                        'message': 'Payment done',
                        'transaction_status': transaction_status
                    }
                else:
                    logger.error("Payment failed.")
                    return {
                        'id': CheckoutRequestID,
                        'status': 'error',
                        'message': transaction_status.get('ResultDesc'),
                    }
            else:
                logger.error("Failed to confirm payment status.")
                return {
                    'status': 'error',
                    'message': 'Failed to confirm payment status'
                }
        else:
            logger.error("Failed to initiate payment.")
            return {
                'status': 'error',
                'message': 'Failed to initiate payment'
            }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error initiating payment: {str(e)}")
        return {
            'status': 'error',
            'message': f"Error initiating payment: {str(e)}"
        }

def query_transaction_status(checkout_request_id):
    consumer_key = 'yrQq21AKgqZPZrFQmHBXB8AVHGcERaYOlSsjQdKEffzDdt20U'
    consumer_secret = 'rrhrucAwdGXie6ZIGPOhwO1ILa5PWIsyOhofvX7RCUSA64Zsjn0i4BGJAtZbMqKI'
    shortcode = '174379'
    passkey = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'
    api_base_url = 'https://sandbox.safaricom.co.ke'
    access_token_url = f'{api_base_url}/oauth/v1/generate?grant_type=client_credentials'
    query_transaction_url = f'{api_base_url}/mpesa/stkpushquery/v1/query'
    headers = {
        'Authorization': f'Basic clFxMjFBS2dxWlBackZRbUhCWEI4QVZIR2NFUmFZT2xTc2pRZEtFZmZ6RGR0MjBVOnJyaHJ1Y0F3ZEdYaWU2WklHUE9od08xSUxhNVBXSXN5T2hvZnZYN1JDVVNBNjRac2puMGk0QkdKQXRaYk1xS0k=',
        'Content-Type': 'application/json'
    }

    # Get access token
    try:
        response = requests.get(access_token_url, headers=headers)
        response.raise_for_status()
        logger.info("Access token fetched successfully.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching access token: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Error fetching access token: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Extract access token from response
    access_token = response.json().get('access_token')

    # Prepare payload for querying transaction status
    payload = {
        'BusinessShortCode': shortcode,
        'Password': generate_mpesa_password(shortcode, passkey),
        'Timestamp': time.strftime('%Y%m%d%H%M%S'),
        'CheckoutRequestID': checkout_request_id,
    }

    while True:
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            response = requests.post(query_transaction_url, json=payload, headers=headers)
            transaction_status = response.json()

            logger.info(f"Transaction status: {transaction_status}")

            if 'ResultCode' in transaction_status:
                return {
                    'status': 'success',
                    'data': transaction_status
                }
            elif transaction_status.get('errorCode') == '500.001.1001':
                logger.info("Transaction is being processed, retrying...")
                time.sleep(5)
            else:
                logger.error("Unexpected error, retrying...")
                time.sleep(5)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying transaction status: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error querying transaction status: {str(e)}'
            }


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

def generate_mpesa_password(shortcode, passkey):
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    data_to_encode = f"{shortcode}{passkey}{timestamp}"
    encoded_data = base64.b64encode(data_to_encode.encode('utf-8')).decode('utf-8')
    return encoded_data

def get_timestamp() -> str:
    from datetime import datetime
    return datetime.now().strftime('%Y%m%d%H%M%S')
