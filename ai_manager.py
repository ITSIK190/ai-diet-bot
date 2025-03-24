import asyncio
import os
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
    """Generate a response using the HuggingChat API with user-specific context."""
    try:
        # 🔹 Fetch user data from Firestore
        user_doc = db.collection("users").document(user_id).get()
        if not user_doc.exists:
            print(f"⚠️ No user data found for {user_id}.")
            return "I couldn't retrieve your details. Please set up your profile first."

        user_data = user_doc.to_dict() or {}
        user_name = user_data.get("name", "Friend")
        weight = user_data.get("weight", "unknown")
        height = user_data.get("height", "unknown")
        diet = user_data.get("diet", "not specified")
        goal_weight = user_data.get("goal_weight", "not set")

        # 🔹 Construct a more informative prompt for the AI
        context = (
            f"You are {user_name}'s personal dietitian. "
            f"{user_name} follows a {diet} diet. "
            f"Their current weight is {weight} kg, and their height is {height} cm. "
            f"Their goal is to reach {goal_weight} kg. "
            f"Now respond to the following request: {prompt}"
        )

        print(f"🔹 Sending to HuggingChat: {context}")  # Debug log

        # 🔹 Call the HuggingChat API asynchronously
        response = await asyncio.to_thread(chatbot.chat, context)

        if not response or not isinstance(response, str):
            print("⚠️ HuggingChat Response was invalid or empty.")
            return "I couldn't process your request. Please try again!"

        print(f"✅ HuggingChat Response: {response.strip()}")  # Debug log
        return response.strip()

    except Exception as e:
        print(f"❌ Error communicating with HuggingChat: {e}")
        return "Sorry, something went wrong! Please try again later."



# Authenticate and save cookies
sign = Login(EMAIL, PASSWORD)
cookies = sign.login()
sign.saveCookiesToDir()

# 🔹 Hugging Face Configuration
HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
HF_SPACE_NAME = "Itsik190/ai-diet-coach"
client = Client(HF_SPACE_NAME)

def truncate_text(text, max_words=30):
    """Truncate text to a maximum number of words."""
    words = text.split()
    return " ".join(words[:max_words]) + ("..." if len(words) > max_words else "")


async def chat_with_ai(prompt):
    """Send user message to Hugging Face model and return response."""
    try:
        print(f"🔹 Sending to HF: {prompt}")  # Debug log
        
        # Run the synchronous `predict()` method in a separate thread
        response = await asyncio.to_thread(client.predict, prompt)

        if not response or not isinstance(response, str):
            print("⚠️ HF Response was invalid or empty.")  
            return "I couldn't process your request. Please try again!"

        truncated_response = truncate_text(response.strip(), max_words=30)

        print(f"✅ HF Response: {truncated_response}")  # Debug log
        return truncated_response

    except Exception as e:
        print(f"❌ Error communicating with HF: {e}")
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

    return await chat_with_ai(prompt)



# Initialize the new Hugging Face client
chatgpt_client = Client("yuntian-deng/ChatGPT")

async def generate_chatgpt_response(user_message):
    """Generates a response using the yuntian-deng/ChatGPT Hugging Face model."""
    try:
        print(f"🔹 Sending to HF ChatGPT: {user_message}")  # Debug log

        # Run the synchronous `predict()` method in a separate thread
        response = await asyncio.to_thread(
            chatgpt_client.predict,
            user_message,  # inputs
            1,  # top_p
            1,  # temperature
            0,  # chat_counter
            [],  # chatbot (empty history)
            api_name="/predict"
        )

        if not response or not isinstance(response, str):
            print("⚠️ HF ChatGPT Response was invalid or empty.")  
            return "I couldn't process your request. Please try again!"

        truncated_response = truncate_text(response.strip(), max_words=30)

        print(f"✅ HF ChatGPT Response: {truncated_response}")  # Debug log
        return truncated_response

    except Exception as e:
        print(f"❌ Error communicating with HF ChatGPT: {e}")
        return "Sorry, something went wrong! Please try again later."