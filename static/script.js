/* ==========================================================================
   INTERVIEWSENSE CLIENT LOGIC
   Handles: Webcam capture, socket-less HTTP frames transmission, 
   UI dashboard rendering, timing, and bounding boxes.
   ========================================================================== */

let activeSessionId = null;
let streamObject = null;
let frameTickerId = null;
let stopwatchId = null;

// Metrics tracking
let sessionDurationSeconds = 0;
let frameCount = 0;
let framesProcessed = 0;
let fpsStartTime = null;
let currentFps = 0;

// Offscreen capture size constants
const CAPTURE_WIDTH = 640;
const CAPTURE_HEIGHT = 480;

// Emotion distribution counts
let sessionEmotionsList = [];
let emotionBreakdownCounts = {
    happy: 0, surprise: 0, neutral: 0, sad: 0, angry: 0, fear: 0, disgust: 0
};

// UI HTML Selectors
const videoElement = document.getElementById('webcam');
const canvasOverlay = document.getElementById('canvas-overlay');
const ctxOverlay = canvasOverlay.getContext('2d');
const videoPlaceholder = document.getElementById('video-placeholder-element');

const btnStart = document.getElementById('btn-start');
const btnStop = document.getElementById('btn-stop');
const btnReset = document.getElementById('btn-reset');
const btnPdf = document.getElementById('btn-export-pdf');

const timerLabel = document.getElementById('session-timer');
const fpsLabel = document.getElementById('stream-fps');
const frameCountLabel = document.getElementById('frames-processed');

const currentEmotionText = document.getElementById('curr-emotion');
const currentConfidenceText = document.getElementById('curr-confidence');
const faceBadgeStatus = document.getElementById('face-indicator');

// Navigation routing logic
document.getElementById('nav-history').addEventListener('click', function(e) {
    // If active session, warn user
    if (activeSessionId) {
        if (!confirm("Your mock practice session is running. Leaving this page will discard current session metrics. Proceed?")) {
            e.preventDefault();
            return;
        }
        resetAllState(true); // reset silently
    }
    window.location.href = "/history";
});

// App Initialization
document.addEventListener("DOMContentLoaded", () => {
    // Init empty visual charts on load
    if (typeof initDashboardCharts === "function") {
        initDashboardCharts();
    }
    
    // Wire main controls
    btnStart.addEventListener('click', beginPracticeSession);
    btnStop.addEventListener('click', stopPracticeSession);
    btnReset.addEventListener('click', () => {
        if (confirm("Reset current practice block? All transient session records will be wiped out.")) {
            resetAllState(false);
        }
    });
    
    btnPdf.addEventListener('click', downloadSessionPdf);
});

// Rescale overlay sizes relative to displaying client viewport
function syncOverlayDimensions() {
    canvasOverlay.width = videoElement.clientWidth;
    canvasOverlay.height = videoElement.clientHeight;
}
window.addEventListener('resize', syncOverlayDimensions);
videoElement.addEventListener('play', syncOverlayDimensions);


function showGlobalSpinner(msg) {
    document.getElementById('spinner-message').textContent = msg;
    document.getElementById('global-spinner').style.display = 'flex';
}

function hideGlobalSpinner() {
    document.getElementById('global-spinner').style.display = 'none';
}

