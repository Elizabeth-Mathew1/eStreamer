import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import random
import json
import pytz


SERVICE_ACCOUNT_KEY_PATH = './service_account_creds.json'
PROJECT_NAME = 'streamer'
FIRESTORE_DB_NAME = 'streamer-db-2'
COLLECTION_NAME = 'stream_summaries'

TIMEZONE = pytz.timezone('Asia/Kolkata')
CHAT_ID = "gamer-jeez-live-65"
END_TIME = datetime.now(TIMEZONE).replace(second=0, microsecond=0)
START_TIME = END_TIME - timedelta(minutes=60) ## starting from 60 minutes ago

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
    

def generate_summary(chat_id, start_time):
    """Generates one synthetic 60-second summary document."""
    
    message_count = random.randint(10, 500)

    sentiments = ["positive", "negative", "neutral","highly positive", "highly negative"]
    avg_sentiment = random.choice(sentiments)

    possible_topics = ["Product Launch", "Technical Deep Dive", "Community Q&A", "Price Discussion", "Future Roadmap"]
    num_topics = random.randint(1, 3)
    
    topics = []
    # Weighted topic counts based on message volume
    for topic_name in random.sample(possible_topics, num_topics):
        topics.append({
            'name': topic_name,
            'count': random.randint(int(message_count * 0.1), int(message_count * 0.5)),
        })
    

    potential_phrases = [
        # Positive/Excited
        f"OMG the {random.choice(possible_topics)} reveal was amazing! 🚀🔥",
        "Take my money! This is exactly what we needed. 💵",
        "Best stream ever! I learned so much today. 🙏",
        "I'm so hyped for the next update! ✨🤩",
        "The community response is overwhelmingly positive. 👍",
        # Neutral/Question
        "When is the next live stream scheduled? 📅",
        "Can we get a quick recap of the last 5 minutes?",
        "What are the system requirements for this?",
        f"Any details on the {random.choice(possible_topics)} implementation?",
        # Negative/Concern
        "I'm worried about the price point, feels too high. 📉",
        "That technical detail was confusing. 😥",
        "Why are they ignoring the chat questions? 😠",
        "I hope they fix that major bug soon. 🤞",
    ]
    
    key_phrases = random.sample(potential_phrases, k=random.randint(3, 5))
    random.shuffle(key_phrases)

    top_users = [
        {'user_id': f"user_{random.randint(100, 999)}", 'count': random.randint(5, 20)},
        {'user_id': f"user_{random.randint(100, 999)}", 'count': random.randint(3, 10)},
    ]


    return {
        'live_chat_id': chat_id,
        'window_start_time': start_time, 
        'message_count': message_count,
        'avg_sentiment': avg_sentiment,
        'top_topics': topics,
        'key_phrases': key_phrases,
        'top_users': top_users,
    }



def ingest_dummy_data(firestore_db):
    """Starting point for ingesting dummy data to code"""

    start_time = START_TIME

    while start_time <= END_TIME:
        live_chat_id = f"chat_{random.randint(10, 999)}"
        chat_summary = generate_summary(chat_id=live_chat_id, start_time=start_time)

        doc_id = f"{CHAT_ID}_T_{start_time.strftime('%Y%m%d%H%M')}"

        try:
            firestore_db.collection(COLLECTION_NAME).document(doc_id).set(chat_summary)
            print(f"Added summary for chat {live_chat_id} at {start_time}")

        except Exception as e:
            print(f"Failed to add summary : {e}")
            continue

        
        start_time += timedelta(minutes=1)
    
    print("Dummy data ingestion completed. Check previous logs for details/ errors.")
  


if __name__ == '__main__':
    firestore_db = initialize_firebase()
    if firestore_db:
        ingest_dummy_data(firestore_db)
    else:
        print("Failed to initialize Firebase.")