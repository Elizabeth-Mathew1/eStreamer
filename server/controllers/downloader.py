import logging
import uuid
import json
from datetime import datetime, timezone
from google.cloud import firestore
from confluent_kafka import Producer
from google.cloud.firestore_v1.base_query import FieldFilter

from settings import (
    FIRESTORE_DB_NAME,
    COLLECTION_NAME,
    VIDEO_DOWNLOADER_JOB_COLLECTION_NAME,
    KAFKA_VIDEO_DOWNLOADER_JOB_TOPIC,
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_API_SECRET,
    KAFKA_API_KEY,
    STREAM_METADATA_COLLECTION_NAME,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class DownloadController:
    THRESHOLD = 0.7

    def __init__(self, video_id: str) -> None:
        self.db = firestore.Client(database=FIRESTORE_DB_NAME)
        self.video_id = video_id
        self.live_video_url = None
        self.producer_config = {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "security.protocol": "SASL_SSL",
            "sasl.mechanisms": "PLAIN",
            "sasl.username": KAFKA_API_KEY,
            "sasl.password": KAFKA_API_SECRET,
        }
        self.producer = Producer(self.producer_config)

    def fetch_high_sentiment_clips(self) -> tuple[list, int]:
        """
        1. Gets Stream Metadata (Start Time, Chat ID).
        2. Scans summaries to find clips.
        3. Calculates Overall Sentiment % for the whole stream.
        Returns: (List of clips, Overall Sentiment Integer)
        """
        logger.info(f"Fetching metadata for Video ID: {self.video_id}")

        meta_ref = self.db.collection(STREAM_METADATA_COLLECTION_NAME).document(
            self.video_id
        )
        meta_doc = meta_ref.get()

        if not meta_doc.exists:
            logger.warning(
                f"No metadata found for video {self.video_id}. Cannot calculate timestamps."
            )
            return [], 0

        meta_data = meta_doc.to_dict()
        stream_start_time = meta_data.get("stream_start_time")
        live_chat_id = meta_data.get("live_chat_id")
        self.live_video_url = meta_data.get("live_video_url")

        if not stream_start_time or not live_chat_id:
            logger.warning("Metadata missing 'stream_start_time' or 'live_chat_id'.")
            return [], 0

        logger.info(
            f"Found Stream Start: {stream_start_time} | Chat ID: {live_chat_id}"
        )

        query = (
            self.db.collection(COLLECTION_NAME)
            .where(filter=FieldFilter("live_chat_id", "==", live_chat_id))
            .order_by("avg_sentiment", direction=firestore.Query.DESCENDING)
        )

        docs = query.stream()
        clips = []

        total_sentiment_score = 0.0
        window_count = 0

        logger.info(f"Scanning windows for {self.live_video_url}...")

        for doc in docs:
            data = doc.to_dict()
            sentiment = data.get("avg_sentiment", 0)

            total_sentiment_score += sentiment
            window_count += 1

            if sentiment >= self.THRESHOLD:
                win_start = data.get("window_start_time")
                win_end = data.get("window_end_time")

                if not win_start:
                    continue

                start_seconds = (win_start - stream_start_time).total_seconds()

                if win_end:
                    duration = (win_end - win_start).total_seconds()
                else:
                    duration = 60.0

                if start_seconds < 0:
                    continue

                clips.append(
                    {
                        "start": int(start_seconds),
                        "duration": int(duration),
                        "score": sentiment,
                        "window_id": doc.id,
                    }
                )

        clips.sort(key=lambda x: x["start"])

        overall_percentage = 0
        if window_count > 0:
            avg_raw = total_sentiment_score / window_count
            overall_percentage = int(avg_raw * 100)

        logger.info(
            f"Found {len(clips)} clips. Overall Sentiment: {overall_percentage}%"
        )
        return clips, overall_percentage

    def delivery_report(self, err, msg):
        """Callback for Kafka producer"""
        if err:
            logger.error(f"Message failed: {err}")
        else:
            logger.info(f"Sent task to {msg.topic()} [{msg.partition()}]")

    def download(self):
        job_id = str(uuid.uuid4())

        clips_list, overall_sentiment = self.fetch_high_sentiment_clips()
        total_clips = len(clips_list)

        if total_clips == 0:
            logger.warning("No clips found. Job will not be created.")
            return None

        logger.info(f"Creating Job {job_id} for {total_clips} clips.")

        self.db.collection(VIDEO_DOWNLOADER_JOB_COLLECTION_NAME).document(job_id).set(
            {
                "job_id": job_id,
                "video_id": self.video_id,
                "live_video_url": self.live_video_url,
                "status": "PROCESSING",
                "total_clips_expected": total_clips,
                "clips_completed_count": 0,
                "video_urls": [],
                "created_at": datetime.now(timezone.utc),
                "failed_clips": 0,
                "overall_sentiment_percentage": overall_sentiment,
            }
        )

        for index, clip in enumerate(clips_list):
            output_filename = f"processed_videos/{job_id}/{index}.mp4"

            task_payload = {
                "job_id": job_id,
                "video_url": self.live_video_url,
                "start_time": clip["start"],
                "duration": clip["duration"],
                "output_path": output_filename,
            }

            self.producer.produce(
                KAFKA_VIDEO_DOWNLOADER_JOB_TOPIC,
                json.dumps(task_payload).encode("utf-8"),
                callback=self.delivery_report,
            )

        self.producer.flush()
        logger.info(f"Job {job_id} dispatch complete.")
        return job_id
