import logging
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from settings.base import FIRESTORE_DB_NAME, VIDEO_DOWNLOADER_JOB_COLLECTION_NAME

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class VideoStatusPollController:
    def __init__(self):
        self.db = firestore.Client(database=FIRESTORE_DB_NAME)

    def poll(self, video_url: str):
        logger.info(f"🔍 [Poll] Checking status for video: {video_url}")

        query = (
            self.db.collection(VIDEO_DOWNLOADER_JOB_COLLECTION_NAME)
            .where(filter=FieldFilter("live_video_url", "==", video_url))
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(1)
        )

        try:
            docs = list(query.stream())
        except Exception as e:
            logger.error(f"[Poll] Firestore query failed: {e}")
            return None

        if not docs:
            logger.info("[Poll] No previous jobs found for this URL.")
            return None

        data = docs[0].to_dict()
        job_id = data.get("job_id")
        status = data.get("status", "PENDING")

        total = data.get("total_clips_expected", 1)
        completed = data.get("clips_completed_count", 0)
        failed = data.get("failed_clips", 0)
        overall_sentiment = data.get("overall_sentiment_percentage", 0)

        percent = int((completed / total) * 100) if total > 0 else 0

        logger.info(
            f"[Poll] Found Job {job_id} | Status: {status} | Progress: {percent}%"
        )

        return {
            "job_id": job_id,
            "status": status,
            "progress": {
                "current": completed,
                "total": total,
                "percent": percent,
                "failed": failed,
            },
            "video_urls": data.get("video_urls", []),
            "created_at": data.get("created_at"),
            "overall_sentiment": overall_sentiment,
        }
