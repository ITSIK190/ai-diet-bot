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
        logger.error("Missing user_id in request")
        return HTMLResponse(content="<h1>Error: Missing user_id</h1>", status_code=400)

    logger.info(f"Fetching data for user_id: {user_id}")

    try:
        user_doc = db.collection("users").document(user_id).get()
        user_data = user_doc.to_dict()

        if not user_data:
            logger.warning(f"User {user_id} not found in Firestore.")
            return HTMLResponse(content="<h1>Error: User not found</h1>", status_code=404)

        logger.info(f"User data retrieved: {user_data}")
  
        # Prepare data to populate the form
        user_name = user_data.get("name") if user_data.get("name") else "USER_NAME_PLACEHOLDER"
        diet_type = user_data.get("diet") if user_data.get("diet") else "DIET_TYPE_PLACEHOLDER"
        weight = str(user_data.get("weight")) if user_data.get("weight") else "WEIGHT_PLACEHOLDER"
        goal_weight = str(user_data.get("goal")) if user_data.get("goal") else "GOAL_WEIGHT_PLACEHOLDER"
        meals_per_day = str(user_data.get("meals_per_day")) if user_data.get("meals_per_day") else "MEALS_PER_DAY_PLACEHOLDER"
        fasting_start = user_data.get("eating_window", {}).get("start") if user_data.get("eating_window", {}).get("start") else "FASTING_START_PLACEHOLDER"
        fasting_end = user_data.get("eating_window", {}).get("stop") if user_data.get("eating_window", {}).get("stop") else "FASTING_END_PLACEHOLDER"
        # New fields
        gender = user_data.get("gender", "")  # Default: blank
        height = user_data.get("height", "")  # Default: blank
        exercise_level = user_data.get("exercise_level", "")  # Default: blank
        

        # Define the path to the HTML file (located in the root directory)
        html_file_path = os.path.join(os.path.dirname(__file__), "web_form.html")

        if not os.path.exists(html_file_path):
            return HTMLResponse(content="<h1>Error: web_form.html not found</h1>", status_code=500)

        # Read the HTML file and replace the placeholders with user data
        with open(html_file_path, "r", encoding="utf-8") as file:
            html_content = file.read()

        html_content = html_content.replace("{{ user_id }}", user_id if user_id else "")
        html_content = html_content.replace("{{ user_name }}", user_name if user_name else "")
        html_content = html_content.replace("{{ diet_type }}", diet_type if diet_type else "")
        html_content = html_content.replace("{{ weight }}", str(weight) if weight else "")
        html_content = html_content.replace("{{ goal_weight }}", str(goal_weight) if goal_weight else "")
        html_content = html_content.replace("{{ meals_per_day }}", str(meals_per_day) if meals_per_day else "")
        html_content = html_content.replace("{{ fasting_start }}", fasting_start if fasting_start else "")
        html_content = html_content.replace("{{ fasting_end }}", fasting_end if fasting_end else "")
        
        html_content = html_content.replace("{{ gender }}", gender if gender else "")
        html_content = html_content.replace("{{ height }}", str(height) if height else "")
        html_content = html_content.replace("{{ exercise_level }}", exercise_level if exercise_level else "")

        return HTMLResponse(content=html_content, status_code=200)

    except Exception as e:
        logger.error(f"Error serving Mini App: {e}", exc_info=True)
        return HTMLResponse(content="<h1>Internal Server Error</h1>", status_code=500)

# Route to handle form submission (updating user data)
@app.post("/update_user")
async def update_user(request: Request):
    data = await request.json()  # ✅ Accept JSON instead of form data
    user_id = data.get("user_id")

    if not user_id:
        return JSONResponse({"error": "Missing user_id"}, status_code=400)

    # Update the Firestore document
    db.collection("users").document(user_id).set(data, merge=True)

    return JSONResponse({"message": "Profile updated successfully"})


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})
