# prediction_analyzer/utils/auth.py
"""
Authentication utilities for API access
"""
import requests
from eth_account import Account
from eth_account.messages import encode_defunct
from ..config import API_BASE_URL

def get_signing_message():
    """
    Fetch the signing message from the API

    Returns:
        Signing message string or None on error
    """
    try:
        resp = requests.get(f"{API_BASE_URL}/auth/signing-message", timeout=10)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"❌ Error getting signing message: {e}")
        return None

def authenticate(private_key: str, signing_message: str):
    """
    Authenticate with the API using private key

    Args:
        private_key: Ethereum private key (with or without 0x prefix)
        signing_message: Message to sign from get_signing_message()

    Returns:
        Tuple of (session_cookie, address) or (None, None) on failure
    """
    if not private_key.startswith("0x"):
        private_key = "0x" + private_key

    try:
        account = Account.from_key(private_key)
        address = account.address

        # Sign the message
        message = encode_defunct(text=signing_message)
        signed = account.sign_message(message)

        sig_hex = signed.signature.hex()
        if not sig_hex.startswith("0x"):
            sig_hex = "0x" + sig_hex

        hex_message = "0x" + signing_message.encode('utf-8').hex()

        # Prepare headers
        headers = {
            'x-account': address,
            'x-signing-message': hex_message,
            'x-signature': sig_hex,
            'Content-Type': 'application/json',
        }

        # Authenticate
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            headers=headers,
            json={"client": "eoa"}
        )
        response.raise_for_status()

        session_cookie = response.cookies.get('limitless_session')
        return session_cookie, address

    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return None, None
