import os
import json
import base64
import asyncio
from google.cloud import firestore
from google.api_core.exceptions import DeadlineExceeded
import firebase_admin
from firebase_admin import credentials

# Load Firebase credentials from Base64 environment variable
firebase_credentials_b64 = os.getenv("FIREBASE_CREDENTIALS")

if not firebase_credentials_b64:
    raise ValueError("FIREBASE_CREDENTIALS is not set or invalid.")

try:
    firebase_credentials_json = base64.b64decode(firebase_credentials_b64).decode("utf-8")
    firebase_credentials = json.loads(firebase_credentials_json)

    # Initialize Firebase only if not already initialized
    if not firebase_admin._apps:
        cred = credentials.Certificate(firebase_credentials)
        firebase_admin.initialize_app(cred)

    db = firestore.client()

except Exception as e:
    raise RuntimeError(f"Failed to initialize Firebase: {e}")

async def get_users_with_retry(limit=100, retries=3, delay=5):
    """
    Fetch users from Firestore with automatic retry on timeouts.
    - limit: Max number of users to fetch per request
    - retries: Number of retry attempts in case of failure
    - delay: Seconds to wait before retrying
    """
    for attempt in range(retries):
        try:
            users = db.collection("users").limit(limit).stream()
            return [user for user in users]  # Convert Firestore stream to list
        except DeadlineExceeded:
            print(f"Firestore query timeout (Attempt {attempt + 1}/{retries}). Retrying in {delay} seconds...")
            await asyncio.sleep(delay)
    
    print("Failed to fetch users after multiple attempts.")
    return []  # Return empty list if all retries fail
