@echo off
cd /d "E:\User\Documents\augment-projects\ipogsites\voice-insight-system"

:: Remove the temp file
del git_status.txt 2>nul

:: Stage everything except node_modules and pycache
git add .gitignore
git add *.py *.bat *.txt *.md
git add packages.txt
git add .streamlit/config.toml
git add core/transcriber.py
git add core/segmenter.py
git add core/shell_runner.py
git add core/bot_manager.py
git add pwa/src/App.jsx
git add pwa/src/App.css
git add pwa/src/index.css
git add pwa/src/main.jsx
git add pwa/index.html
git add pwa/vite.config.js
git add pwa/package.json
git add pwa/eslint.config.js
git add pwa/public/favicon.svg
git add pwa/public/icons.svg
git add scripts/test_transcription.py

:: Remove sensitive .env from tracking
git rm --cached .env 2>nul

:: Commit
git commit -m "Voice Insight System - full project with Streamlit Cloud support"

:: Show status summary (redirect to file to avoid buffer overflow)
git status --short > git_status_short.txt 2>&1
echo Commit done! Files staged:
type git_status_short.txt
