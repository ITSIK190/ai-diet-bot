from flask import Flask, request, jsonify
from google.cloud import firestore


app = Flask(__name__)
db = firestore.client()

@app.route("/get_user", methods=["GET"])
def get_user():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    user_doc = db.collection("users").document(user_id).get()
    if not user_doc.exists:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user_doc.to_dict())

@app.route("/update_user", methods=["POST"])
def update_user():
    data = request.json
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    db.collection("users").document(user_id).update({
        "weight_kg": float(data.get("weight_kg", 0)),
        "height_cm": float(data.get("height_cm", 0)),
        "age": int(data.get("age", 0)),
        "gender": data.get("gender", "male"),
        "activity": data.get("activity", "sedentary"),
        "goal": float(data.get("goal", 0))
    })

    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True)
