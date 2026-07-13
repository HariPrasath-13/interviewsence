@echo off
REM Run facedetect.py using the virtualenv in emotion_env
cd /d "%~dp0"
call "emotion_env\Scripts\activate.bat"
python "%~dp0app.py"
REM Pause so window stays open after script exits
pause

