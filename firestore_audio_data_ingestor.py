import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import random
import pytz


SERVICE_ACCOUNT_KEY_PATH = "./service_account_creds.json"
PROJECT_NAME = "streamer"
FIRESTORE_DB_NAME = "streamer-db-2"
COLLECTION_NAME = "stream_summaries"

TIMEZONE = pytz.timezone("Asia/Kolkata")
CHAT_ID = "gamer-jeez-live-65"
END_TIME = datetime.now(TIMEZONE).replace(second=0, microsecond=0)
START_TIME = END_TIME - timedelta(minutes=60)  ## starting from 60 minutes ago


def initialize_firebase():
    """Initializes Firebase using the service account key and connects to the specified Firestore database."""

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
            firebase_admin.initialize_app(cred)

        print("Firebase initialized successfully.")

        return firestore.client(database_id=FIRESTORE_DB_NAME)

    except Exception as e:
        print(f"Error initializing Firebase : {e}")
        return None

def generate_dummy_data():
    """Generates random dummy data for audio and correlated chat fields"""
    
    # Random audio summaries
    audio_summaries = [
        "spectacular game. Today's evening is blessed",
        "incredible performance by the team tonight",
        "amazing match with lots of exciting moments",
        "great stream with engaging commentary",
        "fantastic gameplay and impressive skills",
        "wonderful session with enthusiastic viewers",
        "outstanding play and memorable highlights",
        "excellent content with positive vibes",
    ]
    
    # Random chat messages
    chat_messages = [
        "life is good", "W", "crazyyy", "what a game",
        "insane!", "goat", "fire", "lets gooo",
        "amazing", "perfect", "legendary", "epic",
        "love it", "best stream", "so good", "incredible",
        "hype", "pog", "clutch", "gg",
    ]
    
    # Generate random audio data
    audio_data = {
        "audio_summary": random.choice(audio_summaries),
        "audio_sentiment": round(random.uniform(-1.0, 1.0), 2),  # Sentiment between -1 and 1
    }
    
    # Generate random correlated chat data
    chat_volume = random.randint(100, 500)
    unique_users = random.randint(30, 150)
    num_chats = min(random.randint(10, 50), chat_volume)  # Can't have more chats than volume
    
    correlated_chat_data = {
        "correlated_chat_volume": chat_volume,
        "correlated_users": unique_users,
        "correlated_chats": random.sample(chat_messages, min(num_chats, len(chat_messages))),
    }
    
    return {
        "audio_data": audio_data,
        "correlated_chat_data": correlated_chat_data,
    }

def ingest_dummy_data(firestore_db):
    """Updates all existing documents in the collection with dummy data"""

    try:
        docs = firestore_db.collection(COLLECTION_NAME).stream()
        updated_count = 0
        
        for doc in docs:
            try:
                # Generate random dummy data for each document
                dummy_doc_data = generate_dummy_data()
                doc.reference.update(dummy_doc_data)
                updated_count += 1
                print(f"Updated document: {doc.id}")
            except Exception as e:
                print(f"Failed to update document {doc.id}: {e}")
                continue

        print(f"Update completed. Updated {updated_count} documents.")

    except Exception as e:
        print(f"Error updating documents: {e}")


if __name__ == "__main__":
    firestore_db = initialize_firebase()
    if firestore_db:
        ingest_dummy_data(firestore_db)
    else:
        print("Failed to initialize Firebase.")

