import uvicorn
import logging
import os
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from firebase_config import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Set up Jinja2 for rendering templates
templates = Jinja2Templates(directory="templates")  # Ensure you have a "templates" folder

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error. Please try again later."},
    )

@app.get("/", response_class=HTMLResponse)
async def serve_form(request: Request, user_id: str = Query(..., description="User ID for profile editing")):
    """Serves the profile editing form with user_id."""
    logger.info(f"Serving web form for user_id: {user_id}")
    
    return templates.TemplateResponse("web_form.html", {"request": request, "user_id": user_id})

@app.get("/get_user")
async def get_user(user_id: str = Query(..., description="User ID to fetch data")):
    """Fetches user data from Firestore."""
    logger.info(f"Fetching user data for user_id: {user_id}")
    
    try:
        doc = db.collection("users").document(user_id).get()
        if not doc.exists:
            logger.warning(f"User {user_id} not found.")
            return JSONResponse({"error": "User not found"}, status_code=404)

        return JSONResponse(doc.to_dict())
    
    except Exception as e:
        logger.error(f"Error fetching user data for {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching user data.")

@app.post("/update_user")
async def update_user(request: Request):
    """Updates user data in Firestore."""
    data = await request.json()
    user_id = data.get("user_id")

    if not user_id:
        logger.error("Missing user_id in request")
        return JSONResponse({"error": "Missing user_id"}, status_code=400)

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
    return JSONResponse({"status": "ok"})


