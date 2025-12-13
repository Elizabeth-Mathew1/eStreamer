import google.generativeai as genai
import json

from web_server.settings import GEMINI_API_KEY

# --- 1. SETUP ---
# Make sure to set your API key in your environment variables or paste it here
# os.environ["GOOGLE_API_KEY"] = "YOUR_ACTUAL_API_KEY"
genai.configure(api_key=GEMINI_API_KEY)

# Use Flash for speed (low latency for live streams)
model = genai.GenerativeModel("gemini-2.5-flash-preview-09-2025")


def generate_prediction(history_window):
    """
    Takes a list of dictionary objects representing past chat minutes.
    Returns a JSON object with predictions and synthetic chat samples.
    """

    # --- 2. THE PROMPT ---
    # We explicitly ask for JSON format to ensure our app can parse it easily.
    prompt = f"""
    You are an AI Analyst for a high-speed YouTube Livestream.
    
    **Context:**
    Here is the aggregated data from the last 5 minutes of chat history.
    - 'volume': messages per minute.
    - 'sentiment': -1.0 (negative) to 1.0 (positive).
    - 'keywords': most common words used.

    **History Data:**
    {json.dumps(history_window, indent=2)}

    **Your Task:**
    1. Analyze the trajectory of the volume and sentiment.
    2. Predict the stats for the NEXT minute (Minute 0 / Now).
    3. **CRITICAL:** Generate 3 "Simulated Chat Messages" that represent exactly what users will likely say next, matching the predicted mood and keywords.
       - If sentiment is dropping, write angry/troll messages.
       - If sentiment is hype, write excited messages.
       - Use slang appropriate for Twitch/YouTube (e.g., "W stream", "L", "rip").

    **Response Format (JSON ONLY, no markdown):**
    {{
      "predicted_volume": <int>,
      "predicted_sentiment": <float>,
      "volatility_risk": "<LOW | MEDIUM | HIGH>",
      "simulated_chat_samples": ["<msg1>", "<msg2>", "<msg3>"],
      "reasoning": "<short explanation>"
    }}
    """

    try:
        # --- 3. CALL GEMINI ---
        response = model.generate_content(
            prompt, generation_config={"response_mime_type": "application/json"}
        )

        # Parse the JSON string back into a Python dictionary
        prediction_data = json.loads(response.text)
        return prediction_data

    except Exception as e:
        print(f"Error generating prediction: {e}")
        return None


# --- 4. RUNNING THE EXAMPLE ---

# Simulating data where a stream is crashing (High lag, angry users)
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
    print("\n--- FUTURE CHAT SAMPLES (What users will say next) ---")
    for msg in result["simulated_chat_samples"]:
        print(f"> {msg}")
