import re
import statistics
from collections import Counter
from datetime import datetime, timedelta, timezone
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from settings.base import COLLECTION_NAME, FIRESTORE_DB_NAME


class AnalyzerController:
    def __init__(self, live_chat_id: str, duration_seconds: int) -> None:
        self.live_chat_id = live_chat_id
        self.duration_seconds = duration_seconds
        self.db = firestore.Client(database=FIRESTORE_DB_NAME)

    def _is_spam(self, text: str) -> bool:
        """
        Returns True if the message looks like spam.
        """
        if not text:
            return True

        if re.search(r"(.)\1{4,}", text):
            return True

        if re.search(r"\b(\w+)( \1){3,}\b", text, re.IGNORECASE):
            return True

        if len(text) < 4:
            return True

        return False

    def analyze(self):
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(seconds=int(self.duration_seconds))

        query = (
            self.db.collection(COLLECTION_NAME)
            .where(filter=FieldFilter("live_chat_id", "==", self.live_chat_id))
            .where(filter=FieldFilter("window_start_time", ">=", start_time))
        )

        docs = query.stream()

        sentiments = []
        all_topics = Counter()
        all_users = Counter()
        all_chats = []
        doc_count = 0
        seen_messages = set()

        for doc in docs:
            doc_data = doc.to_dict()
            doc_count += 1

            s_score = doc_data.get("avg_sentiment")
            if s_score is not None:
                sentiments.append(s_score)

            topics = doc_data.get("top_topics", [])
            for topic in topics:
                name = topic.get("name")
                count = topic.get("count", 1)
                if name:
                    all_topics[name] += count

            messages = doc_data.get("messages", [])
            for msg in messages:
                user = msg.get("author_display_name", "Unknown")
                text = msg.get("message", "")

                all_users[user] += 1
                score = 0
                if text and not self._is_spam(text=text) and text not in seen_messages:
                    score = len(text)
                    seen_messages.add(text)

                all_chats.append({"message": text, "author": user, "score": score})

        if doc_count == 0:
            return {
                "avg_sentiment": 0,
                "top_topics": [],
                "top_chats": [],
                "top_users": [],
            }

        final_avg_sentiment = statistics.mean(sentiments) if sentiments else 0

        final_top_topics = [name for name, _ in all_topics.most_common(5)]

        final_top_users = [{user: count} for user, count in all_users.most_common(5)]

        sorted_chats = sorted(all_chats, key=lambda x: x["score"], reverse=True)
        final_top_chats = [c["message"] for c in sorted_chats[:5]]

        return {
            "avg_sentiment": round(final_avg_sentiment, 2),
            "top_topics": final_top_topics,
            "top_chats": final_top_chats,
            "top_users": final_top_users,
        }
