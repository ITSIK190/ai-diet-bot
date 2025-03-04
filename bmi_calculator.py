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


def calculate_tdee(weight_kg, height_cm, age, gender, activity_level):
    """Calculates TDEE based on BMR and activity level."""
    if gender.lower() == "male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    # Activity multipliers
    activity_multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very active": 1.9
    }
    
    tdee = bmr * activity_multipliers.get(activity_level, 1.2)  # Default to sedentary
    return tdee

def calculate_goal_calories(weight_kg, height_cm, age, gender, activity_level, goal_weight_kg):
    """Calculates daily calories required to reach target weight."""
    current_tdee = calculate_tdee(weight_kg, height_cm, age, gender, activity_level)
    weight_difference = goal_weight_kg - weight_kg
    weekly_weight_change = weight_difference / 8  # Aim for goal in ~2 months
    calorie_adjustment = weekly_weight_change * 1100  # 1100 kcal per 0.5 kg per week

    target_calories = current_tdee + calorie_adjustment
    return round(target_calories, 2)

