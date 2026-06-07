@echo off
cd /d "E:\User\Documents\augment-projects\ipogsites\voice-insight-system"

REM Critical: Set env vars BEFORE starting Python to avoid DLL loading deadlocks
set KMP_DUPLICATE_LIB_OK=TRUE
set OMP_NUM_THREADS=2
set HF_HOME=E:\.hf-cache
set WHISPER_MODEL=tiny
set SERVER_PORT=9000

echo Starting Voice Insight Server on port 9000...
echo (Model: tiny, KMP_DUPLICATE_LIB_OK=TRUE, OMP_NUM_THREADS=2)
python server.py