// 1. Begin practice session
async function beginPracticeSession() {
    showGlobalSpinner("Requesting system configuration...");
    
    try {
        // Initialize user media webcam access
        streamObject = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: "user"
            },
            audio: false
        });
        
        // Feed stream to video tag
        videoElement.srcObject = streamObject;
        videoPlaceholder.style.display = 'none';
        
        // Notify Flask of start
        const startResponse = await fetch('/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const startJson = await startResponse.json();
        
        if (startJson.status !== 'success') {
            throw new Error(startJson.message || "Endpoint error registering session ID.");
        }
        
        activeSessionId = startJson.session_id;
        
        // Reset local trackers
        sessionDurationSeconds = 0;
        framesProcessed = 0;
        sessionEmotionsList = [];
        emotionBreakdownCounts = {
            happy: 0, surprise: 0, neutral: 0, sad: 0, angry: 0, fear: 0, disgust: 0
        };
        
        // UI Controls configuration
        btnStart.disabled = true;
        btnStop.disabled = false;
        btnReset.disabled = false;
        btnPdf.disabled = true;
        
        document.getElementById('panel-coaching').style.display = 'none';
        
        // Reset GUI dashboard metrics
        currentEmotionText.textContent = "Neutral";
        currentConfidenceText.textContent = "0.0%";
        timerLabel.textContent = "00:00";
        fpsLabel.textContent = "00";
        frameCountLabel.textContent = "0";
        
        if (typeof resetDashboardCharts === "function") {
            resetDashboardCharts();
        }
        
        // Trigger stopwatch timer
        stopwatchId = setInterval(() => {
            sessionDurationSeconds++;
            const mins = Math.floor(sessionDurationSeconds / 60).toString().padStart(2, '0');
            const secs = (sessionDurationSeconds % 60).toString().padStart(2, '0');
            timerLabel.textContent = `${mins}:${secs}`;
        }, 1000);
        
        // Trigger frame capture ticker (4 FPS = once every 250 milliseconds)
        fpsStartTime = performance.now();
        frameCount = 0;
        frameTickerId = setInterval(captureAndProcessFrame, 250);
        
    } catch (err) {
        alert("Camera initialization failed. Please authorize camera permissions in your browser and verify that no other software is using the device.\n\nError: " + err.message);
        console.error(err);
    } finally {
        hideGlobalSpinner();
    }
}

// 2. Offscreen capture and POST transmission
function captureAndProcessFrame() {
    if (!activeSessionId || videoElement.paused || videoElement.ended) return;
    
    // Draw current video posture to off-screen buffer canvas
    const offCanvas = document.createElement('canvas');
    offCanvas.width = CAPTURE_WIDTH;
    offCanvas.height = CAPTURE_HEIGHT;
    const offCtx = offCanvas.getContext('2d');
    
    // Draw mirrored or standard webcam crop
    offCtx.drawImage(videoElement, 0, 0, CAPTURE_WIDTH, CAPTURE_HEIGHT);
    
    // Export to lossy JPEG structure
    const base64Jpg = offCanvas.toDataURL('image/jpeg', 0.70);
    
    // Record current video timer for exact database synchronization
    const currentFrameOffset = sessionDurationSeconds;
    
    frameCount++;
    const now = performance.now();
    currentFps = Math.round((frameCount * 1000) / (now - fpsStartTime));
    fpsLabel.textContent = currentFps;
    
    // Fire JSON details asynchronously
    fetch('/process_frame', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_id: activeSessionId,
            frame: base64Jpg,
            elapsed_seconds: currentFrameOffset
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            handleFrameResponse(data.analysis, currentFrameOffset);
        }
    })
    .catch(err => {
        console.error("Frame processing endpoint failure:", err);
    });
}

