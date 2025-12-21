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
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class DownloadController:
    THRESHOLD = 0.6

    def __init__(self, live_video_url: str) -> None:
        self.db = firestore.Client(database=FIRESTORE_DB_NAME)
        self.live_video_url = live_video_url
        self.producer_config = {"bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS}
        self.producer = Producer(self.producer_config)

    def fetch_high_sentiment_clips(self) -> list:
        """
        Finds 1-minute windows with high sentiment and converts them
        to relative video timestamps.
        """
        query = (
            self.db.collection(COLLECTION_NAME)
            .where(filter=FieldFilter("live_video_url", "==", self.live_video_url))
            .where(filter=FieldFilter("avg_sentiment", ">=", self.THRESHOLD))
            .order_by("avg_sentiment", direction=firestore.Query.DESCENDING)
        )

        docs = query.stream()
        clips = []

        logger.info(
            f"🔎 Scanning for windows with sentiment >= {self.THRESHOLD} for {self.live_video_url}..."
        )

        for doc in docs:
            data = doc.to_dict()
            stream_start_time = data.get("stream_start_time")
            win_start = data.get("window_start_time")
            win_end = data.get("window_end_time")

            if not win_start or not stream_start_time:
                continue

            start_seconds = (win_start - stream_start_time).total_seconds()

            if win_end:
                duration = (win_end - win_start).total_seconds()
            else:
                duration = 60.0

            if start_seconds < 0:
                logger.warning(
                    f"⚠️ Skipped window {doc.id} (Negative timestamp: {start_seconds}s)"
                )
                continue

            clips.append(
                {
                    "start": int(start_seconds),
                    "duration": int(duration),
                    "score": data.get("avg_sentiment", 0),
                    "window_id": doc.id,
                }
            )

        clips.sort(key=lambda x: x["start"])

        logger.info(f"Found {len(clips)} high-sentiment intervals.")
        return clips

    def delivery_report(self, err, msg):
        """Callback for Kafka producer"""
        if err:
            logger.error(f"Message failed: {err}")
        else:
            logger.info(f"Sent task to {msg.topic()} [{msg.partition()}]")

    def download(self):
        job_id = str(uuid.uuid4())

        clips_list = self.fetch_high_sentiment_clips()
        total_clips = len(clips_list)

        if total_clips == 0:
            logger.warning(" No clips found. Job will not be created.")
            return None

        logger.info(f"Creating Job {job_id} for {total_clips} clips.")

        # 2. Save Job State to Firestore
        self.db.collection(VIDEO_DOWNLOADER_JOB_COLLECTION_NAME).document(job_id).set(
            {
                "job_id": job_id,
                "live_video_url": self.live_video_url,
                "status": "PROCESSING",
                "total_clips_expected": total_clips,
                "clips_completed_count": 0,
                "video_urls": [],
                "created_at": datetime.now(timezone.utc),
                "failed_clips": 0,
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
        logger.info(f"🏁 Job {job_id} dispatch complete.")
        return job_id
