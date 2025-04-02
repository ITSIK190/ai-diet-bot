import asyncio
import os
import datetime
import pytz  # Ensure this is installed: pip install pytz
from firebase_config import db
from huggingface_hub import InferenceClient
from gradio_client import Client
from hugchat import hugchat
from hugchat.login import Login



# Retrieve credentials from environment variables
EMAIL = os.getenv("hf_email")
PASSWORD = os.getenv("hf_pw")

# Define cookie storage directory
cookie_path_dir = "./cookies/"  # NOTE: trailing slash is required

# Ensure credentials are provided
if not EMAIL or not PASSWORD:
    raise ValueError("Hugging Face email and password must be set as environment variables!")

# Login and retrieve cookies
sign = Login(EMAIL, PASSWORD)
cookies = sign.login(cookie_dir_path=cookie_path_dir, save_cookies=True)

# Initialize HuggingChat with authenticated cookies
chatbot = hugchat.ChatBot(cookies=cookies.get_dict())

def chat_with_huggingchat(prompt: str) -> str:
    """Send a message to HuggingChat and return the response."""
    response = chatbot.chat(prompt).wait_until_done()
    return response





async def generate_huggingchat_response(user_id, prompt):
    """Generate a response using the HuggingChat API with user details."""
    try:
        # Fetch user data from Firestore
        user_doc = db.collection("users").document(user_id).get()
        user_data = user_doc.to_dict() or {}

        # Extract user details
        user_name = user_data.get("name", "Friend")
        diet_type = user_data.get("diet", "an unspecified diet")
        weight = user_data.get("weight", "unknown")
        goal_weight = user_data.get("goal", "not set")
        meals_per_day = user_data.get("meals_per_day", "unknown")

        # Handle fasting details
        fasting = user_data.get("fasting", False)
        eating_window = user_data.get("eating_window", {})
        fasting_start = eating_window.get("start", None)
        fasting_end = eating_window.get("stop", None)

        # Get current time in Israel Time (IST)
        israel_tz = pytz.timezone("Asia/Jerusalem")
        current_time = datetime.datetime.now(israel_tz).strftime("%H:%M")

        # 🔹 Build AI prompt context
        context = (
            f"You are {user_name}'s personal dietitian. "
            f"{user_name} follows a {diet_type} diet and weighs {weight} kg, aiming for {goal_weight} kg. "
            f"They eat {meals_per_day} meals per day. "
        )

        if fasting and fasting_start and fasting_end:
            context += f"They practice intermittent fasting from {fasting_start} to {fasting_end}. "

        context += (
            f"The time now in Israel is {current_time}. "
            f"Generate a personal motivation message (≤50 words) including their name, a diet detail, and **answering this prompt**: {prompt} "
            f"Ensure the response stays relevant to their diet goals and offers practical motivation."
        )

        full_prompt = context

        print(f"🔹 Sending to HuggingChat: {full_prompt}")  # Debug log

        # Call the HuggingChat API asynchronously
        response = await asyncio.to_thread(lambda: chatbot.chat(full_prompt).wait_until_done())

        if not response or not isinstance(response, str):
            print(f"⚠️ Invalid response type: {type(response)} - {response}")
            return "I couldn't process your request. Please try again!"

        clean_response = response.strip().replace("<|im_end|>", "").strip()

        print(f"✅ HuggingChat Response: {clean_response}")  # Debug log
        return clean_response

    except Exception as e:
        print(f"❌ Error communicating with HuggingChat: {e}")
        return "Sorry, something went wrong! Please try again later."






# Authenticate and save cookies
sign = Login(EMAIL, PASSWORD)
cookies = sign.login()
sign.saveCookiesToDir()

# 🔹 Hugging Face Configuration
HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
# HF_SPACE_NAME = "Itsik190/ai-diet-coach"
# client = Client(HF_SPACE_NAME)

def truncate_text(text, max_words=30):
    """Truncate text to a maximum number of words."""
    words = text.split()
    return " ".join(words[:max_words]) + ("..." if len(words) > max_words else "")


# async def chat_with_ai(prompt):
#     """Send user message to Hugging Face model and return response."""
#     try:
#         print(f"🔹 Sending to HF: {prompt}")  # Debug log
        
#         # Run the synchronous `predict()` method in a separate thread
#         response = await asyncio.to_thread(client.predict, prompt)

#         if not response or not isinstance(response, str):
#             print("⚠️ HF Response was invalid or empty.")  
#             return "I couldn't process your request. Please try again!"

#         truncated_response = truncate_text(response.strip(), max_words=30)

#         print(f"✅ HF Response: {truncated_response}")  # Debug log
#         return truncated_response

#     except Exception as e:
#         print(f"❌ Error communicating with HF: {e}")
#         return "Sorry, something went wrong! Please try again later."



# async def generate_encouragement(user_id, user_name):
#     """Generates a short AI-based encouragement message using stored user data."""
#     user_ref = db.collection("users").document(user_id)
#     user = user_ref.get()

#     if not user.exists:
#         return "I don’t have your details yet! Please log your weight with /logweight."

#     user_data = user.to_dict()
#     weight = user_data.get("weight")
#     goal_weight = user_data.get("goal")

#     # 🔹 Construct AI prompt based on available data
#     if weight and goal_weight:
#         prompt = f"Give {user_name} a short, highly motivating message. They currently weigh {weight} kg and their goal is {goal_weight} kg. Keep it under 20 words."
#     elif weight:
#         prompt = f"Give {user_name} a short, highly motivating message. They currently weigh {weight} kg. Keep it under 20 words."
#     elif goal_weight:
#         prompt = f"Give {user_name} a short, highly motivating message. Their goal is {goal_weight} kg. Keep it under 20 words."
#     else:
#         prompt = f"Give {user_name} a short, highly motivating message about staying healthy and fit. Keep it under 20 words."

#     return await chat_with_ai(prompt)



# # Initialize the new Hugging Face client
# chatgpt_client = Client("yuntian-deng/ChatGPT")

# async def generate_chatgpt_response(user_message):
#     """Generates a response using the yuntian-deng/ChatGPT Hugging Face model."""
#     try:
#         print(f"🔹 Sending to HF ChatGPT: {user_message}")  # Debug log

#         # Run the synchronous `predict()` method in a separate thread
#         response = await asyncio.to_thread(
#             chatgpt_client.predict,
#             user_message,  # inputs
#             1,  # top_p
#             1,  # temperature
#             0,  # chat_counter
#             [],  # chatbot (empty history)
#             api_name="/predict"
#         )

#         if not response or not isinstance(response, str):
#             print("⚠️ HF ChatGPT Response was invalid or empty.")  
#             return "I couldn't process your request. Please try again!"

#         truncated_response = truncate_text(response.strip(), max_words=30)

#         print(f"✅ HF ChatGPT Response: {truncated_response}")  # Debug log
#         return truncated_response

#     except Exception as e:
#         print(f"❌ Error communicating with HF ChatGPT: {e}")
#         return "Sorry, something went wrong! Please try again later."