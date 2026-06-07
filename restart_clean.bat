@echo off
cd /d "E:\User\Documents\augment-projects\ipogsites\voice-insight-system"
title Voice Insight - Clean Restart

echo ============================================
echo  VOICE INSIGHT SYSTEM - CLEAN RESTART
echo ============================================
echo.

:: Step 1: Kill ALL Python processes
echo [1/6] Killing all Python processes...
taskkill /F /IM python.exe 2>nul
timeout /T 2 /NOBREAK > NUL

:: Step 2: Kill any Node/Vite processes
echo [2/6] Killing Node/Vite processes...
taskkill /F /IM node.exe 2>nul
timeout /T 2 /NOBREAK > NUL

:: Step 3: Kill any processes on our ports
echo [3/6] Clearing ports 9000 and 5173...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":9000 "') do (
    taskkill /F /PID %%a 2>nul
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173 "') do (
    taskkill /F /PID %%a 2>nul
)
timeout /T 2 /NOBREAK > NUL

:: Step 4: Clear Vite cache (stale bundled JS)
echo [4/6] Clearing Vite cache...
if exist "pwa\node_modules\.vite" rmdir /s /q "pwa\node_modules\.vite"

:: Step 5: Verify env file is correct
echo [5/6] Verifying config...
findstr /B "VITE_SERVER_PORT=9000" pwa\.env > NUL
if %ERRORLEVEL% NEQ 0 echo VITE_SERVER_PORT=9000 > pwa\.env
echo    PWA configured for port 9000

:: Step 6: Start everything
echo [6/6] Starting services...
echo.

:: Start backend server (fresh cmd window)
echo  * Starting Backend Server (port 9000)...
start "VoiceInsight-Server" cmd /c "start_server.bat"

:: Wait for server to be ready
echo  * Waiting for server to initialize...
timeout /T 8 /NOBREAK > NUL

:: Start PWA
echo  * Starting PWA frontend (port 5173)...
cd pwa
start "VoiceInsight-PWA" cmd /c "npm run dev"
cd ..

:: Verify server is up
echo.
echo ============================================
echo  Verifying connections...
echo ============================================
timeout /T 3 /NOBREAK > NUL
curl -s http://localhost:9000/health 2>nul
echo.

echo ============================================
echo  ✅ SYSTEM IS STARTING UP
echo ============================================
echo.
echo  Access the PWA at: http://localhost:5173
echo.
echo  Quick commands:
echo    - Hard refresh: Ctrl+F5 or Ctrl+Shift+R
echo    - InPrivate:    Ctrl+Shift+N
echo    - Dev Tools:    F12
echo ============================================
pause
