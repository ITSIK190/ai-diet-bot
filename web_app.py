import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import logging
from firebase_config import db  # Firebase Firestore logic

# Initialize FastAPI app
app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Route to serve the profile form
@app.get("/mini_app", response_class=HTMLResponse)
async def serve_mini_app(request: Request, user_id: str = None):
    if not user_id:
        return HTMLResponse(content="<h1>Error: Missing user_id</h1>", status_code=400)

    try:
        # Fetch user data from Firestore
        user_doc = db.collection("users").document(user_id).get()
        user_data = user_doc.to_dict()

        if not user_data:
            return HTMLResponse(content="<h1>Error: User not found</h1>", status_code=404)

        # Prepare data to populate the form
        user_name = user_data.get("name", "")
        diet_type = user_data.get("diet", "")
        weight = user_data.get("weight", "")
        goal_weight = user_data.get("goal", "")
        meals_per_day = user_data.get("meals_per_day", "")
        fasting_start = user_data.get("eating_window", {}).get("start", "")
        fasting_end = user_data.get("eating_window", {}).get("stop", "")

        # Define the path to the HTML file (located in the root directory)
        html_file_path = os.path.join(os.path.dirname(__file__), "web_form.html")

        if not os.path.exists(html_file_path):
            return HTMLResponse(content="<h1>Error: web_form.html not found</h1>", status_code=500)

        # Read the HTML file and replace the placeholders with user data
        with open(html_file_path, "r", encoding="utf-8") as file:
            html_content = file.read().replace("USER_ID_PLACEHOLDER", user_id) \
                                       .replace("USER_NAME_PLACEHOLDER", user_name) \
                                       .replace("DIET_TYPE_PLACEHOLDER", diet_type) \
                                       .replace("WEIGHT_PLACEHOLDER", str(weight)) \
                                       .replace("GOAL_WEIGHT_PLACEHOLDER", str(goal_weight)) \
                                       .replace("MEALS_PER_DAY_PLACEHOLDER", str(meals_per_day)) \
                                       .replace("FASTING_START_PLACEHOLDER", fasting_start) \
                                       .replace("FASTING_END_PLACEHOLDER", fasting_end)

        return HTMLResponse(content=html_content, status_code=200)

    except Exception as e:
        logger.error(f"Error serving Mini App: {e}", exc_info=True)
        return HTMLResponse(content="<h1>Internal Server Error</h1>", status_code=500)

# Route to handle form submission (updating user data)
@app.post("/update_user")
async def update_user(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    if not user_id:
        return JSONResponse({"error": "Missing user_id"}, status_code=400)

    # Update data in Firestore
    db.collection("users").document(user_id).set(data, merge=True)

    return JSONResponse({"message": "Profile updated successfully"})

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})
