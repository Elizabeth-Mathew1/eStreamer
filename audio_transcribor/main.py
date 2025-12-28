from flask import Flask, request
import base64
import json
import logging
import os
import threading
import time
import yt_dlp
import subprocess
from typing import Generator
from dotenv import load_dotenv
import queue
import uuid

from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech as cloud_speech_types
from google.oauth2 import service_account

from google.api_core import exceptions
from google.cloud import speech
from google.cloud.speech_v2 import types as cloud_speech_types
from google.cloud.speech_v2.types import cloud_speech
from confluent_kafka import Producer, KafkaException



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ID = "streamer-478916"


load_dotenv()


# # ---- Chunk Configuration ----
# SAMPLE_RATE = 16000
# CHUNK_DURATION_MS = 100
# CHUNK_SIZE = int(SAMPLE_RATE * 2 * (CHUNK_DURATION_MS / 1000))
# SESSION_DURATION_SECONDS = 270  

# --- Google Cloud Configuration ---

SERVICE_ACCOUNT_PATH = os.getenv("SERVICE_ACCOUNT_KEY_PATH", "./service_account_creds.json")
LOCATION = "global"

# --- Kafka Configuration ---
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_API_KEY = os.environ.get("KAFKA_API_KEY")
KAFKA_API_SECRET = os.environ.get("KAFKA_API_SECRET")
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC")


oauth_credentials = {
    "client_id": os.environ.get("CLIENT_ID"),
    "client_secret": os.environ.get("CLIENT_SECRET"),
    "refresh_token": os.environ.get("REFRESH_TOKEN"),
    "type": "authorized_user"
}


app = Flask(__name__)


def create_kafka_producer():
    """Initializes and returns a Confluent Kafka Producer."""

    if not all([KAFKA_BOOTSTRAP_SERVERS, KAFKA_API_KEY, KAFKA_API_SECRET, KAFKA_TOPIC]):
        logger.warning(
            "Missing Kafka environment variables. Kafka production disabled."
        )
        return None

    conf = {
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "security.protocol": "SASL_SSL",
        "sasl.mechanisms": "PLAIN",
        "sasl.username": KAFKA_API_KEY,
        "sasl.password": KAFKA_API_SECRET,
        "client.id": "youtube-audio-processor",
        "retries": 3,
        "linger.ms": 1000,
        "batch.size": 50000,  # 50KB accommodates approx 200 chat messages.
        "delivery.timeout.ms": 30000,
    }

    try:
        producer = Producer(conf)
        logger.info(f"Kafka Producer initialized for {KAFKA_BOOTSTRAP_SERVERS}")
        return producer

    except Exception as e:
        logger.error(f"Failed to initialize Kafka Producer: {e}")
        return None


def retry_with_backoff(fn, max_retries=5):
    """Retries a network function with exponential backoff."""
    for i in range(max_retries):
        try:
            return fn()
        except Exception as e:
            wait = 2 ** i
            logger.error(f"Network error: {e}. Retrying in {wait}s...")
            time.sleep(wait)
    raise Exception("Max retries exceeded for network operation.")


def delivery_report(err, msg):
    """Called once for each message produced to indicate delivery result."""
    logger.info(f"Delivery report: {err}, {msg}")
    if err is not None:
        logger.error(f"Kafka Message delivery failed: {err}")


