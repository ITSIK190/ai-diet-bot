import http.client
import json
from firebase_config import db  # Import Firestore instance

# Function to fetch BMI & Calories
def get_bmi_calories(weight_lbs, height_inches, user_id):
    conn = http.client.HTTPSConnection("smart-body-mass-index-calculator-bmi.p.rapidapi.com")

    headers = {
        'x-rapidapi-key': "41831ad208msha8b2dc059d7b761p159763jsn39bdfa480754",
        'x-rapidapi-host': "smart-body-mass-index-calculator-bmi.p.rapidapi.com"
    }

    endpoint = f"/api/BMI/imperial?lbs={weight_lbs}&inches={height_inches}"
    conn.request("GET", endpoint, headers=headers)

    res = conn.getresponse()
    data = json.loads(res.read().decode("utf-8"))

    if "bmi" in data and "calories_per_day" in data:
        bmi = data["bmi"]
        calories_per_day = data["calories_per_day"]

        # Save to Firebase
        user_ref = db.collection("users").document(user_id)
        user_ref.set({"bmi": bmi, "calories_per_day": calories_per_day}, merge=True)

        return f"Your BMI: {bmi}\nRecommended Calories: {calories_per_day} kcal/day"
    else:
        return "Error fetching data. Please try again."
