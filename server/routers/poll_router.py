from flask import Blueprint, request, jsonify

from controllers.poll import VideoStatusPollController


poll_router = Blueprint("poll_router", __name__)


@poll_router.route("/video/poll", methods=["GET"])
def poll_video_job():
    video_url = request.args.get("live_video_url")
    if not video_url:
        return jsonify({"error": "Missing 'live_video_url' parameter"}), 400

    result = VideoStatusPollController().poll(video_url=video_url)

    if result is None:
        return jsonify(
            {"status": "NOT_FOUND", "message": "No jobs found for this video"}
        ), 404
    return jsonify(result), 200
