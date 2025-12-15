from flask import Blueprint, request, jsonify
from controllers.predictor import PredictionController

prediction_router = Blueprint("prediction_router", __name__)


@prediction_router.route("/predict", methods=["POST"])
def predict_route():
    try:
        req_data = request.get_json()

        if not req_data or "live_chat_id" not in req_data:
            return jsonify({"error": "Missing field: live_chat_id"}), 400

        live_chat_id = req_data["live_chat_id"]

        controller = PredictionController()
        result = controller.generate_prediction(live_chat_id=live_chat_id)

        if result is None:
            return jsonify(
                {
                    "status": "success",
                    "message": "Not enough data to generate prediction yet.",
                    "data": None,
                }
            ), 200

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500
