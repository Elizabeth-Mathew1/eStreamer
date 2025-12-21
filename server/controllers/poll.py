from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from settings.base import FIRESTORE_DB_NAME, VIDEO_DOWNLOADER_JOB_COLLECTION_NAME


class VideoStatusPollController:
    def __init__(self):
        self.db = firestore.Client(database=FIRESTORE_DB_NAME)

    def poll(self, video_url: str):
        query = (
            self.db.collection(VIDEO_DOWNLOADER_JOB_COLLECTION_NAME)
            .where(filter=FieldFilter("live_video_url", "==", video_url))
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(1)
        )

        docs = list(query.stream())

        if not docs:
            return None

        data = docs[0].to_dict()

        total = data.get("total_clips_expected", 1)
        job_id = data.get("job_id")
        completed = data.get("clips_completed_count", 0)
        failed = data.get("failed_clips", 0)

        percent = int((completed / total) * 100) if total > 0 else 0

        return {
            "job_id": job_id,
            "status": data.get("status", "PENDING"),
            "progress": {
                "current": completed,
                "total": total,
                "percent": percent,
                "failed": failed,
            },
            "video_urls": data.get("video_urls", []),
            "created_at": data.get("created_at"),
        }
