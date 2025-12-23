import grpc
import os
import time
import threading
import logging
import json
import base64

from flask import Flask, request
from datetime import datetime
from dateutil import parser
from google.cloud import firestore

import grpc_proto.stream_list_pb2 as stream_list_pb2
import grpc_proto.stream_list_pb2_grpc as stream_list_pb2_grpc


from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from confluent_kafka import Producer, KafkaException


# --- YouTube API Configuration ---
REST_API_KEY = os.environ.get("REST_API_KEY")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
CLIENT_ID = os.environ.get("CLIENT_ID")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")
YOUTUBE_SCOPE = ["https://www.googleapis.com/auth/youtube.readonly"]

# --- Kafka Configuration ---
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_API_KEY = os.environ.get("KAFKA_API_KEY")
KAFKA_API_SECRET = os.environ.get("KAFKA_API_SECRET")
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC")
FIRESTORE_DB_NAME = os.environ.get("FIRESTORE_DB_NAME")
FIRESTORE_COLLECTION_NAME = os.environ.get("FIRESTORE_COLLECTION_NAME")


db = firestore.Client(database=FIRESTORE_DB_NAME)


# --- Logging Configuration ---

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


app = Flask(__name__)

## Helper Functions


def refresh_access_token():
    """Refreshes the Access Token using the stored Refresh Token."""
    # Use the google.auth Request object for the HTTP call

    # --- Global Credential Object ---

    credentials = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=YOUTUBE_SCOPE,
    )
    try:
        credentials.refresh(Request())
        logger.info(
            f"Token refreshed successfully. Expires at: {credentials.expiry.isoformat()}"
        )

    except Exception as e:
        logger.error(f"Failed to refresh access token: {e}")
        return None

    return credentials.token


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
        "client.id": "youtube-chat-processor",
        "retries": 3,
        "linger.ms": 1000,
        "batch.size": 50000,
        "delivery.timeout.ms": 30000,
    }

    try:
        producer = Producer(conf)
        logger.info(f"Kafka Producer initialized for {KAFKA_BOOTSTRAP_SERVERS}")
        return producer

    except Exception as e:
        logger.error(f"Failed to initialize Kafka Producer: {e}")
        return None


def delivery_report(err, msg):
    """Called once for each message produced to indicate delivery result."""
    logger.info(f"Delivery report: {err}, {msg}")
    if err is not None:
        logger.error(f"Kafka Message delivery failed: {err}")


def get_live_chat_id(video_id: str) -> str | None:
    """Uses the REST API to find the Live Chat ID from the Video ID."""

    logger.info(f"\n--- STEP 1: REST - Finding Chat ID for Video {video_id} ---")

    try:
        youtube_api = build("youtube", "v3", developerKey=REST_API_KEY)

        response = (
            youtube_api.videos()
            .list(part="liveStreamingDetails", id=video_id)
            .execute()
        )

        if not response.get("items"):
            logger.error(f"No live chat id found for video {video_id}")
            return None

        live_chat_id = (
            response["items"][0].get("liveStreamingDetails", {}).get("activeLiveChatId")
        )

        if not live_chat_id:
            logger.error(f"No live chat id found for video {video_id}")
            return None

        logger.info(f"SUCCESS: Retrieved Live Chat ID: {live_chat_id}")

        item = response["items"][0]
        snippet = item.get("snippet", {})
        details = item.get("liveStreamingDetails", {})
        start_time = details.get("actualStartTime")
        if not start_time:
            start_time = details.get("scheduledStartTime")

        stream_data = {
            "live_video_url": f"https://www.youtube.com/watch?v={video_id}",
            "video_id": video_id,
            "stream_start_time": start_time,
            "stream_name": snippet.get("title"),
            "channel_name": snippet.get("channelTitle"),
            "live_chat_id": live_chat_id,
            "last_updated": firestore.SERVER_TIMESTAMP,
        }

        doc_ref = db.collection(FIRESTORE_COLLECTION_NAME).document(video_id)
        doc_ref.set(stream_data, merge=True)

        logger.info(f"Saved metadata for '{stream_data['stream_name']}' to Firestore.")
        logger.info(f"SUCCESS: Retrieved Live Chat ID: {live_chat_id}")
        return live_chat_id

    except HttpError as e:
        logger.error(f"REST API Error: {e}")
        return None


