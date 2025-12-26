import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Any
import google.generativeai as genai
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from settings import GEMINI_API_KEY, FIRESTORE_DB_NAME, COLLECTION_NAME

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class PredictionController:
    def __init__(self) -> None:
        genai.configure(api_key=GEMINI_API_KEY)
        self.db = firestore.Client(database=FIRESTORE_DB_NAME)

        self.prediction_schema = {
            "type": "OBJECT",
            "properties": {
                "sentiment_score": {
                    "type": "NUMBER",
                    "description": "The predicted sentiment score for the immediate future (-1.0 to 1.0).",
                },
                "strategy": {
                    "type": "STRING",
                    "description": "Actionable advice for the streamer (e.g., 'Keep going', 'Change topic').",
                },
                "reasoning": {
                    "type": "STRING",
                    "description": "Simple, non-technical explanation of why this strategy was chosen.",
                },
            },
            "required": ["sentiment_score", "strategy", "reasoning"],
        }

        self.system_instruction = """
        You are a real-time Streamer Performance Coach. 
        
        **Input Context:**
        You will receive data containing:
        - 'avg_sentiment': Current mood (-1.0 to 1.0).
        - 'message_count': Engagement level/speed.
        - 'window_start_time': Timestamp.

        **Your Task:**
        1. **Analyze:** Look at the 'avg_sentiment' and 'message_count' trends.
        2. **Predict:** Determine the 'sentiment_score' for the next minute.
        3. **Advise (Strategy):**
           - If engagement is dropping/boring: Warn the streamer.
           - If engagement is high + good sentiment: Validate them.
           - If toxicity is high: Suggest moderation.
        4. **Explain (Reasoning):**
           - Write for a gamer, NOT a data scientist.
           - Use simple, direct language.
        """

        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-preview-09-2025",
            system_instruction=self.system_instruction,
        )

    def _serialize_firestore_data(self, data: dict) -> dict:
        """Helper to convert Firestore timestamps to strings."""
        clean_data = {}
        for key, value in data.items():
            if hasattr(value, "isoformat"):
                clean_data[key] = value.isoformat()
            else:
                clean_data[key] = value
        return clean_data

    def fetch_chat_history(self, live_chat_id: str):
        now = datetime.now(timezone.utc)
        five_minutes_ago = now - timedelta(minutes=5)

        logger.info(
            f"[Predictor] Fetching last 5 mins of chat history for: {live_chat_id}"
        )

        query = (
            self.db.collection(COLLECTION_NAME)
            .where(filter=FieldFilter("live_chat_id", "==", live_chat_id))
            .where(filter=FieldFilter("window_start_time", ">=", five_minutes_ago))
            .order_by("window_start_time")
        )

        docs = query.stream()
        messages = []

        for doc in docs:
            data = doc.to_dict()
            if not data:
                continue

            history = {
                "avg_sentiment": data.get("avg_sentiment"),
                "message_count": data.get("message_count"),
                "window_start_time": data.get("window_start_time"),
                "window_end_time": data.get("window_end_time"),
            }

            messages.append(self._serialize_firestore_data(history))

        if not messages:
            logger.warning("[Predictor] No recent chat history found. Cannot predict.")
            return None

        logger.info(f"[Predictor] Retrieved {len(messages)} history points.")
        return messages

    def generate_prediction(self, live_chat_id: str) -> dict[str, Any] | None:
        """
        Takes history data, sends it to Gemini, and returns structured JSON.
        """
        message_history = self.fetch_chat_history(live_chat_id=live_chat_id)

        if message_history is None:
            return None

        try:
            history_json_string = json.dumps(message_history, indent=2)

            logger.info("🧠 [Predictor] Sending data to Gemini for analysis...")

            response = self.model.generate_content(
                history_json_string,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=self.prediction_schema,
                ),
            )

            prediction_data = json.loads(response.text)

            logger.info(
                f"[Predictor] Prediction generated! Strategy: '{prediction_data.get('strategy')}'"
            )
            return prediction_data

        except Exception as e:
            logger.error(f"[Predictor] Gemini Error: {e}")
            return None
