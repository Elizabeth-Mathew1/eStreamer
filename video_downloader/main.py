import os
import sys
import logging
import threading
from flask import Flask
from flask_cors import CORS

from controllers.consumer import VideoTimeStampConsumerController

# --- 1. FORCE LOGS TO STDOUT (So Cloud Run sees them) ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)


@app.route("/")
def health_check():
    return "Service is running", 200


def run_consumer():
    """Wrapper to handle errors and keep the thread clean."""
    logger.info("🧵 Background Thread Started...")
    try:
        controller = VideoTimeStampConsumerController()
        controller.consume()
    except Exception as e:
        logger.critical(f"Consumer crashed: {e}")


if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
    logger.info("🚀 App starting. Launching Consumer Thread...")
    listener_thread = threading.Thread(target=run_consumer, daemon=True)
    listener_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)  # nosec B104
