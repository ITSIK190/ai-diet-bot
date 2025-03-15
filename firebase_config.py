import os
import json
import base64
import asyncio
from google.cloud import firestore
from google.api_core.exceptions import DeadlineExceeded
import firebase_admin
from firebase_admin import credentials

# Decode Base64 Firebase credentials and save to a temporary file
firebase_credentials_b64 = os.getenv("FIREBASE_CREDENTIALS")
if not firebase_credentials_b64:
    raise ValueError("FIREBASE_CREDENTIALS is not set or invalid.")

firebase_json_path = "/tmp/firebase_creds.json"  # Save credentials in a temp file
try:
    firebase_credentials_json = base64.b64decode(firebase_credentials_b64).decode("utf-8")
    with open(firebase_json_path, "w") as f:
        f.write(firebase_credentials_json)

    # 🔹 Set the environment variable BEFORE initializing Firestore
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = firebase_json_path  

    # Initialize Firebase Admin SDK
    if not firebase_admin._apps:
        cred = credentials.Certificate(firebase_json_path)
        firebase_admin.initialize_app(cred)

    # 🔥 Explicitly pass credentials to Firestore
    db = firestore.Client()

    print("✅ Firebase initialized successfully.")

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
