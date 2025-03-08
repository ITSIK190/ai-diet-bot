from flask import Flask, request, jsonify
from google.cloud import firestore
import logging

# Initialize Flask app
app = Flask(__name__)

# Initialize Firestore client
db = firestore.client()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route("/get_user", methods=["GET"])
def get_user():
    user_id = request.args.get("user_id")
    if not user_id:
        logger.error("Missing user_id in request")
        return jsonify({"error": "Missing user_id"}), 400

    try:
        user_doc = db.collection("users").document(user_id).get()
        if not user_doc.exists:
            logger.warning(f"User with ID {user_id} not found")
            return jsonify({"error": "User not found"}), 404

        logger.info(f"User data retrieved successfully for user_id: {user_id}")
        return jsonify(user_doc.to_dict())
    except Exception as e:
        logger.error(f"Error fetching user data for user_id {user_id}: {e}", exc_info=True)
        return jsonify({"error": "Error fetching user data"}), 500

@app.route("/update_user", methods=["POST"])
def update_user():
    data = request.json
    user_id = data.get("user_id")

    if not user_id:
        logger.error("Missing user_id in request")
        return jsonify({"error": "Missing user_id"}), 400

    try:
        # Update user data
        db.collection("users").document(user_id).update({
            "weight_kg": float(data.get("weight_kg", 0)),
            "height_cm": float(data.get("height_cm", 0)),
            "age": int(data.get("age", 0)),
            "gender": data.get("gender", "male"),
            "activity": data.get("activity", "sedentary"),
            "goal": float(data.get("goal", 0))
        })

        logger.info(f"User data updated successfully for user_id: {user_id}")
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error updating user data for user_id {user_id}: {e}", exc_info=True)
        return jsonify({"error": "Error updating user data"}), 500

# if __name__ == "__main__":
#     logger.info("Starting Flask app...")
#     app.run(debug=True)