// 3. UI feedback updates and Canvas drawing
function handleFrameResponse(analysis, timestamp) {
    framesProcessed++;
    frameCountLabel.textContent = framesProcessed;
    
    // Clear old visual frames on client UI layer canvas
    ctxOverlay.clearRect(0, 0, canvasOverlay.width, canvasOverlay.height);
    
    if (!analysis.face_detected) {
        setFaceIndicatorState(false);
        currentEmotionText.textContent = "No Face";
        currentConfidenceText.textContent = "0.0%";
        return;
    }
    
    setFaceIndicatorState(true);
    
    const domEm = analysis.dominant_emotion;
    const confScore = analysis.confidence;
    const probs = analysis.emotion_probabilities;
    
    // Update live metrics cards
    currentEmotionText.textContent = domEm;
    currentConfidenceText.textContent = `${parseFloat(confScore).toFixed(1)}%`;
    
    // Update raw sliders feedback
    updateProbabilitySliders(probs);
    
    // Update live UI charts
    sessionEmotionsList.push({
        time: timestamp,
        emotion: domEm,
        confidence: confScore
    });
    
    if (domEm in emotionBreakdownCounts) {
        emotionBreakdownCounts[domEm]++;
    }
    
    if (typeof updateDashboardCharts === "function") {
        updateDashboardCharts(sessionEmotionsList, emotionBreakdownCounts);
    }
    
    // Paint real-time face overlay bounding boxes
    if (analysis.face_box) {
        const box = analysis.face_box;
        
        // Calculate scaling multipliers
        const scaleX = canvasOverlay.width / CAPTURE_WIDTH;
        const scaleY = canvasOverlay.height / CAPTURE_HEIGHT;
        
        const scaledX = box.x * scaleX;
        const scaledY = box.y * scaleY;
        const scaledWidth = box.width * scaleX;
        const scaledHeight = box.height * scaleY;
        
        // Set styling attributes
        ctxOverlay.strokeStyle = getEmotionHexColor(domEm);
        ctxOverlay.lineWidth = 3;
        ctxOverlay.shadowColor = 'rgba(0, 0, 0, 0.5)';
        ctxOverlay.shadowBlur = 10;
        
        // Stroke rectangle wrapper
        ctxOverlay.strokeRect(scaledX, scaledY, scaledWidth, scaledHeight);
        
        // Draw caption top flag
        ctxOverlay.fillStyle = getEmotionHexColor(domEm);
        ctxOverlay.fillRect(scaledX - 1.5, scaledY - 26, scaledWidth + 3, 26);
        
        // Fill caption text
        ctxOverlay.fillStyle = "#ffffff";
        ctxOverlay.font = "600 13px 'Plus Jakarta Sans', sans-serif";
        ctxOverlay.shadowBlur = 0; // Disable shadow for texts
        ctxOverlay.fillText(`${domEm.toUpperCase()} (${parseFloat(confScore).toFixed(0)}%)`, scaledX + 8, scaledY - 8);
    }
}

function getEmotionHexColor(emotion) {
    const colorsMap = {
        happy: '#10b981',    // Success tint
        surprise: '#3b82f6', // Info tint
        neutral: '#6b7280',  // Slate tint
        sad: '#f59e0b',      // Warning tint
        angry: '#ef4444',    // Danger tint
        fear: '#8b5cf6',     // Violet tint
        disgust: '#ec4899'   // Pink
    };
    return colorsMap[emotion.toLowerCase()] || '#4f46e5';
}

function setFaceIndicatorState(detected) {
    const statusDot = faceBadgeStatus.querySelector('.status-dot');
    const badgeText = faceBadgeStatus.querySelector('.badge-txt');
    
    if (detected) {
        statusDot.className = "status-dot active";
        badgeText.textContent = "CONNECTED";
    } else {
        statusDot.className = "status-dot warning";
        badgeText.textContent = "NO FACE";
    }
}

function updateProbabilitySliders(probabilities) {
    for (const [em, rawVal] of Object.entries(probabilities)) {
        const lowerEm = em.toLowerCase();
        const items = document.querySelectorAll('.emotion-bar-item');
        items.forEach(el => {
            const labelNode = el.querySelector('.em-name');
            if (labelNode && labelNode.textContent.toLowerCase().trim() === lowerEm) {
                const fill = el.querySelector('.em-fill');
                const label = el.querySelector('.em-pct');
                if (fill && label) {
                    fill.style.width = `${rawVal}%`;
                    label.textContent = `${rawVal.toFixed(1)}%`;
                }
            }
        });
    }
}

// Custom selector helper matching case-insensitive
jQuerySelectorFallback = function() {
    // If native DOM parsing needed
};

