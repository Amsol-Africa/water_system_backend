# scripts/daraja_c2b_setup.py
from wsgiref import headers
import requests
from requests.auth import HTTPBasicAuth

CONSUMER_KEY = "VGCt4R27tIhvvJPa8lMTZz7GNG9p5Tw3eGUxaP4I4AdMWoOj"
CONSUMER_SECRET = "tRvwFAFNERk5eSi6QvlKr25cMZLxlVHd9EI1beFFowPkHjS8SfvOSBGKqstYGx6M"
BASE_URL = "https://sandbox.safaricom.co.ke"

def get_access_token():
    resp = requests.get(
        f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
        auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET),
    )
    resp.raise_for_status()
    data = resp.json()
    print("OAuth token response:", data)
    return data["access_token"]

BASE_URL = "https://sandbox.safaricom.co.ke"

def register_c2b_urls(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    confirmation_url = "https://unsurrendered-duskily-linnie.ngrok-free.dev/api/payments/webhooks/c2b/"
    validation_url   = "https://unsurrendered-duskily-linnie.ngrok-free.dev/api/payments/webhooks/c2b/"

    payload = {
        "ShortCode": "600999",
        "ResponseType": "Completed",
        "ConfirmationURL": confirmation_url,
        "ValidationURL": validation_url,
    }

    resp = requests.post(
        f"{BASE_URL}/mpesa/c2b/v1/registerurl",
        json=payload,
        headers=headers,
        timeout=30,
    )
    print("RegisterURL status:", resp.status_code)
    print("RegisterURL body:", resp.text)
    resp.raise_for_status()

    
def simulate_c2b_payment(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "ShortCode": "600999",
        "CommandID": "CustomerPayBillOnline",
        "Amount": 300,
        "Msisdn": "254708374149",
        "BillRefNumber": "58000185726",  # your meter_id
    }

    resp = requests.post(
        f"{BASE_URL}/mpesa/c2b/v1/simulate",   # NOTE: sandbox + /c2b/v1/simulate
        json=payload,
        headers=headers,
        timeout=30,
    )
    print("Simulate status:", resp.status_code)
    print("Simulate body:", resp.text)
    resp.raise_for_status()
    

if __name__ == "__main__":
    token = get_access_token()
    register_c2b_urls(token)
    simulate_c2b_payment(token)
