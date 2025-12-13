from typing import Any
import google.generativeai as genai
import json
from settings import GEMINI_API_KEY


class PredictionController:
    def __init__(self) -> None:
        genai.configure(api_key=GEMINI_API_KEY)

        self.prediction_schema = {
            "type": "OBJECT",
            "properties": {
                "predicted_volume": {"type": "INTEGER"},
                "predicted_sentiment": {"type": "NUMBER"},
                "volatility_risk": {
                    "type": "STRING",
                    "enum": ["LOW", "MEDIUM", "HIGH"],
                },
                "simulated_chat_samples": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                },
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

        self.system_instruction = """
        You are an AI Analyst for a high-speed YouTube Livestream.

        Your Task:
        1. Analyze the trajectory of the provided message volume and sentiment data.
        2. Predict the stats for the NEXT minute (Minute 0 / Now).
        3. Generate 3 "Simulated Chat Messages" that represent exactly what users will likely say next.
        - If sentiment is dropping, write angry/troll messages.
        - If sentiment is hype, write excited messages.
        - Use slang appropriate for Twitch/YouTube (e.g., "W stream", "L", "rip").
        """

        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-preview-09-2025",
            system_instruction=self.system_instruction,
        )

    def generate_prediction(self, history_window) -> dict[str, Any] | None:
        """
        Takes history data, sends it to Gemini, and returns structured JSON.
        """

        user_query = json.dumps(history_window)

        try:
            payload = {
                "contents": [{"parts": [{"text": user_query}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseSchema": self.prediction_schema,
                },
            }

            response = self.model.generate_content(
                contents=payload["contents"],
                generation_config=genai.GenerationConfig(
                    response_mime_type=payload["generationConfig"]["responseMimeType"],
                    response_schema=payload["generationConfig"]["responseSchema"],
                ),
            )

            prediction_data = json.loads(response.text)
            return prediction_data

        except Exception as e:
            print(f"Error generating prediction: {e}")
            return None