// 4. Stop practice session
async function stopPracticeSession() {
    if (!activeSessionId) return;
    
    showGlobalSpinner("Finalizing session analytics...");
    
    // Halt frame processing immediately
    if (frameTickerId) clearInterval(frameTickerId);
    if (stopwatchId) clearInterval(stopwatchId);
    
    // Shut off camera streams
    if (streamObject) {
         streamObject.getTracks().forEach(track => track.stop());
    }
    
    videoElement.srcObject = null;
    videoPlaceholder.style.display = 'flex';
    ctxOverlay.clearRect(0, 0, canvasOverlay.width, canvasOverlay.height);
    
    try {
        const stopResponse = await fetch('/stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: activeSessionId,
                duration: sessionDurationSeconds
            })
        });
        
        const stopJson = await stopResponse.json();
        
        if (stopJson.status !== 'success') {
            throw new Error(stopJson.message || "Failed stop payload processing.");
        }
        
        renderFinalAnalytics(stopJson.analytics);
        
    } catch (err) {
        alert("An error occurred stopped final calculations: " + err.message);
        console.error(err);
    } finally {
        hideGlobalSpinner();
    }
}

function renderFinalAnalytics(analytics) {
    // Display card recommendations block
    const coachingPanel = document.getElementById('panel-coaching');
    coachingPanel.style.display = 'block';
    coachingPanel.scrollIntoView({ behavior: 'smooth' });
    
    // Load text
    document.getElementById('stat-pos-pct').textContent = `${analytics.positive_pct.toFixed(0)}%`;
    document.getElementById('stat-neu-pct').textContent = `${analytics.neutral_pct.toFixed(0)}%`;
    document.getElementById('stat-neg-pct').textContent = `${analytics.negative_pct.toFixed(0)}%`;
    
    document.getElementById('coaching-advice').textContent = analytics.recommendations;
    
    // Unlock buttons
    btnPdf.disabled = false;
    btnStart.disabled = false;
    btnStop.disabled = true;
    btnReset.disabled = true;
    
    // Store last session ID for PDF report downloading
    btnPdf.setAttribute('data-last-id', activeSessionId);
    
    // Also save state inactive locally
    activeSessionId = null;
}

// 5. PDF generation & downloads
function downloadSessionPdf() {
    // Since btn is unlocked only when session stops, we need the stored completed session ID.
    // Wait, since stopping session nullifies activeSessionId, we should store a temporary reference!
    const targetSessionId = btnPdf.getAttribute('data-last-id') || activeSessionId;
    
    // When stop runs, let's write it to data-last-id!
    // In stop session, we will do:
    // btnPdf.setAttribute('data-last-id', stopJson.session_id);
    
    if (!targetSessionId) {
        alert("Reference Session ID not available. Run mock practice first.");
        return;
    }
    
    window.location.href = `/download_report?session_id=${targetSessionId}`;
}

// 6. Reset all local state
function resetAllState(silent) {
    if (frameTickerId) clearInterval(frameTickerId);
    if (stopwatchId) clearInterval(stopwatchId);
    
    if (streamObject) {
        streamObject.getTracks().forEach(track => track.stop());
    }
    
    videoElement.srcObject = null;
    videoPlaceholder.style.display = 'flex';
    ctxOverlay.clearRect(0, 0, canvasOverlay.width, canvasOverlay.height);
    
    const requestResetOnServer = () => {
        if (!activeSessionId) return Promise.resolve();
        return fetch('/reset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: activeSessionId })
        });
    };
    
    if (silent) {
        requestResetOnServer();
        activeSessionId = null;
        return;
    }
    
    showGlobalSpinner("Resetting session details...");
    requestResetOnServer()
        .then(() => {
            activeSessionId = null;
            btnStart.disabled = false;
            btnStop.disabled = true;
            btnReset.disabled = true;
            btnPdf.disabled = true;
            
            document.getElementById('panel-coaching').style.display = 'none';
            timerLabel.textContent = "00:00";
            fpsLabel.textContent = "00";
            frameCountLabel.textContent = "0";
            currentEmotionText.textContent = "Neutral";
            currentConfidenceText.textContent = "0.0%";
            setFaceIndicatorState(false);
            
            // Clean bars
            updateProbabilitySliders({
                happy: 0, surprise: 0, neutral: 0, sad: 0, angry: 0, fear: 0, disgust: 0
            });
            
            if (typeof resetDashboardCharts === "function") {
                resetDashboardCharts();
            }
        })
        .catch(err => {
            console.error("Error resetting session:", err);
        })
        .finally(() => {
            hideGlobalSpinner();
        });
}
