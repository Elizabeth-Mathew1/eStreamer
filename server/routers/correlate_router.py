from flask import Blueprint, request, jsonify
from controllers.correlate import CorrelationController

correlate_router = Blueprint("correlate", __name__)
controller = CorrelationController()


@correlate_router.route("/correlate", methods=["GET"])
def get_correlation_snapshot():
    video_id = request.args.get("video_id")
    if not video_id:
        return jsonify({"error": "Missing video_id query parameter"}), 400

    try:
        result = controller.get_live_correlation(video_id)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
