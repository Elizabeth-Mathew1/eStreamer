from flask import Blueprint, request, jsonify
from controllers.analyzer import AnalyzerController

analyze_router = Blueprint("analyze_router", __name__)


@analyze_router.route("/analyze", methods=["POST"])
def predict_route():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON body"}), 400

        video_id = data.get("video_id")
        if not video_id:
            return jsonify({"error": "Missing 'video_id'"}), 400

        duration_seconds = data.get("duration")
        if not duration_seconds:
            duration_seconds = 60

        controller = AnalyzerController(
            duration_seconds=duration_seconds, video_id=video_id
        )
        result = controller.analyze()

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500