def get_live_stream_url(video_url: str) -> str:
    """Extracts the direct .m3u8 (HLS) or .mpd (DASH) URL."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'js_runtimes': {'node': {}}, # Use nodejs for JavaScript execution
        
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)

        if not info.get('is_live'):
            logger.warning(f"Note: {video_url} is not currently live.")
            
        return info['url']


def request_generator(video_url: str):

    audio_queue = queue.Queue(maxsize=50)
    stop_event = threading.Event()


    recognition_config = cloud_speech_types.RecognitionConfig(
        explicit_decoding_config=cloud_speech_types.ExplicitDecodingConfig(
            encoding=cloud_speech_types.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            audio_channel_count=1,
        ),
        language_codes=["en-US"],
        model="latest_long",
    )
    streaming_config = cloud_speech_types.StreamingRecognitionConfig(config=recognition_config)

    def ffmpeg_worker():
        """Background thread to feed the queue from FFmpeg."""
        try:
            # Replace with your actual stream retrieval logic
            stream_url = retry_with_backoff(lambda: get_live_stream_url(video_url))
            
            # Using low-latency flags for FFmpeg
            ffmpeg_cmd = [
            'ffmpeg',
            '-loglevel', 'info',
            '-analyzeduration', '0',
            '-probesize', '32768',
            '-i', stream_url,
            '-vn',             # No video (ESSENTIAL)
            '-acodec', 'pcm_s16le',
            '-f', 's16le',     # Force raw output
            '-ac', '1',
            '-ar', '16000',
            'pipe:1'
            ]
            
            process = subprocess.Popen(
                ffmpeg_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.DEVNULL,
                bufsize=16000 
            )
            
            CHUNK_SIZE = 6400  # 200ms
            
            while not stop_event.is_set():
                chunk = process.stdout.read(CHUNK_SIZE)
                if not chunk:
                    break
                audio_queue.put(chunk)
                
            process.terminate()
        except Exception as e:
            logger.error(f"FFmpeg Worker Error: {e}")
        finally:
            audio_queue.put(None) 

    worker_thread = threading.Thread(target=ffmpeg_worker, daemon=True)
    worker_thread.start()

    try:
        yield cloud_speech_types.StreamingRecognizeRequest(
            recognizer=f"projects/{PROJECT_ID}/locations/global/recognizers/_",
            streaming_config=streaming_config,
        )

        start_time = time.time()
        chunks_sent = 0

        while True:
            try:
                chunk = audio_queue.get(timeout=5.0)
            except queue.Empty:
                logger.error("Queue empty for 5s - Source likely died.")
                break

            if chunk is None: 
                break

            yield cloud_speech_types.StreamingRecognizeRequest(audio=chunk)
            
            chunks_sent += 1
            if chunks_sent % 25 == 0: # Logging every 5 seconds
                elapsed = time.time() - start_time
                logger.info(f"Sent: {chunks_sent * 0.2:.1f}s audio | Elapsed: {elapsed:.1f}s")

    finally:
        stop_event.set()
        worker_thread.join(timeout=1.0)
        logger.info("Generator session closed.")

         
def run_transcription(video_url: str):
        client = SpeechClient.from_service_account_json(SERVICE_ACCOUNT_PATH)
        logger.info("Starting Robust Transcription (V2)...")
        producer = create_kafka_producer()

        try:
            responses = client.streaming_recognize(requests=request_generator(video_url))
            for response in responses:
                if not response.results:
                    continue
                    
                for result in response.results:
                    if result.alternatives:
                        transcript = result.alternatives[0].transcript
                        if result.is_final:
                            logger.info(f"[FINAL] Transcript: {transcript}")
                            
                            
                        else:
                            logger.debug(f"[INTERIM] Transcript: {transcript}")

                        if producer:
                                key = str(uuid.uuid4())
                                chat_data = {
                                    "published_at": int(time.time() * 1000),
                                    "transcript": transcript,
                                }

                                try:
                                    producer.produce(
                                        topic=KAFKA_TOPIC,
                                        key=key,
                                        value=json.dumps(chat_data).encode("utf-8"),
                                        callback=delivery_report,
                                    )
                                    logger.info(f"Produced message to Kafka: {key}")
                                    producer.poll(0)

                                except (KafkaException, BufferError) as kafka_err:
                                    producer.flush()
                                    logger.warning(
                                        f"Kafka production failed or buffer full: {kafka_err}"
                                    )

        except exceptions.DeadlineExceeded:
            logger.warning("STT Session deadline exceeded.")

        except exceptions.OutOfRange:
            logger.warning("STT Session limit reached.")

        except Exception as e:
            logger.error(f"STT Session ended: {e}", exc_info=True)



@app.route("/", methods=["POST", "GET"])
def index():
    """
    Receives Pub/Sub push messages containing the YouTube Video ID.
    Converts Video ID to Live Chat ID and starts a new ingestion thread.
    """
    if request.method == "GET":
        return "Server is running. Awaiting POST requests from Pub/Sub.", 200

    if request.method == "POST":
        envelope = request.get_json(silent=True)

        if envelope is None:
            logger.error("Received POST with malformed or empty JSON body.")
            return "Bad Request: Malformed JSON or missing body.", 400

        # 1. Check for the Pub/Sub structure
        if "message" in envelope and "data" in envelope["message"]:
            data_b64 = envelope["message"]["data"]
            try:
                # Decode the base64 Pub/Sub payload
                data_decoded = base64.b64decode(data_b64).decode("utf-8")
                payload = json.loads(data_decoded)

                video_id = payload.get("video_id")

                if video_id:
                    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
                    logger.info(f"Received Pub/Sub trigger for YouTube URL: {youtube_url}")

                    transcription_thread = threading.Thread(
                        target=run_transcription, args=(youtube_url,)
                    )
                    transcription_thread.daemon = True
                    transcription_thread.start()

                    return "Transcription thread started.", 200

                # If the inner payload was valid but missing 'video_id'
                logger.warning("Pub/Sub payload did not contain a 'video_id'.")
                return "OK (No video_id).", 200

            except Exception as e:
                # Catch errors during base64 decode or JSON load of the *data* field
                logger.error(f"Error processing Pub/Sub message data: {e}")
                return "Error processing Pub/Sub message data.", 500

        # If the outer envelope was valid JSON but missing the necessary fields
        logger.info(
            "Received POST request with valid JSON but incorrect Pub/Sub structure."
        )
        return "OK (Invalid Pub/Sub structure).", 200

    # Fallback to catch anything else, although unlikely
    return "Internal Server Error: Unhandled Request Flow", 500



# The Cloud Run environment will provide the PORT variable
if __name__ == "__main__":
    
    # port = int(os.environ.get("PORT", 8080))
    # app.run(host="0.0.0.0", port=port)
    run_transcription("https://www.youtube.com/watch?v=nJKDNPs0wP8")
   
