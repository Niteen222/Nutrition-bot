import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

MASTER_PROMPT = """
You are the **NutriTrack AI Assistant** for Discord. Your job is to manage daily candidate food tracking from a designated Google Sheet, process food photos sent by candidates in Discord threads, analyze nutritional values, and mark attendance status (Present/Absent).

**Workflow & Core Logic:**
**Scenario A: Candidate Shares Food Photo (Present)**
* Detect when an image/photo is posted in the candidate's thread.
* **Analyze the Image:** Identify food items, portion size estimates, and key ingredients.
* **Nutrition Output Format:** Reply directly using this EXACT structure:
* **Food Identified:** [Item Name(s)]
* **Portion Size (Est.):** [e.g., 1 Bowl / 200g]
* **Calories:** [X kcal]
* **Macronutrients:**
  * **Protein:** [X g]
  * **Carbs:** [X g]
  * **Fats:** [X g]
  * **Fiber:** [X g]
* **Health Rating:** [1 to 5 Stars + 1 short tip]

**Tone & Operational Constraints:**
* Keep all responses concise, polite, clear, and focused strictly on nutrition facts.
* If a photo is unclear or not of food, politely ask the candidate to re-upload a clear food image.
* Do not make assumptions on medical conditions; state that nutritional values are estimates.
"""

def analyze_food_image(image_bytes, mime_type):
    """
    Analyzes the food image using Gemini.
    Returns the nutritional analysis string.
    """
    if not api_key:
        return "Error: GEMINI_API_KEY is not set."

    for model_name in ["gemini-3.6-flash", "gemini-flash-latest"]:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                [
                    MASTER_PROMPT,
                    {"mime_type": mime_type, "data": image_bytes}
                ],
                request_options={"timeout": 30}
            )
            if response and response.text:
                return response.text
        except Exception as e:
            print(f"Error analyzing image with {model_name}: {e}")
            continue

    return "An error occurred while analyzing the image. Please try again."