def youtube_ingest(live_chat_id: str):
    next_page_token = None
    access_token = refresh_access_token()
    if not access_token:
        logger.error("Failed to obtain access token. Cannot proceed with ingestion.")
        return

    producer = create_kafka_producer()

    metadata = (("authorization", f"Bearer {access_token}"),)
    creds = grpc.ssl_channel_credentials()

    with grpc.secure_channel("dns:///youtube.googleapis.com:443", creds) as channel:
        stub = stream_list_pb2_grpc.V3DataLiveChatMessageServiceStub(channel)

        while True:
            try:
                logger.info(
                    f"\n--- Requesting chat stream for: {live_chat_id}. Next token: {next_page_token or 'None'} ---"
                )

                # Build the request message using the generated Protobuf class
                request = stream_list_pb2.LiveChatMessageListRequest(
                    part=["snippet", "authorDetails"],
                    live_chat_id=live_chat_id,
                    max_results=200,
                    page_token=next_page_token,
                )

                # The StreamList call returns an iterable stream of responses (Server Streaming RPC)
                for response in stub.StreamList(request, metadata=metadata):
                    for item in response.items:
                        author = item.author_details.display_name
                        message = item.snippet.display_message

                        try:
                            published_dt = parser.parse(item.snippet.published_at)
                        except (ValueError, TypeError):
                            published_dt = datetime.utcnow()

                        epoch_seconds = published_dt.timestamp()

                        published_at_ms = int(epoch_seconds * 1000)

                        if producer:
                            chat_data = {
                                "id": item.id,
                                "published_at": published_at_ms,
                                "live_chat_id": item.snippet.live_chat_id,
                                "message": message,
                                "author_display_name": author,
                                "author_channel_id": item.author_details.channel_id,
                                "is_chat_owner": item.author_details.is_chat_owner,
                                "is_chat_moderator": item.author_details.is_chat_moderator,
                            }

                            try:
                                producer.produce(
                                    topic=KAFKA_TOPIC,
                                    key=item.id.encode("utf-8"),
                                    value=json.dumps(chat_data).encode("utf-8"),
                                    callback=delivery_report,
                                )

                                producer.poll(0)

                            except (KafkaException, BufferError) as kafka_err:
                                producer.flush()
                                logger.warning(
                                    f"Kafka production failed or buffer full: {kafka_err}"
                                )

                        # Log the chat message at the INFO level
                        logger.info(f"CHAT: [{author}]: {message}: {published_at_ms}")
                        next_page_token = response.next_page_token
                        if not next_page_token:
                            logger.info("Stream ended or encountered terminal message.")
                            break

            except grpc.RpcError as e:
                # Check if the error is due to a natural close (EOF/stream end) or an issue
                logger.error(f"\n--- gRPC Error: {e.code()} - {e.details()} ---")

                if e.code() == grpc.StatusCode.UNAUTHENTICATED:
                    logger.error(
                        "Authentication failed. Check if your OAuth token is expired or invalid."
                    )
                    break

                elif (
                    e.code() == grpc.StatusCode.UNAVAILABLE
                    or e.code() == grpc.StatusCode.INTERNAL
                ):
                    logger.error(
                        "Connection issue. Attempting reconnect in 5 seconds..."
                    )
                    time.sleep(5)
                    continue

                else:
                    break

            except KeyboardInterrupt:
                logger.info("\n--- Streaming stopped by user. ---")
                break

        if producer:
            logger.info("Flushing remaining Kafka messages (waiting up to 30s)...")
            remaining_messages = producer.flush(timeout=30)
            if remaining_messages > 0:
                logger.error(
                    f"WARNING: {remaining_messages} messages still in queue after flush timeout. Data loss possible."
                )
            else:
                logger.info("All messages successfully flushed to Kafka.")


# --- Push Handler (The Flask Entry Point) ---


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
                    logger.info(f"Received Pub/Sub trigger for Video ID: {video_id}")
                    live_chat_id = get_live_chat_id(video_id)

                    if live_chat_id:
                        logger.info(
                            f"Live Chat ID {live_chat_id} found. Starting ingestion thread."
                        )

                        ingestion_thread = threading.Thread(
                            target=youtube_ingest, args=(live_chat_id,)
                        )
                        ingestion_thread.daemon = True
                        ingestion_thread.start()

                        return "Ingestion thread started.", 200

                    else:
                        logger.warning(
                            f"Could not find active live chat ID for video {video_id}. Returning 200 to avoid Pub/Sub retry."
                        )
                        return "No active chat found.", 200

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
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)  # nosec B104
