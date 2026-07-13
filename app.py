import os
import shutil

# Limit TensorFlow thread pool and log verbosity for resource-constrained server instances (e.g. Render Free Tier)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['TF_NUM_INTRAOP_THREADS'] = '1'
os.environ['TF_NUM_INTEROP_THREADS'] = '1'

# Set DeepFace Home directory to localized project path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ['DEEPFACE_HOME'] = BASE_DIR

# Ensure DeepFace weights directory exists and model weights are ready locally
weights_dir = os.path.join(BASE_DIR, '.deepface', 'weights')
os.makedirs(weights_dir, exist_ok=True)
src_weight = os.path.join(BASE_DIR, 'models', 'facial_expression_model_weights.h5')
dst_weight = os.path.join(weights_dir, 'facial_expression_model_weights.h5')

if os.path.exists(src_weight) and not os.path.exists(dst_weight):
    try:
        shutil.copy(src_weight, dst_weight)
        print("Model weights successfully prepared in .deepface/weights")
    except Exception as e:
        print(f"Error copying weights: {e}")


import uuid
import base64
import numpy as np
import cv2
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS

# Import project modules
import database as db
from emotion_detector import EmotionDetector
from report_generator import ReportGenerator

app = Flask(__name__)
CORS(app)

# Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = os.path.join(BASE_DIR, 'database')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
DB_PATH = os.path.join(DATABASE_DIR, 'interview_sense.db')

