import uvicorn
import logging
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from firebase_config import db
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Path to your HTML form file
HTML_FILE = os.path.join(os.path.dirname(__file__), "web_form.html")

@app.get("/", response_class=FileResponse)
async def serve_form():
    """Serves the web form for user profile editing."""
    logger.info("Serving web form...")
    return FileResponse(HTML_FILE)

@app.get("/get_user")
async def get_user(user_id: str):
    """Fetches user data from Firestore."""
    logger.info(f"Fetching user data for user_id: {user_id}")
    doc = db.collection("users").document(user_id).get()
    if not doc.exists:
        logger.warning("User not found")
        return JSONResponse({"error": "User not found"}, status_code=404)
    logger.info("User data retrieved successfully")
    return JSONResponse(doc.to_dict())

@app.post("/update_user")
async def update_user(request: Request):
    """Updates user data in Firestore."""
    data = await request.json()
    user_id = data.get("user_id")
    if not user_id:
        logger.error("Missing user_id in request")
        return JSONResponse({"error": "Missing user_id"}, status_code=400)

    logger.info(f"Updating user data for user_id: {user_id}")
    db.collection("users").document(user_id).set(data, merge=True)
    logger.info("Profile updated successfully")
    return JSONResponse({"message": "Profile updated successfully"})

@app.get("/health")
async def health_check():
    return JSONResponse({"status": "ok"})

# Ensure app runs on the correct port
if __name__ == "__main__":
    logger.info("Starting FastAPI app on port 8080...")
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")

