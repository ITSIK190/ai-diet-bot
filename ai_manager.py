from firebase_config import db
import os
from huggingface_hub import InferenceClient

# 🔹 Hugging Face Model Configuration
HF_SPACE_NAME = "Itsik190/ai-diet-coach"
client = InferenceClient(model=HF_SPACE_NAME)

def truncate_text(text, max_words=30):
    """Truncate text to a maximum number of words."""
    words = text.split()
    return " ".join(words[:max_words]) + ("..." if len(words) > max_words else "")

def chat_with_ai(prompt):
    """Send user message to Hugging Face model and return response."""
    try:
        print(f"Sending to HF: {prompt}")  # Debug log

        response = client.text_generation(prompt)

        if not response or not response.strip():
            print("HF Response was empty or None")  
            return "I couldn't process your request. Please try again!"

        truncated_response = truncate_text(response.strip(), max_words=30)

        print(f"HF Response: {truncated_response}")  # Debug log
        return truncated_response

    except Exception as e:
        print(f"Error communicating with HF: {e}")
        return "Sorry, something went wrong! Please try again later."

async def generate_encouragement(user_id, user_name):
    """Generates a short AI-based encouragement message using stored user data."""
    user_ref = db.collection("users").document(user_id)
    user = user_ref.get()

    if not user.exists:
        return "I don’t have your details yet! Please log your weight with /logweight."

    user_data = user.to_dict()
    weight = user_data.get("weight")
    goal_weight = user_data.get("goal")

    # 🔹 Construct AI prompt based on available data
    if weight and goal_weight:
        prompt = f"Give {user_name} a short, highly motivating message. They currently weigh {weight} kg and their goal is {goal_weight} kg. Keep it under 20 words."
    elif weight:
        prompt = f"Give {user_name} a short, highly motivating message. They currently weigh {weight} kg. Keep it under 20 words."
    elif goal_weight:
        prompt = f"Give {user_name} a short, highly motivating message. Their goal is {goal_weight} kg. Keep it under 20 words."
    else:
        prompt = f"Give {user_name} a short, highly motivating message about staying healthy and fit. Keep it under 20 words."

    return chat_with_ai(prompt)
