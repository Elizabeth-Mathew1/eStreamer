from flask import Blueprint, request, jsonify
from controllers.downloader import DownloadController

download_router = Blueprint("download_router", __name__)


@download_router.route("/download", methods=["POST"])
def predict_route():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON body"}), 400

        live_video_url = data.get("live_video_url")
        if not live_video_url:
            return jsonify({"error": "Missing 'live_video_url'"}), 400

        controller = DownloadController(live_video_url=live_video_url)
        result = controller.download()

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500
