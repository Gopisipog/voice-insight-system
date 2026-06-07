@echo off
cd /d "E:\User\Documents\augment-projects\ipogsites\voice-insight-system"
git add -A
git commit -m "Voice Insight System - full project with Streamlit Cloud support"
git status > git_status.txt 2>&1
type git_status.txt
