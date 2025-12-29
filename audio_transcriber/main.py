from pathlib import Path
from flask import Flask, request
import base64
import json
import logging
import os
import threading
import time
import yt_dlp
import shutil
import tempfile
import subprocess
from dotenv import load_dotenv
import queue
import uuid

from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech as cloud_speech_types
from confluent_kafka import Producer

# --- Configuration & Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

PROJECT_ID = "streamer-478916"
SERVICE_ACCOUNT_PATH = os.getenv(
    "SERVICE_ACCOUNT_KEY_PATH", "./service_account_creds.json"
)
LOCATION = "global"

# --- Kafka Configuration ---
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_API_KEY = os.environ.get("KAFKA_API_KEY")
KAFKA_API_SECRET = os.environ.get("KAFKA_API_SECRET")
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC")

BASE_DIR = Path(__file__).resolve().parent.parent
app = Flask(__name__)

# --- Global Queue & Event Control ---
# Increased size to buffer audio during the split-second API reconnection
audio_queue = queue.Queue(maxsize=1000)
stop_event = threading.Event()
VIDEO_ID = None


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
        "batch.size": 50000,
        "delivery.timeout.ms": 30000,
    }

    try:
        return Producer(conf)
    except Exception as e:
        logger.error(f"Failed to initialize Kafka Producer: {e}")
        return None


def delivery_report(err, msg):
    if err is not None:
        logger.error(f"Kafka Message delivery failed: {err}")


def get_live_stream_url(video_url: str) -> str:
    """Extracts the direct .m3u8 URL safely for Cloud Run."""
    gcp_secret_path = Path("/secrets/cookies.txt")
    local_dev_path = BASE_DIR / "cookies.txt"
    cookie_source = None
    temp_cookie_path = None

    if gcp_secret_path.exists():
        cookie_source = gcp_secret_path
    elif local_dev_path.exists():
        cookie_source = local_dev_path

    if cookie_source:
        try:
            # Create a TEMP copy of cookies to avoid Read-Only errors
            with tempfile.NamedTemporaryFile(
                mode="wb", delete=False, suffix=".txt"
            ) as tmp_file:
                with open(cookie_source, "rb") as src:
                    shutil.copyfileobj(src, tmp_file)
                temp_cookie_path = tmp_file.name
            logger.info(f"Using cookies from temp file: {temp_cookie_path}")
        except Exception as e:
            logger.error(f"Failed to copy cookies: {e}")
            # Only fallback if copy fails
            temp_cookie_path = str(cookie_source)

    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "js_runtimes": {"node": {}},  # Use nodejs for JavaScript execution
        "no_cache_dir": True,
        "force_ipv4": True,
    }
    if temp_cookie_path:
        ydl_opts["cookiefile"] = temp_cookie_path
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)

        if not info.get("is_live"):
            logger.warning(f"Note: {video_url} is not currently live.")

        return info["url"]


def start_ffmpeg_worker(video_url):
    """
    Starts FFmpeg ONCE. It keeps running in the background filling the queue
    regardless of Google API reconnections.
    """

    def ffmpeg_worker():
        try:
            stream_url = get_live_stream_url(video_url)
            logger.info("FFmpeg starting capture...")

            ffmpeg_cmd = [
                "ffmpeg",
                "-loglevel",
                "error",
                "-analyzeduration",
                "0",
                "-probesize",
                "32768",
                "-i",
                stream_url,
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-f",
                "s16le",
                "-ac",
                "1",
                "-ar",
                "16000",
                "pipe:1",
            ]

            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=16000,
            )

            CHUNK_SIZE = 6400  # 200ms

            while not stop_event.is_set():
                chunk = process.stdout.read(CHUNK_SIZE)
                if not chunk:
                    logger.warning("FFmpeg stream ended naturally.")
                    break
                audio_queue.put(chunk)

            process.terminate()
        except Exception as e:
            logger.error(f"FFmpeg Worker Error: {e}")
        finally:
            audio_queue.put(None)  # Signal end of stream

    t = threading.Thread(target=ffmpeg_worker, daemon=True)
    t.start()
    return t


