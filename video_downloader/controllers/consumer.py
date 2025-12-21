import yt_dlp
import json
import os

from confluent_kafka import Consumer, KafkaError, Producer
from google.cloud import storage
from pathlib import Path

from settings import (
    KAFKA_BOOTSTRAP_SERVERS,
    BUCKET_NAME,
    KAFKA_VIDEO_DOWNLOADER_JOB_TOPIC,
    KAFKA_VIDEO_DOWNLOADER_STATUS_TOPIC,
)


class VideoTimeStampConsumerController:
    BASE_DIR = Path(__file__).resolve().parent.parent
    TEMP_DIR = BASE_DIR / "temp"

    def __init__(self):
        self.consumer_configs = {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "group.id": "video-cosnumer",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
        self.consumer = Consumer(self.consumer_configs)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(BUCKET_NAME)
        self.producer_conf = {"bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS}

        self.producer = Producer(self.producer_conf)

    def delivery_report(err, msg):
        """Called once for each message produced to indicate delivery result."""
        if err is not None:
            print(f"Message delivery failed: {err}")
        else:
            print(f"Result sent to {msg.topic()} [{msg.partition()}]")

    def upload_video_to_gcp(self, local_path, destination_blob_name):
        print(f"Uploading {local_path.name}...")
        blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_filename(str(local_path))
        return blob.public_url

    def download_video(self, job_id: str, start: int, duration: int, url: str):
        output_filename = self.TEMP_DIR / f"{job_id}.mp4"

        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": str(output_filename),
            "external_downloader": "ffmpeg",
            "external_downloader_args": {
                "ffmpeg_i": ["-ss", str(start), "-t", str(duration)]
            },
            "overwrites": True,
            "quiet": True,
        }

        print(f"Starting download for Job {job_id}...")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return output_filename
        except Exception as e:
            print(f"Download failed: {e}")
            return None

    def cleanup(self, local_path):
        if local_path.exists():
            os.remove(local_path)

    def consume(self):
        self.consumer.subscribe([KAFKA_VIDEO_DOWNLOADER_JOB_TOPIC])
        try:
            while True:
                msg = self.consumer.poll(1.0)

                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        print(f"Consumer Error: {msg.error()}")
                        continue

                try:
                    data = json.loads(msg.value().decode("utf-8"))
                    job_id = data.get("job_id")
                    print(f"Processing Job: {job_id}")

                    local_file = self.download_video(
                        url=data["video_url"],
                        start=data["start_time"],
                        duration=data["duration"],
                        job_id=job_id,
                    )
                    if local_file:
                        public_url = self.upload_video_to_gcp(
                            local_file, data["output_path"]
                        )
                        self.cleanup(local_file)

                        self.consumer.commit(message=msg, asynchronous=False)

                        result_msg = {
                            "job_id": job_id,
                            "status": "COMPLETED",
                            "gcs_url": public_url,
                        }

                        self.producer.produce(
                            KAFKA_VIDEO_DOWNLOADER_STATUS_TOPIC,
                            json.dumps(result_msg).encode("utf-8"),
                            callback=self.delivery_report,
                        )

                except Exception as e:
                    print(f"Worker Failed: {e}")
                    error_msg = {"job_id": job_id, "status": "FAILED", "error": str(e)}
                    self.producer.produce(
                        KAFKA_VIDEO_DOWNLOADER_STATUS_TOPIC,
                        json.dumps(error_msg).encode("utf-8"),
                    )

        except KeyboardInterrupt:
            pass
        finally:
            self.consumer.close()
            self.producer.flush()
