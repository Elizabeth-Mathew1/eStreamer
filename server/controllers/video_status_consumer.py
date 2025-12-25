import logging
import json
from google.cloud import firestore
from confluent_kafka import Consumer

from settings.base import (
    FIRESTORE_DB_NAME,
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_VIDEO_DOWNLOADER_STATUS_TOPIC,
    VIDEO_DOWNLOADER_JOB_COLLECTION_NAME,
    KAFKA_API_KEY,
    KAFKA_API_SECRET,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class VideoStatusController:
    def __init__(self):
        self.db = firestore.Client(database=FIRESTORE_DB_NAME)
        self.consumer_conf = {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "security.protocol": "SASL_SSL",
            "sasl.mechanisms": "PLAIN",
            "sasl.username": KAFKA_API_KEY,
            "sasl.password": KAFKA_API_SECRET,
            "group.id": "video-status-group",
            "auto.offset.reset": "earliest",
        }
        self.consumer = Consumer(self.consumer_conf)

    def start_result_listener(self):
        """Runs in background thread on Main Server"""
        self.consumer.subscribe([KAFKA_VIDEO_DOWNLOADER_STATUS_TOPIC])

        logger.info(
            f"🎧 [StatusListener] Main Server listening for results on '{KAFKA_VIDEO_DOWNLOADER_STATUS_TOPIC}'..."
        )

        try:
            while True:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    logger.error(f"[StatusListener] Consumer Error: {msg.error()}")
                    continue

                try:
                    data = json.loads(msg.value().decode("utf-8"))
                    self._handle_job_completion(data)
                except Exception as e:
                    logger.error(f"[StatusListener] Failed to process message: {e}")

        finally:
            self.consumer.close()
            logger.info("[StatusListener] Consumer closed.")

    def _handle_job_completion(self, data):
        job_id = data.get("job_id")
        status = data.get("status")
        gcs_url = data.get("gcs_url")

        logger.info(f"[StatusListener] Received result for Job {job_id}: {status}")

        doc_ref = self.db.collection(VIDEO_DOWNLOADER_JOB_COLLECTION_NAME).document(
            job_id
        )

        @firestore.transactional
        def update_in_transaction(transaction, ref):
            snapshot = ref.get(transaction=transaction)
            if not snapshot.exists:
                logger.warning(
                    f"[StatusListener] Job {job_id} not found in Firestore. Skipping update."
                )
                return

            doc_data = snapshot.to_dict()

            current_completed = doc_data.get("clips_completed_count", 0)
            total_expected = doc_data.get("total_clips_expected", 1)
            current_urls = doc_data.get("video_urls", [])
            current_failed = doc_data.get("failed_clips", 0)

            updates = {}

            if status == "COMPLETED" and gcs_url:
                current_urls.append(gcs_url)
                updates["video_urls"] = current_urls
            elif status == "FAILED":
                current_failed += 1
                updates["failed_clips"] = current_failed

            new_count = current_completed + 1
            updates["clips_completed_count"] = new_count

            if new_count >= total_expected:
                if current_failed == total_expected:
                    updates["status"] = "FAILED"
                elif current_failed > 0:
                    updates["status"] = "PARTIALLY_COMPLETED"
                else:
                    updates["status"] = "COMPLETED"

                logger.info(
                    f"🏁 [StatusListener] Job {job_id} fully finished. Final Status: {updates['status']}"
                )

            transaction.update(ref, updates)

        # Run the transaction
        transaction = self.db.transaction()
        try:
            update_in_transaction(transaction, doc_ref)
        except Exception as e:
            logger.error(f"[StatusListener] Transaction failed for Job {job_id}: {e}")
