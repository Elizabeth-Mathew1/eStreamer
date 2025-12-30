from flask import jsonify
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from settings import (
    FIRESTORE_DB_NAME,
    COLLECTION_NAME,
    FIRESTORE_COLLECTION_STREAM_METADATA,
)


class CorrelationController:
    def __init__(self):
        self.db = firestore.Client(database=FIRESTORE_DB_NAME)

    def get_live_correlation(self, video_id: str):
        """
        Fetches data and returns a JSON Response object directly.
        """
        query = self.db.collection(FIRESTORE_COLLECTION_STREAM_METADATA).where(
            filter=FieldFilter("video_id", "==", video_id)
        )

        doc = next(query.stream(), None)

        if doc:
            live_chat_id = doc.get("live_chat_id")
        else:
            raise Exception("Video ID not found in stream metadata")
        query = (
            self.db.collection(COLLECTION_NAME)
            .where(filter=FieldFilter("live_chat_id", "==", live_chat_id))
            .order_by("window_start_time", direction=firestore.Query.DESCENDING)
            .limit(1)
        )

        docs = list(query.stream())

        if not docs:
            return {
                "audio_data": {
                    "audio_summary": "Waiting for data...",
                    "audio_sentiment": 0.0,
                },
                "correlated_chat_data": {
                    "correlated_chat_volume": 0,
                    "correlated_users": 0,
                    "correlated_chats": [],
                },
            }

        data = docs[0].to_dict()    
        audio_data = data.get("audio_data", {})
        correlated_chat_data = data.get("correlated_chat_data", {})

        return {
            "audio_data": audio_data,
            "correlated_chat_data": correlated_chat_data,
        }
