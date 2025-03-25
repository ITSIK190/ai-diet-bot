import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import logging
import uvicorn
from firebase_config import db  # Keep Firestore logic

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
templates = Jinja2Templates(directory="templates")  # Ensure you have a "templates" folder

@app.get("/", response_class=HTMLResponse)
async def serve_form(request: Request, user_id: str = None):
    logger.info(f"Serving web form for user_id: {user_id}")

    if not user_id:
        logger.error("User ID is missing in request")
        return HTMLResponse(content="<h1>Error: Missing user_id</h1>", status_code=400)

    try:
        html_file = os.path.join(os.path.dirname(__file__), "web_form.html")
        
        if not os.path.exists(html_file):  # Check if file exists
            logger.error("web_form.html not found")
            return HTMLResponse(content="<h1>Error: web_form.html not found</h1>", status_code=500)

        with open(html_file, "r", encoding="utf-8") as file:
            html_content = file.read().replace("USER_ID_PLACEHOLDER", user_id)

        return HTMLResponse(content=html_content, status_code=200)
    
    except Exception as e:
        logger.error(f"Error serving the form: {e}", exc_info=True)
        return HTMLResponse(content="<h1>Internal Server Error</h1>", status_code=500)


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

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})


@app.get("/mini_app", response_class=HTMLResponse)
async def serve_mini_app(request: Request, user_id: str = None):
    logger.info(f"Serving Mini App for user_id: {user_id}")

    if not user_id:
        return HTMLResponse(content="<h1>Error: Missing user_id</h1>", status_code=400)

    try:
        html_file = os.path.join(os.path.dirname(__file__), "web_form.html")

        if not os.path.exists(html_file):  
            return HTMLResponse(content="<h1>Error: web_form.html not found</h1>", status_code=500)

        with open(html_file, "r", encoding="utf-8") as file:
            html_content = file.read().replace("USER_ID_PLACEHOLDER", user_id)

        return HTMLResponse(content=html_content, status_code=200)

    except Exception as e:
        logger.error(f"Error serving Mini App: {e}", exc_info=True)
        return HTMLResponse(content="<h1>Internal Server Error</h1>", status_code=500)


# Run FastAPI in Railway (single service, one port)
# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
