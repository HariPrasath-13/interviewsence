import cv2
import base64
import numpy as np
from deepface import DeepFace

class EmotionDetector:
    def __init__(self):
        # Load OpenCV Haar Cascade Face Classifier
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        if self.face_cascade.empty():
            print("Warning: Haar Cascade face classifier failed to load. Ensure OpenCV is installed correctly.")

    def base64_to_cv2(self, base64_str):
        """Converts a base64 encoded image string (with or without HTML prefix) to an OpenCV BGR image."""
        try:
            if "," in base64_str:
                base64_str = base64_str.split(",")[1]
            img_data = base64.b64decode(base64_str)
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            print(f"Error decoding base64 image: {e}")
            return None

    def analyze_frame(self, frame):
        """
        Analyzes a single OpenCV image frame for faces and performs emotional analysis using DeepFace.
        Returns a dictionary containing face details, dominant emotion, confidence, and probabilities.
        """
        if frame is None:
            return {
                "face_detected": False,
                "dominant_emotion": "None",
                "confidence": 0.0,
                "emotion_probabilities": {},
                "face_box": None,
                "error": "Invalid or empty image frame"
            }

        try:
            # 1. Pre-detection: Use OpenCV Haar cascades to verify face presence and get coordinates.
            # This is fast and acts as a filter before running heavy DeepFace models.
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5, 
                minSize=(60, 60) # Only care about faces of reasonable size
            )

            if len(faces) == 0:
                return {
                    "face_detected": False,
                    "dominant_emotion": "None",
                    "confidence": 0.0,
                    "emotion_probabilities": {},
                    "face_box": None
                }

            # Use the largest face found by bounding area
            x, y, w, h = max(faces, key=lambda rect: rect[2] * rect[3])

            # 2. Emotion analysis using DeepFace.
            # We pass the image and tell DeepFace not to enforce face detection since we already verified it.
            # We restrict actions to ['emotion'] to keep it fast.
            # detector_backend is "opencv" as requested.
            analysis = DeepFace.analyze(
                img_path=frame,
                actions=['emotion'],
                enforce_detection=False,
                detector_backend="opencv",
                silent=True
            )

            # DeepFace.analyze returns a list of dictionaries if it detects multiple faces or a single dict.
            if isinstance(analysis, list):
                res = analysis[0]
            else:
                res = analysis

            dominant_emotion_raw = res.get("dominant_emotion", "neutral")
            emotion_probs_raw = res.get("emotion", {})

            # Clean and format output
            dominant_emotion = str(dominant_emotion_raw).lower()
            
            # Map DeepFace raw values (percents 0-100)
            emotion_probabilities = {}
            for emotion_name, prob_val in emotion_probs_raw.items():
                # Store percentage values rounded to 2 decimal places
                emotion_probabilities[emotion_name.lower()] = round(float(prob_val), 2)
            
            # Use raw confidence score (represented by probability of dominant emotion)
            confidence = emotion_probabilities.get(dominant_emotion, 0.0)

            return {
                "face_detected": True,
                "dominant_emotion": dominant_emotion,
                "confidence": confidence,
                "emotion_probabilities": emotion_probabilities,
                "face_box": {
                    "x": int(x),
                    "y": int(y),
                    "width": int(w),
                    "height": int(h)
                }
            }

        except Exception as e:
            print(f"DeepFace analysis error: {e}")
            # Fallback error recovery
            return {
                "face_detected": False,
                "dominant_emotion": "None",
                "confidence": 0.0,
                "emotion_probabilities": {},
                "face_box": None,
                "error": str(e)
            }