# Ensure directories exist
os.makedirs(DATABASE_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Initialize database
db.init_db(DB_PATH)

# Initialize Detector and Report Generator
detector = EmotionDetector()
reporter = ReportGenerator(DB_PATH, REPORTS_DIR)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/history')
def history_page():
    return render_template('history.html')

@app.route('/start', methods=['POST'])
@app.route('/api/start', methods=['POST'])
def start_session():
    try:
        session_id = str(uuid.uuid4())
        db.create_session(DB_PATH, session_id)
        return jsonify({
            "status": "success",
            "session_id": session_id,
            "message": "Session started successfully."
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to start session: {str(e)}"
        }), 500

@app.route('/process_frame', methods=['POST'])
@app.route('/api/process_frame', methods=['POST'])
def process_frame():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No JSON payload provided."}), 400
        
        session_id = data.get('session_id')
        frame_b64 = data.get('frame')
        elapsed_seconds = data.get('elapsed_seconds', 0.0)
        
        if not session_id:
            return jsonify({"status": "error", "message": "Missing session_id."}), 400
        if not frame_b64:
            return jsonify({"status": "error", "message": "Missing frame content."}), 400
            
        # Decode base64 image to CV2 matrix
        frame = detector.base64_to_cv2(frame_b64)
        if frame is None:
            return jsonify({"status": "error", "message": "Failed to decode frame image."}), 400
            
        # Run emotion detection
        analysis_result = detector.analyze_frame(frame)
        
        # If face is detected, store metrics in DB
        if analysis_result.get("face_detected"):
            db.add_frame_data(
                db_path=DB_PATH,
                session_id=session_id,
                elapsed_seconds=elapsed_seconds,
                emotion=analysis_result["dominant_emotion"],
                confidence=analysis_result["confidence"],
                probabilities=analysis_result["emotion_probabilities"]
            )
            
        return jsonify({
            "status": "success",
            "analysis": analysis_result
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error in processing frame: {str(e)}"
        }), 500

@app.route('/stop', methods=['POST'])
@app.route('/api/stop', methods=['POST'])
def stop_session():
    try:
        data = request.get_json()
        if not data or 'session_id' not in data:
            return jsonify({"status": "error", "message": "Missing session_id."}), 400
            
        session_id = data.get('session_id')
        duration = data.get('duration', 0.0)
        
        # Calculate analytics of the session
        details = db.get_session_details(DB_PATH, session_id)
        
        if not details:
            # Session exists but no faces were processed/detected
            dominant_emotion = "None"
            avg_confidence = 0.0
            pos_pct, neg_pct, neu_pct = 0.0, 0.0, 0.0
            recommendations = "No face analysis data was collected. Please make sure that you are positioned directly in front of the camera and that lighting is adequate."
        else:
            # Perform calculations
            emotions = [d['emotion'] for d in details]
            confidences = [d['confidence'] for d in details]
            
            dominant_emotion = max(set(emotions), key=emotions.count)
            avg_confidence = float(np.mean(confidences))
            
            # Categories definitions
            positive_emotions = {'happy', 'surprise'}
            neutral_emotions = {'neutral'}
            negative_emotions = {'sad', 'angry', 'fear', 'disgust'}
            
            pos_count = sum(1 for e in emotions if e in positive_emotions)
            neu_count = sum(1 for e in emotions if e in neutral_emotions)
            neg_count = sum(1 for e in emotions if e in negative_emotions)
            total_count = len(emotions)
            
            pos_pct = round((pos_count / total_count) * 100, 2)
            neu_pct = round((neu_count / total_count) * 100, 2)
            neg_pct = round((neg_count / total_count) * 100, 2)
            
            # Custom rule-based recommendation generation
            recommendations_list = []
            
            if pos_pct > 40:
                recommendations_list.append("Great job! You showed a high percentage of positive expressions. This helps build rapport with the interviewer.")
            elif pos_pct < 10:
                recommendations_list.append("Try to smile more and show engagement. A neutral or slightly distant look can be interpreted as a lack of enthusiasm.")
                
            if neg_pct > 30:
                recommendations_list.append("We detected highly negative emotional signals (e.g., sadness, anger, scale of tension). Practice relaxing your facial muscles, breathing calmly, and keeping a pleasant demeanor to manage stress signals.")
                
            if neu_pct > 70:
                recommendations_list.append("You maintained an extremely flat or neutral expression. Try to inject dynamic emotions and vocal/facial expressiveness to show passion and excitement about the opportunity.")
                
            if dominant_emotion == 'fear':
                recommendations_list.append("Expressions indicating fear or nervousness were common. Practice mock interviews in front of mirrors, use steady breathing, and focus on slow, deliberate delivery to combat anxiety.")
            elif dominant_emotion == 'angry':
                recommendations_list.append("Facial tension resembling anger was detected. Keep an eye on furrowing your brow or narrowing your eyes when thinking deeply; try to look interested instead.")
            elif dominant_emotion == 'happy':
                recommendations_list.append("Your dominant expression was happy. This displays friendliness; just make sure it aligns with the serious nature of technical or logical answers!")
                
            if avg_confidence < 45.0:
                recommendations_list.append("The emotion detection confidence was relatively low. Ensure your webcam setting has balanced front-facing lighting to prevent shadow interference.")
                
            if not recommendations_list:
                recommendations_list.append("Excellent balanced emotional posture! You moved dynamically between professional neutrality and positive engagement. Keep practicing to maintain this control.")
                
            recommendations = " ".join(recommendations_list)
            
        # Update session with final aggregates
        db.update_session_analytics(
            db_path=DB_PATH,
            session_id=session_id,
            duration=duration,
            dominant_emotion=dominant_emotion,
            average_confidence=avg_confidence,
            positive_pct=pos_pct,
            negative_pct=neg_pct,
            neutral_pct=neu_pct,
            recommendations=recommendations
        )
        
        return jsonify({
            "status": "success",
            "session_id": session_id,
            "analytics": {
                "duration": duration,
                "dominant_emotion": dominant_emotion,
                "average_confidence": round(avg_confidence, 2),
                "positive_pct": pos_pct,
                "negative_pct": neg_pct,
                "neutral_pct": neu_pct,
                "recommendations": recommendations,
                "total_frames_with_face": len(details)
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to stop session: {str(e)}"
        }), 500

@app.route('/reset', methods=['POST'])
@app.route('/api/reset', methods=['POST'])
def reset_session():
    try:
        data = request.get_json()
        if not data or 'session_id' not in data:
            return jsonify({"status": "error", "message": "Missing session_id."}), 400
            
        session_id = data.get('session_id')
        db.delete_session(DB_PATH, session_id)
        
        # Also clean up report file if it exists
        report_file = os.path.join(REPORTS_DIR, f"{session_id}.pdf")
        if os.path.exists(report_file):
            os.remove(report_file)
            
        return jsonify({
            "status": "success",
            "message": "Session reset successfully. All transient data deleted."
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to reset session: {str(e)}"
        }), 500

@app.route('/download_report')
@app.route('/api/download_report')
def download_report():
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return "Missing session_id parameter", 400
            
        # Ensure session exists and analytics are updated before reporting
        session = db.get_session(DB_PATH, session_id)
        if not session:
            return "Session not found in history.", 404
            
        # Generate report (overwrite if already exists, ensuring latest calculations)
        pdf_path = reporter.generate_pdf_report(session_id)
        
        if not pdf_path or not os.path.exists(pdf_path):
            return "Error: Failed to generate PDF report.", 500
            
        formatted_date = datetime.strptime(session['timestamp'], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
        filename = f"InterviewSense_Report_{formatted_date}_{session_id[:8]}.pdf"
        
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return f"Internal Server Error generating report: {str(e)}", 500

@app.route('/history_data', methods=['GET'])
@app.route('/api/history_data', methods=['GET'])
@app.route('/api/history', methods=['GET'])
def get_history_data():
    try:
        sessions = db.get_all_sessions(DB_PATH)
        return jsonify({
            "status": "success",
            "sessions": sessions
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to load history list: {str(e)}"
        }), 500

@app.route('/api/session_details/<session_id>', methods=['GET'])
@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session_detail_data(session_id):
    try:
        session = db.get_session(DB_PATH, session_id)
        if not session:
            return jsonify({"status": "error", "message": "Session not found."}), 404
        details = db.get_session_details(DB_PATH, session_id)
        return jsonify({
            "status": "success",
            "session": session,
            "details": details
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to load session details: {str(e)}"
        }), 500


@app.route('/delete_session/<session_id>', methods=['POST', 'DELETE'])
@app.route('/api/delete_session/<session_id>', methods=['POST', 'DELETE'])
@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_saved_session(session_id):
    try:
        db.delete_session(DB_PATH, session_id)
        report_file = os.path.join(REPORTS_DIR, f"{session_id}.pdf")
        if os.path.exists(report_file):
            os.remove(report_file)
        return jsonify({
            "status": "success",
            "message": "Session deleted permanently."
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to delete session: {str(e)}"
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "detector_ready": detector is not None
    })

@app.route('/api/analyze_image', methods=['POST'])
def analyze_image():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No JSON payload provided."}), 400
        
        frame_b64 = data.get('image')
        if not frame_b64:
            return jsonify({"status": "error", "message": "Missing 'image' base64 content."}), 400
            
        # Decode base64 image to CV2 matrix
        frame = detector.base64_to_cv2(frame_b64)
        if frame is None:
            return jsonify({"status": "error", "message": "Failed to decode image frame."}), 400
            
        # Run emotion detection
        analysis_result = detector.analyze_frame(frame)
        
        return jsonify({
            "status": "success",
            "analysis": analysis_result
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error in image analysis: {str(e)}"
        }), 500

if __name__ == '__main__':
    # Bind to 0.0.0.0 and port environment variable for web cloud hosting compatibility (e.g. Render)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
