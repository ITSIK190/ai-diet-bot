import uvicorn
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from firebase_config import db
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Path to your HTML form file
HTML_FILE = os.path.join(os.path.dirname(__file__), "web_form.html")

# Global exception handler to catch unhandled errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error. Please try again later."},
    )

@app.get("/", response_class=FileResponse)
async def serve_form():
    """Serves the web form for user profile editing."""
    logger.info("Serving web form...")
    try:
        return FileResponse(HTML_FILE)
    except Exception as e:
        logger.error(f"Error serving the form: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error serving the form.")

@app.get("/get_user")
async def get_user(user_id: str):
    """Fetches user data from Firestore."""
    logger.info(f"Fetching user data for user_id: {user_id}")
    try:
        doc = db.collection("users").document(user_id).get()
        if not doc.exists:
            logger.warning(f"User with ID {user_id} not found.")
            return JSONResponse({"error": "User not found"}, status_code=404)
        logger.info("User data retrieved successfully")
        return JSONResponse(doc.to_dict())
    except Exception as e:
        logger.error(f"Error fetching user data for user_id {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching user data.")

@app.post("/update_user")
async def update_user(request: Request):
    """Updates user data in Firestore."""
    data = await request.json()
    user_id = data.get("user_id")
    if not user_id:
        logger.error("Missing user_id in request")
        return JSONResponse({"error": "Missing user_id"}, status_code=400)

    logger.info(f"Updating user data for user_id: {user_id}")
    try:
        db.collection("users").document(user_id).set(data, merge=True)
        logger.info(f"User data for {user_id} updated successfully")
        return JSONResponse({"message": "Profile updated successfully"})
    except Exception as e:
        logger.error(f"Error updating user data for {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating user data.")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.info("Health check requested.")
    return JSONResponse({"status": "ok"})

# # Ensure app runs on the correct port
# if __name__ == "__main__":
#     logger.info("Starting FastAPI app on port 8080...")
#     uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
