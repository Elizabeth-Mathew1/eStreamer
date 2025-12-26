from flask import Blueprint, request, jsonify
from controllers.downloader import DownloadController

download_router = Blueprint("download_router", __name__)


@download_router.route("/download", methods=["POST"])
def predict_route():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON body"}), 400

        video_id = data.get("video_id")
        if not video_id:
            return jsonify({"error": "Missing 'video_id'"}), 400

        controller = DownloadController(video_id=video_id)
        result = controller.download()

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500
