# InterviewSense — AI Powered Mock Interview Practice Assistant

InterviewSense is a production-ready, local-first Computer Vision web application. It is designed to analyze facial expressions and body posture signals during mock practice interviews and generate custom emotional timelines and coaching suggestions. The system is 100% software-based, does not measure technical success, and is designed entirely for objective mock self-reflection.

---

## Key Features

- **Live Webcam Processing**: Utilizes HTML5 Video and Canvas to capture facial states locally and streams images to the backend.
- **Real-time Face Bounding Overlays**: Highlights the user's face with custom, dynamically colored bounding grids matching their dominant emotion in real-time.
- **Emotion Timeline Charts**: Charts confidence scores metrics over time on lines charts.
- **Aggregate Distribution Maps**: Renders a dynamic doughnut distribution chart breaking down individual expressions (Happy, Surprise, Neutral, Sad, Angry, Fear, Disgust).
- **SQLite Historical Syncing**: Saves complete practice history records, durations, dominant feelings, and granular coordinates datasets.
- **Professional PDF Exports**: Generates detailed, beautifully formatted Summary PDF reports using ReportLab with horizontal indicators and timeline tables.
- **Premium Glassmorphic Dark Theme**: Highly polished, modern dashboards layout styled in dark colors.

---

## Folder Structure

```text
c:\Users\Asus\Desktop\interview\
│
├── app.py                      # Flask backend containing endpoint routing
├── emotion_detector.py         # OpenCV Haar cascades and DeepFace image processing
├── database.py                 # SQLite schema declarations & CRUD utilities
├── report_generator.py         # ReportLab PDF design and generation layout
├── requirements.txt            # Python dependencies lists
├── README.md                   # Setup and usage manuals
│
├── templates/
│   ├── index.html              # Main dashboard HTML template
│   └── history.html            # Archived session history logs HTML template
│
├── static/
│   ├── style.css               # Glassmorphic premium styling override definitions
│   ├── script.js               # Webcam drivers and client endpoint controllers
│   └── charts.js               # Chart.js line and doughnut chart implementations
│
├── database/                   # SQLite database storage directory (automatically generated)
│   └── interview_sense.db      # SQLite DB file
│
└── reports/                    # Session PDF archives storage (automatically generated)
    └── [session_uuid].pdf      # Generated PDF reports
```

---

## Installation & Setup Instructions

Ensure you have **Python 3.11** installed.

### 1. Initialize Virtual Environment

From your terminal (Command Prompt or PowerShell) inside the directory, execute:

```powershell
python -m venv .venv
```

### 2. Activate Virtual Environment

- **PowerShell (Windows)**:
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- **Command Prompt (Windows)**:
  ```cmd
  .venv\Scripts\activate.bat
  ```

### 3. Install Package Dependencies

```powershell
pip install -r requirements.txt
```

*Note: Depending on your local hardware network constraints, downloading DeepFace and its underlying machine learning backends (TensorFlow) can take a few minutes. Subsequent executions will load immediately since weights are cached in your local profile directory.*

### 4. Run the Application

```powershell
python app.py
```

Open your browser and navigate to `http://127.0.0.1:5000` to interact with the application.

---

## Usage Guide

1. **Start Mock Practice**: Open the Home dashboard. Click the **Start Mock** button. Your browser will prompt you for camera access. Agree to start streaming.
2. **Dynamic Live Graphs**: Sit in front of the camera. The system will start recording and processing frames. You will see a glowing bounding box drawn on your face, real-time metrics changing, and Chart.js lines plotting your expressions.
3. **Stop & Save**: Once your practice session is complete, click **Stop & Save**. The frame loops will halt, and the AI Practice Feedback card will render with custom, rule-based recommendation lists.
4. **Generate Report PDF**: Click **Download PDF** to generate and download a publication-quality analysis report.
5. **View History Logs**: Go to **History Logs** in the sidebar. You can inspect previous attempts, see color-coded pills representing emotion distributions, display timeline metrics inside the sliding drawer, and download PDF reports of historical sessions.
6. **Reset/Discard logs**: Click **Reset** on the home dashboard to wipe out current transient data immediately. Click the trash icon in the History page to delete log records permanently from the SQLite database.

---

## GitHub Operations & Push Guide

If you wish to upload your mock assistant repository to GitHub, execute the following commands in sequence:

```bash
# 1. Initialize Git repository
git init

# 2. Add files to version control (.gitignore filters out local venvs, DBs, and PDFs)
# Let's create a standard .gitignore if needed, or add files manually.
git add app.py emotion_detector.py database.py report_generator.py requirements.txt README.md templates static

# 3. Create initial commit
git commit -m "feat: initial commit for InterviewSense practice assistant mockup"

# 4. Define primary branch name
git branch -M main

# 5. Connect to your remote repository
git remote add origin https://github.com/HariPrasath-13/Emotion-Detector.git

# 6. Upload repository files
git push -u origin main
```
