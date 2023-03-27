import requests
import os
import asyncio
from dotenv import load_dotenv

# Load Coinbase Commerce API key from .env file
load_dotenv()
API_KEY = os.getenv("CB_TOKEN")

# Coinbase Commerce API used to accept payments using request to its rest API


class Payment:
    """
    Various aspects of the payment process are handled by this class.
    invoice() is used to create an invoice for the user to pay.
    - Name is name of the customer
    - Email is the email id of the customer.
    - Price is the invoice amount
    - Denomination is the amount of the invoice
    - desc is the the memo.
    check() is used to check if the invoice has been paid or is pending.
    requests are made to these methods using other functions in the app.
    """
    def invoice(name: str, email: str, price: float, denomination: str , desc: str) -> dict:
        # URL for Coinbase Commerce API
        url = 'https://api.commerce.coinbase.com/invoices'

        # Headers required by Coinbase Commerce API
        headers = {
            'X-CC-Api-Key': API_KEY,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-CC-Version': '2018-03-22'
        }

        # Body for the POST request to API
        body = {
            "customer_name": name,
            "customer_email": email,
            "memo": desc,
            "local_price": {
                "amount": price,
                "currency": denomination
            }
        }

        # POST request to Coinbase Commerce API, with try/except block to catch errors
        try:
            # Making the request
            response = requests.post(url, headers=headers, json=body)

            # Getting the invoice URL, ID and Code from the response
            invoice_url = (response.json())["data"]["hosted_url"]
            id = (response.json())["data"]["id"]
            code = (response.json())["data"]["code"]

            # print("Response: ", response.content)
            print(invoice_url, id)
            return {"url": invoice_url, "id": id, "code": code}
        except Exception as e:
            print(e)

    # Method to check if an invoice has been paid or is pending, using Coinbase Commerce API
    def check(id: str) -> str:
        # Invoice ID in the callback URL
        url = 'https://api.commerce.coinbase.com/invoices/' + id

        # Headers required by Coinbase Commerce API
        headers = {
            'X-CC-Api-Key': API_KEY,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-CC-Version': '2018-03-22'
        }

        # Get request to Coinbase Commerce API
        response = requests.get(url, headers=headers)
        # print("Response: ", response.content)

        # Get transaction status
        status = response.json()["data"]["status"]
        print("\nTransaction status: ", status)
        return status


