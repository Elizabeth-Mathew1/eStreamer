from flask import Blueprint, request, jsonify
from controllers.predictor import PredictionController

prediction_router = Blueprint("prediction_router", __name__)


@prediction_router.route("/predict", methods=["POST"])
def predict_route():
    if not request.is_json:
        return jsonify({"error": "Invalid JSON"}), 400

    data = request.get_json()
    history_window = data.get("history")

    if not history_window:
        return jsonify({"error": "Missing 'history' field"}), 400

    return PredictionController().generate_prediction(history_window=history_window)
