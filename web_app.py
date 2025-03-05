from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from firebase_config import db  # Use db from firebase_config.py (already initialized)
import os

# FastAPI instance initialization
app = FastAPI()

# Path to your HTML form file
HTML_FILE = os.path.join(os.path.dirname(__file__), "web_form.html")

@app.get("/", response_class=FileResponse)
async def serve_form():
    """Serves the web form for user profile editing."""
    return FileResponse(HTML_FILE)

@app.get("/get_user")
async def get_user(user_id: str):
    """Fetches user data from Firestore."""
    doc = db.collection("users").document(user_id).get()
    if not doc.exists:
        return JSONResponse({"error": "User not found"}, status_code=404)
    return JSONResponse(doc.to_dict())

@app.post("/update_user")
async def update_user(request: Request):
    """Updates user data in Firestore."""
    data = await request.json()
    user_id = data.get("user_id")
    if not user_id:
        return JSONResponse({"error": "Missing user_id"}, status_code=400)

    db.collection("users").document(user_id).set(data, merge=True)
    return JSONResponse({"message": "Profile updated successfully"})
