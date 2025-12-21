from datetime import datetime, timezone
import uuid
import json
from google.cloud import firestore
from confluent_kafka import Producer
from google.cloud.firestore_v1.base_query import FieldFilter

from settings import (
    FIRESTORE_DB_NAME,
    COLLECTION_NAME,
    VIDEO_DOWNLOADER_JOB_COLLECTION_NAME,
    KAFKA_VIDEO_DOWNLOADER_JOB_TOPIC,
)


class DownloadController:
    THRESHOLD = 0.6

    def __init__(self, live_video_url: str) -> None:
        self.db = firestore.Client(database=FIRESTORE_DB_NAME)
        self.live_video_url = live_video_url
        self.producer_config = {"bootstrap.servers": "localhost:29092"}
        self.producer = Producer(self.producer_config)

    def fetch_high_sentiment_clips(self) -> list:
        """
        Finds 1-minute windows with high sentiment and converts them
        to relative video timestamps.

        Args:
            live_video_url (str): The ID of the chat/stream.
            stream_start_time (datetime): CRITICAL. The UTC time the stream actually started.
                                        (e.g., 2025-12-19 11:00:00 UTC)
            threshold (float): Minimum sentiment score to accept (e.g., 0.5 or 1).

        Returns:
            list[dict]: List of clips [{'start': 300, 'duration': 60}, ...]
        """
        query = (
            self.db.collection(COLLECTION_NAME)
            .where(filter=FieldFilter("live_video_url", "==", self.live_video_url))
            .where(filter=FieldFilter("avg_sentiment", ">=", self.THRESHOLD))
            .order_by("avg_sentiment", direction=firestore.Query.DESCENDING)
        )

        docs = query.stream()
        clips = []

        print(f"Scanning for windows with sentiment >= {self.THRESHOLD}...")

        for doc in docs:
            data = doc.to_dict()
            stream_start_time = data.get("stream_start_time")

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
                print(f"Skipped window {doc.id} (Negative timestamp: {start_seconds})")
                continue

            clips.append(
                {
                    "start": int(start_seconds),
                    "duration": int(duration),
                    "score": data.get("average_sentiment", 0),
                    "window_id": doc.id,
                }
            )

        clips.sort(key=lambda x: x["start"])

        print(f"Found {len(clips)} high-sentiment intervals.")
        return clips

    def delivery_report(self, err, msg):
        if err:
            print(f"Message failed: {err}")
        else:
            print(f"Sent to {msg.topic()} [{msg.partition()}]")

    def download(self):
        job_id = str(uuid.uuid4())
        clips_list = self.fetch_high_sentiment_clips()
        total_clips = len(clips_list)

        print(f"Creating Job {job_id} for {total_clips} clips.")

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
            output_filename = (
                f"processed_videos/{self.live_video_url}/{job_id}_{index}.mp4"
            )

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
        return job_id
