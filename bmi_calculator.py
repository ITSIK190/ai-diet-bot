import os
import http.client
import json
from firebase_config import db  # Import Firestore instance



def fetch_and_store_bmi(user_id, weight_kg, height_cm, age, gender, goal_weight):
    """Fetch BMI & daily calorie needs and store them in Firebase."""

    # Call the API
    conn = http.client.HTTPSConnection("smart-body-mass-index-calculator-bmi.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': os.getenv("rapidapi_key"),  # Replace with your actual API key
        'x-rapidapi-host': "smart-body-mass-index-calculator-bmi.p.rapidapi.com"
    }
    
    api_url = f"/api/BMI/metric?kg={weight_kg}&cm={height_cm}"
    conn.request("GET", api_url, headers=headers)
    res = conn.getresponse()
    data = json.loads(res.read().decode("utf-8"))

    if "bmi" not in data:
        raise ValueError("Invalid response from API: missing BMI")

    bmi = data["bmi"]
    calories_per_day = data.get("calories_needed", {}).get(str(goal_weight), None)  # Extract calories for goal weight

    # Save to Firebase
    user_ref = db.collection("users").document(user_id)
    user_ref.set({
        "bmi": bmi,
        "calories_per_day": calories_per_day,
        "weight_kg": weight_kg,
        "height_cm": height_cm,
        "goal_weight": goal_weight
    }, merge=True)

    return {"bmi": bmi, "calories_per_day": calories_per_day}
