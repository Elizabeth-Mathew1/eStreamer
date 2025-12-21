import os
import threading

from flask import Flask

from controllers.consumer import VideoTimeStampConsumerController


app = Flask(__name__)

listener_thread = threading.Thread(
    target=VideoTimeStampConsumerController().consume(), daemon=True
)
listener_thread.start()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)  # nosec B104
