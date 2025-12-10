import os
import json
import requests
import time
from confluent_kafka import Consumer, KafkaException, KafkaError
from datetime import datetime, timedelta, timezone
import logging
from flask import Flask
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_API_KEY = os.environ.get("KAFKA_API_KEY")
KAFKA_API_SECRET = os.environ.get("KAFKA_API_SECRET")
KAFKA_TOPIC = os.environ.get('KAFKA_TOPIC')
KAFKA_GROUP_ID = os.environ.get('KAFKA_GROUP_ID')

GEMINI_MODEL = 'gemini-2.5-flash-preview-09-2025'
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


FIRESTORE_DB_NAME = os.environ.get("FIRESTORE_DB_NAME")
PROJECT_NAME = os.environ.get('PROJECT_NAME')
SERVICE_ACCOUNT_KEY_PATH = os.environ.get('SERVICE_ACCOUNT_KEY_PATH')
COLLECTION_NAME = os.environ.get('COLLECTION_NAME')



# --- Logging Configuration ---

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__) 


app = Flask(__name__)


def initialize_firebase():

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
            firebase_admin.initialize_app(cred)
            
        print("Firebase initialized successfully.")
        
        return firestore.client(database_id=FIRESTORE_DB_NAME)
        
    except Exception as e:
        print(f"Error initializing Firebase : {e}")
        return None


def get_kafka_consumer():

    if not all([KAFKA_BOOTSTRAP_SERVERS, KAFKA_API_KEY, KAFKA_API_SECRET, KAFKA_TOPIC]):
        logger.error("Missing critical Kafka environment variables. Required: KAFKA_BOOTSTRAP_SERVERS, KAFKA_API_KEY, KAFKA_API_SECRET, KAFKA_TOPIC")
        return None
        
    conf = {
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'security.protocol': 'SASL_SSL',
        'sasl.mechanisms': 'PLAIN',
        'sasl.username': KAFKA_API_KEY,
        'sasl.password': KAFKA_API_SECRET,
        'group.id': KAFKA_GROUP_ID,
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': True, 
        'client.id': 'gemini-ai-worker'
    }
    
    try:
        consumer = Consumer(conf)
        consumer.subscribe([KAFKA_TOPIC])
        logger.info(f"Subscribed to Kafka topic '{KAFKA_TOPIC}' with group '{KAFKA_GROUP_ID}'")
        return consumer

    except Exception as e:
        logger.critical(f"Failed to create Kafka Consumer: {e}")
        return None


def analyze_with_gemini(messages_list):

    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is missing. Skipping analysis.")
        return {"avg_sentiment": 0.0, "top_topics": ["No Analysis"], "key_phrases": []}
        

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    
    formatted_messages = [f"{m['author_display_name']}: {m['message']}" for m in messages_list]
    combined_text = ",".join(formatted_messages)
    
    system_prompt = (
        "You are an expert stream data analyst. Analyze the following 1-minute batch of chat "
        "messages for sentiment and key themes. Respond ONLY with a valid JSON object."
    )
    
    user_query = (
        "Analyze these chat messages and return the results in the JSON format defined by the schema. "
        "Calculate the 'avg_sentiment' (float from -1.0 for negative to 1.0 for positive). "
        "Identify up to 3 'top_topics' (strings) and up to 5 'key_phrases' (strings)."
        f"\n\nMessages:\n{combined_text}"
    )

    # Define the expected JSON output schema
    json_schema = {
        "type": "OBJECT",
        "properties": {
            "avg_sentiment": { "type": "NUMBER", "description": "Average sentiment score between -1.0 and 1.0." },
            "top_topics": { "type": "ARRAY", "items": { "type": "STRING" } },
            "key_phrases": { "type": "ARRAY", "items": { "type": "STRING" } }
        },
        "required": ["avg_sentiment", "top_topics", "key_phrases"]
    }
    
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": { 
            "responseMimeType": "application/json",
            "responseSchema": json_schema
        }
    }
    
    try:
        # Use exponential backoff for robustness against API limits
        for attempt in range(3):
            resp = requests.post(url, json=payload, timeout=45)
            if resp.status_code == 429 and attempt < 2:
                wait_time = 2 ** attempt
                logger.warning(f"Rate limited (429). Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            resp.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            
            result = resp.json()

            # Navigate to the text content within the structured response
            json_text = result['candidates'][0]['content']['parts'][0]['text']
            return json.loads(json_text)
            
        logger.error(f"Gemini API failed after multiple retries. Final status: {resp.status_code}")
        return {"avg_sentiment": 0.0, "top_topics": ["API Failure"], "key_phrases": []}
        
    except Exception as e:
        logger.error(f"Gemini Analysis Error: {e}")
        return {"avg_sentiment": 0.0, "top_topics": ["Processing Error"], "key_phrases": []}




def process_batch(db, msg_value):

    try:
        data = json.loads(msg_value)
        
        live_chat_id = data.get('live_chat_id')
        messages = data.get('messages', [])
        count = data.get('message_count')

        window_end_ms = data.get('window_end')  ## in epoch milliseconds
    
            
        epoch_seconds = window_end_ms / 1000.0
        window_end_dt = datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
        window_start_dt = window_end_dt - timedelta(minutes=1) ## batching happens by flink in 1 minute windows

        logger.info(f"Processing batch for {live_chat_id} | Start: {window_start_dt.isoformat()} | Count: {count}")

        analysis = analyze_with_gemini(messages)

        # Doc ID must be deterministic and unique (chat_id + window_start_time)
        doc_id = f"{live_chat_id}_{window_start_dt.strftime('%Y%m%d%H%M')}"
        
        doc_data = {
            'live_chat_id': live_chat_id,
            # Firestore will store these datetime objects correctly as Timestamps
            'window_start_time': window_start_dt, 
            'window_end_time': window_end_dt,   
            'message_count': count,
            'messages': messages,
            'avg_sentiment': analysis.get('avg_sentiment', 0.0),
            
            # Prepare topics for the Retrieval API's aggregation function
            'top_topics': [{'name': t, 'count': 1} for t in analysis.get('top_topics', [])],
            'key_phrases': analysis.get('key_phrases', []),

        }

        print(doc_data)

        db.collection(COLLECTION_NAME).document(doc_id).set(doc_data)
        logger.info(f"Saved analysis to Firestore: {doc_id}")

    except Exception as e:
        logger.error(f"Fatal error processing batch: {e}", exc_info=True)



def run_consumer(db):

    consumer = get_kafka_consumer()
    if consumer is None:
        return 
        
    logger.info(f"Starting consumer loop...")

    while True:
        try:
            msg = consumer.poll(1.0) # Poll every 1 second
            
            if msg is None: 
                continue
                
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition event - normal during restart or at stream end
                    continue
                elif msg.error():
                    logger.error(f"Kafka Consumer error: {msg.error()}")
                    continue

            # Safely decode message value
            msg_value = msg.value()[5:]
            if msg_value is None:
                logger.warning("Received message with None value, skipping")
                continue
                
            print(msg_value.decode('utf-8'))

            process_batch(db, msg_value.decode('utf-8'))
            
        except KafkaException as e:
            logger.critical(f"Kafka exception occurred: {e}", exc_info=True)
            time.sleep(5) 
        except Exception as e:
            logger.critical(f"Unhandled exception in consumer loop: {e}", exc_info=True)
            time.sleep(5)


if __name__ == "__main__":
    db = initialize_firebase()
    if db is None:
        logger.error("Firebase not initialized. Exiting.")
        exit(1)
    run_consumer(db)