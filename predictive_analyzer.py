import google.generativeai as genai
import json
from web_server.settings import GEMINI_API_KEY

# --- 1. SETUP ---
genai.configure(api_key=GEMINI_API_KEY)

# --- 2. DEFINE THE SCHEMA (The Structure) ---
# This tells the model EXACTLY what JSON fields to return.
# We define this once, outside the function.
prediction_schema = {
    "type": "OBJECT",
    "properties": {
        "predicted_volume": {"type": "INTEGER"},
        "predicted_sentiment": {"type": "NUMBER"},
        "volatility_risk": {
            "type": "STRING",
            "enum": ["LOW", "MEDIUM", "HIGH"],  # Enforce specific values
        },
        "simulated_chat_samples": {"type": "ARRAY", "items": {"type": "STRING"}},
        "reasoning": {"type": "STRING"},
    },
    "required": [
        "predicted_volume",
        "predicted_sentiment",
        "volatility_risk",
        "simulated_chat_samples",
        "reasoning",
    ],
}

# --- 3. DEFINE THE SYSTEM PROMPT (The Persona) ---
# This sets the behavior. It is passed to the model on initialization.

system_instruction = """
You are an AI Analyst for a high-speed YouTube Livestream.

Your Task:
1. Analyze the trajectory of the provided message volume and sentiment data.
2. Predict the stats for the NEXT minute (Minute 0 / Now).
3. Generate 3 "Simulated Chat Messages" that represent exactly what users will likely say next.
   - If sentiment is dropping, write angry/troll messages.
   - If sentiment is hype, write excited messages.
   - Use slang appropriate for Twitch/YouTube (e.g., "W stream", "L", "rip").
"""

# Initialize the model with the system instruction
# Note: Ensure you use a model that supports system_instruction and response_schema (Gemini 1.5 Pro/Flash)
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash-preview-09-2025",  # Use a standard valid model name
    system_instruction=system_instruction,
)


def generate_prediction(history_window):
    """
    Takes history data, sends it to Gemini, and returns structured JSON.
    """

    # --- 4. THE USER QUERY (The Data) ---
    # We only send the data here. No instructions needed.
    user_query = json.dumps(history_window)

    try:
        payload = {
            "contents": [{"parts": [{"text": user_query}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": prediction_schema,
            },
        }

        # --- Call Gemini using payload ---
        response = model.generate_content(
            contents=payload["contents"],
            generation_config=genai.GenerationConfig(
                response_mime_type=payload["generationConfig"]["responseMimeType"],
                response_schema=payload["generationConfig"]["responseSchema"],
            ),
        )

        # Parse the JSON string back into a Python dictionary
        prediction_data = json.loads(response.text)
        return prediction_data

    except Exception as e:
        print(f"Error generating prediction: {e}")
        return None


# --- 6. RUNNING THE EXAMPLE ---
sample_history = [
    {
        "minute_offset": -5,
        "volume": 120,
        "sentiment": 0.8,
        "keywords": "hello, hype, start",
    },
    {
        "minute_offset": -4,
        "volume": 150,
        "sentiment": 0.9,
        "keywords": "wow, cool, graphics",
    },
    {
        "minute_offset": -3,
        "volume": 300,
        "sentiment": 0.4,
        "keywords": "lag, buffering, fix",
    },
    {"minute_offset": -2, "volume": 450, "sentiment": -0.5, "keywords": "F, rip, fail"},
    {
        "minute_offset": -1,
        "volume": 600,
        "sentiment": -0.8,
        "keywords": "refund, scam, trash",
    },
]

print("Analyzing Chat History...")
result = generate_prediction(sample_history)

if result:
    print("\n--- PREDICTION RESULT ---")
    print(f"Predicted Volume: {result['predicted_volume']}")
    print(f"Predicted Sentiment: {result['predicted_sentiment']}")
    print(f"Risk Level: {result['volatility_risk']}")
    print(f"Reasoning: {result['reasoning']}")
    print("\n--- FUTURE CHAT SAMPLES ---")
    for msg in result["simulated_chat_samples"]:
        print(f"> {msg}")
