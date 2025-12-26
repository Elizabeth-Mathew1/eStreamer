import yt_dlp
import json
import os
import shutil
import tempfile
import logging
from confluent_kafka import Consumer, KafkaError, Producer
from google.cloud import storage
from pathlib import Path

from settings import (
    KAFKA_BOOTSTRAP_SERVERS,
    BUCKET_NAME,
    KAFKA_VIDEO_DOWNLOADER_JOB_TOPIC,
    KAFKA_VIDEO_DOWNLOADER_STATUS_TOPIC,
    KAFKA_API_KEY,
    KAFKA_API_SECRET,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class VideoTimeStampConsumerController:
    BASE_DIR = Path(__file__).resolve().parent.parent
    TEMP_DIR = BASE_DIR / "temp"

    def __init__(self):
        logger.info("Initializing VideoTimeStampConsumerController...")

        self.consumer_configs = {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "security.protocol": "SASL_SSL",
            "sasl.mechanisms": "PLAIN",
            "sasl.username": KAFKA_API_KEY,
            "sasl.password": KAFKA_API_SECRET,
            "group.id": "video-consumer",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }

        try:
            self.consumer = Consumer(self.consumer_configs)
            logger.info("Kafka Consumer initialized successfully.")
        except Exception as e:
            logger.critical(f"Failed to initialize Kafka Consumer: {e}")
            raise e

        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(BUCKET_NAME)

        self.producer_conf = {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "security.protocol": "SASL_SSL",
            "sasl.mechanisms": "PLAIN",
            "sasl.username": KAFKA_API_KEY,
            "sasl.password": KAFKA_API_SECRET,
        }
        self.producer = Producer(self.producer_conf)

        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Temp directory set to: {self.TEMP_DIR}")

    def delivery_report(self, err, msg):
        """Called once for each message produced to indicate delivery result."""
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.info(f"Result sent to {msg.topic()} [Partition: {msg.partition()}]")

    def upload_video_to_gcp(self, local_path, destination_blob_name):
        logger.info(
            f"Starting upload: {local_path.name} -> gs://{BUCKET_NAME}/{destination_blob_name}"
        )
        try:
            blob = self.bucket.blob(destination_blob_name)
            blob.upload_from_filename(str(local_path))
            logger.info(f"Upload successful. Public URL: {blob.public_url}")
            return blob.public_url
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise e

    def download_video(self, job_id: str, start: int, duration: int, url: str):
        output_filename = self.TEMP_DIR / f"{job_id}.mp4"
        logger.info(
            f"Preparing download for Job {job_id} | URL: {url} | Start: {start}s | Duration: {duration}s"
        )

        gcp_secret_path = Path("/secrets/cookies.txt")
        local_dev_path = self.BASE_DIR / "cookies.txt"

        cookie_source = None
        temp_cookie_path = None

        if gcp_secret_path.exists():
            cookie_source = gcp_secret_path
            logger.info(f"Found GCP Secret cookies at: {gcp_secret_path}")
        elif local_dev_path.exists():
            cookie_source = local_dev_path
            logger.info(f"Found Local Dev cookies at: {local_dev_path}")
        else:
            logger.warning(
                "No cookie file found! Download may fail due to Bot Detection."
            )

        if cookie_source:
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb", delete=False, suffix=".txt"
                ) as tmp_file:
                    with open(cookie_source, "rb") as src:
                        shutil.copyfileobj(src, tmp_file)
                    temp_cookie_path = tmp_file.name
                logger.info(f"Copied cookies to temp file: {temp_cookie_path}")
            except Exception as e:
                logger.error(f"Failed to copy cookie file: {e}")

                temp_cookie_path = str(cookie_source)

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

        if temp_cookie_path:
            ydl_opts["cookiefile"] = temp_cookie_path

        logger.debug(f"yt-dlp options: {ydl_opts}")

        try:
            logger.info(f"Executing yt-dlp for Job {job_id}...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            if output_filename.exists():
                file_size = output_filename.stat().st_size / (1024 * 1024)
                logger.info(
                    f"Download finished: {output_filename} ({file_size:.2f} MB)"
                )
                return output_filename
            else:
                logger.error(
                    f"Download appeared to finish, but file {output_filename} is missing!"
                )
                return None

        except Exception as e:
            logger.error(f"Download failed for Job {job_id}: {e}")
            return None
        finally:
            if temp_cookie_path and os.path.exists(temp_cookie_path):
                if temp_cookie_path != str(gcp_secret_path) and temp_cookie_path != str(
                    local_dev_path
                ):
                    try:
                        os.remove(temp_cookie_path)
                        logger.info(f"Removed temp cookie file: {temp_cookie_path}")
                    except OSError:
                        pass

    def cleanup(self, local_path):
        if local_path.exists():
            try:
                os.remove(local_path)
                logger.info(f"Cleaned up video file: {local_path}")
            except Exception as e:
                logger.error(f"Failed to cleanup file {local_path}: {e}")

    def consume(self):
        self.consumer.subscribe([KAFKA_VIDEO_DOWNLOADER_JOB_TOPIC])
        logger.info(f"Subscribed to topic: {KAFKA_VIDEO_DOWNLOADER_JOB_TOPIC}")
        logger.info("Waiting for messages...")

        try:
            while True:
                msg = self.consumer.poll(1.0)

                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Consumer Error: {msg.error()}")
                        continue

                try:
                    logger.info(
                        f"Received Message [Partition: {msg.partition()} | Offset: {msg.offset()}]"
                    )

                    data = json.loads(msg.value().decode("utf-8"))
                    job_id = data.get("job_id")
                    logger.info(f"Processing Job: {job_id}")

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
                        self.producer.flush()

                except Exception as e:
                    logger.exception(
                        f"Worker Failed for Job {job_id if 'job_id' in locals() else 'Unknown'}"
                    )

                    if "job_id" in locals():
                        error_msg = {
                            "job_id": job_id,
                            "status": "FAILED",
                            "error": str(e),
                        }
                        self.producer.produce(
                            KAFKA_VIDEO_DOWNLOADER_STATUS_TOPIC,
                            json.dumps(error_msg).encode("utf-8"),
                        )
                        self.producer.flush()

        except KeyboardInterrupt:
            logger.info("Stopping consumer...")
        finally:
            self.consumer.close()
            self.producer.flush()
            logger.info("Consumer closed successfully.")


if __name__ == "__main__":
    controller = VideoTimeStampConsumerController()
    controller.consume()