def request_generator_session(config, timeout_seconds=290):
    """
    Yields audio chunks for ~290 seconds, then returns.
    This allows the main loop to close the request cleanly and restart a new one.
    """
    # 1. Send Configuration Frame First
    yield cloud_speech_types.StreamingRecognizeRequest(
        recognizer=f"projects/{PROJECT_ID}/locations/global/recognizers/_",
        streaming_config=config,
    )

    start_time = time.time()

    while True:
        # 2. Check Time Limit (Reconnect before 305s limit)
        if time.time() - start_time > timeout_seconds:
            logger.info("♻️ Refreshing Stream Session (Time Limit)...")
            return

        try:
            # 3. Get Audio from Queue
            chunk = audio_queue.get(timeout=10.0)

            if chunk is None:
                return  # End of stream

            yield cloud_speech_types.StreamingRecognizeRequest(audio=chunk)

        except queue.Empty:
            # Just keep waiting, stream might be buffering
            continue


def run_transcription(video_url: str):
    """Main Orchestrator: Starts FFmpeg once, restarts Google API in a loop."""
    client = SpeechClient.from_service_account_json(SERVICE_ACCOUNT_PATH)
    producer = create_kafka_producer()

    # 1. Start FFmpeg Background Worker
    start_ffmpeg_worker(video_url)

    # 2. Configure Google Speech
    recognition_config = cloud_speech_types.RecognitionConfig(
        explicit_decoding_config=cloud_speech_types.ExplicitDecodingConfig(
            encoding=cloud_speech_types.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            audio_channel_count=1,
        ),
        language_codes=["en-US"],
        model="latest_long",
    )
    streaming_config = cloud_speech_types.StreamingRecognitionConfig(
        config=recognition_config
    )

    logger.info("✅ Starting Infinite Transcription Loop...")

    # 3. Infinite Reconnection Loop
    while not stop_event.is_set():
        try:
            # Create generator that lasts only 290 seconds
            requests_gen = request_generator_session(
                streaming_config, timeout_seconds=290
            )

            # Call API
            responses = client.streaming_recognize(requests=requests_gen)

            # Process Responses
            for response in responses:
                if not response.results:
                    continue

                for result in response.results:
                    if not result.alternatives:
                        continue

                    transcript = result.alternatives[0].transcript
                    if result.is_final:
                        logger.info(f"[FINAL] {transcript}")

                        if producer:
                            try:
                                key = str(uuid.uuid4())
                                audio_data = {
                                    "published_at": int(time.time() * 1000),
                                    "transcript": transcript,
                                    "is_final": True,
                                    "video_id": VIDEO_ID,
                                }
                                producer.produce(
                                    topic=KAFKA_TOPIC,
                                    key=key,
                                    value=json.dumps(audio_data).encode("utf-8"),
                                    callback=delivery_report,
                                )
                                producer.poll(0)
                            except Exception as e:
                                logger.error(f"Kafka Error: {e}")

        except Exception as e:
            logger.error(f"Stream Loop Exception: {e}")
            # If the queue is empty/None, break completely
            if not audio_queue.empty() and audio_queue.queue[-1] is None:
                break
            time.sleep(1)  # Brief pause before reconnecting

    # Cleanup
    if producer:
        producer.flush()


@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "GET":
        return "Server is running.", 200

    if request.method == "POST":
        envelope = request.get_json(silent=True)
        if not envelope:
            return "Bad Request", 400

        if "message" in envelope and "data" in envelope["message"]:
            try:
                data_decoded = base64.b64decode(envelope["message"]["data"]).decode(
                    "utf-8"
                )
                payload = json.loads(data_decoded)
                video_id = payload.get("video_id")

                if video_id:
                    VIDEO_ID = video_id  # noqa
                    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
                    logger.info(f"Starting job for: {youtube_url}")

                    # Reset stop event for new thread
                    stop_event.clear()

                    # Clean queue (optional but good practice)
                    with audio_queue.mutex:
                        audio_queue.queue.clear()

                    t = threading.Thread(target=run_transcription, args=(youtube_url,))
                    t.daemon = True
                    t.start()
                    return "Started", 200
            except Exception as e:
                logger.error(f"PubSub Error: {e}")
                return "Error", 500

        return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)  # nosec B104
