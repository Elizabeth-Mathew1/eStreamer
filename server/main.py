import os
import json
from flask import Flask, request, jsonify
from google.cloud import pubsub_v1

PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
TOPIC_ID = os.environ.get("PUBSUB_TOPIC_ID")

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

app = Flask(__name__)


@app.route('/video_id', methods=['POST'])
def publish_video_id():
    # Publishes the video ID to the Pub/Sub topic

    # 1. Validate Request
    if not request.is_json:
        return jsonify({"error": "Missing or invalid JSON"}), 400

    data = request.get_json()
    video_id = data.get('video_id')

    if not video_id:
        return jsonify({"error": "Missing 'video_id' field"}), 400

    
    # 2. Prepare and Publish Message
    try:
        # The message data must be a byte string
        message_json = json.dumps({"video_id": video_id})
        message_bytes = message_json.encode("utf-8")

        # Publish the message
        future = publisher.publish(topic_path, data=message_bytes)
        message_id = future.result()

        return jsonify({
            "status": "success",
            "message": "Video ID queued for ingestion.",
            "message_id": message_id
        }), 202

    except Exception as e:
        app.logger.error(f"Pub/Sub Publish Error: {e}")
        return jsonify({"error": "Internal server error during publish"}), 500

        

if __name__ == '__main__':
    # Use gunicorn in production containers, but Flask's built-in server for local testing
    # Cloud Run automatically sets the PORT environment variable
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)


    