# scripts/daraja_c2b_register_production.py
import os
import sys
import json
import requests
from requests.auth import HTTPBasicAuth

# ----------------------------
# CONFIG (from environment)
# ----------------------------
BASE_URL = os.getenv("MPESA_BASE_URL", "https://api.safaricom.co.ke").rstrip("/")
CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")

SHORTCODE = os.getenv("MPESA_SHORTCODE")  # e.g. 4003047
RESPONSE_TYPE = os.getenv("MPESA_RESPONSE_TYPE", "Completed")

CONFIRMATION_URL = os.getenv("MPESA_CONFIRMATION_URL")
VALIDATION_URL = os.getenv("MPESA_VALIDATION_URL")

TIMEOUT = int(os.getenv("MPESA_TIMEOUT", "30"))

def require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        print(f"[ERROR] Missing env var: {name}")
        sys.exit(1)
    return val

def get_access_token() -> str:
    require_env("MPESA_CONSUMER_KEY")
    require_env("MPESA_CONSUMER_SECRET")

    url = f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(url, auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET), timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"No access_token in response: {data}")
    return token

def check_url_reachable(url: str) -> bool:
    """
    Optional: check that your endpoint is reachable from the public internet.
    We'll try GET. If your endpoint only accepts POST, it may return 405 — that's OK.
    """
    try:
        r = requests.get(url, timeout=10, allow_redirects=True)
        # 200, 301/302, 405 are all "reachable" signals
        return r.status_code in (200, 301, 302, 405)
    except requests.RequestException:
        return False

def register_c2b_urls(access_token: str):
    require_env("MPESA_SHORTCODE")
    require_env("MPESA_CONFIRMATION_URL")
    require_env("MPESA_VALIDATION_URL")

    # Daraja C2B register URL endpoint
    endpoint = f"{BASE_URL}/mpesa/c2b/v1/registerurl"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "ShortCode": str(SHORTCODE),
        "ResponseType": RESPONSE_TYPE,
        "ConfirmationURL": CONFIRMATION_URL,
        "ValidationURL": VALIDATION_URL,
    }

    r = requests.post(endpoint, json=payload, headers=headers, timeout=TIMEOUT)

    print("\n=== REGISTER C2B URLs (PRODUCTION) ===")
    print("POST:", endpoint)
    print("Payload:", json.dumps(payload, ensure_ascii=False))
    print("Status:", r.status_code)
    print("Body:", r.text)

    r.raise_for_status()
    return r.json() if r.text else {}

if __name__ == "__main__":
    # Quick safety check: avoid accidentally running against sandbox
    if "sandbox" in BASE_URL:
        print("[ERROR] BASE_URL looks like sandbox. Use https://api.safaricom.co.ke for production.")
        sys.exit(1)

    print("BASE_URL:", BASE_URL)
    print("SHORTCODE:", SHORTCODE)
    print("CONFIRMATION_URL:", CONFIRMATION_URL)
    print("VALIDATION_URL:", VALIDATION_URL)

    # Optional reachability checks
    if CONFIRMATION_URL and not check_url_reachable(CONFIRMATION_URL):
        print("[WARN] ConfirmationURL not reachable via GET from here (could still be OK if POST-only).")
    if VALIDATION_URL and not check_url_reachable(VALIDATION_URL):
        print("[WARN] ValidationURL not reachable via GET from here (could still be OK if POST-only).")

    token = get_access_token()
    print("\nAccess token acquired ✅")

    result = register_c2b_urls(token)
    print("\nRegister success ✅")
    print("Response JSON:", json.dumps(result, indent=2))
