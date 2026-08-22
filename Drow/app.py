import cv2
import base64
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from detector import DrowsinessDetector


app=Flask(__name__)
CORS(app)

# One detector instance — shared across all requests
detector = DrowsinessDetector()

@app.route("/",methods=["GET"])
def home():
    return jsonify({"status" : "running"})

@app.route("/process",methods=["POST"])
def process():
    # Get base64 image from React
    data=request.get_json()
    b64=data["frame"].split(",")[1]
    img_bytes=base64.b64decode(b64)
    np_arr    = np.frombuffer(img_bytes, np.uint8)
    frame     = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # Run detection
    result = detector.process(frame)
    return jsonify(result)

@app.route("/reset", methods=["POST"])
def reset():
    detector.reset()
    return jsonify({"message": "Session reset"})

if __name__ == "__main__":
    app.run(debug=True, port=5004)