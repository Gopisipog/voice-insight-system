# Voice Insight System

A dual-approach voice capture and analysis system that transcribes audio and filters it through local Shell/PowerShell commands before sending the results to Telegram.

## 📁 Project Structure

- `core/`: Common logic for Transcription (Whisper), Segmentation, Shell Execution, and Telegram Bot.
- `main_hub.py`: **Approach 1** - Local Desktop Hub. Single script for mic capture -> transcription -> shell -> Telegram.
- `pwa/`: **Approach 2** - Mobile-ready PWA (React + Vite).
- `server.py`: **Approach 2** - Backend server for PWA audio uploads and Bridge communication.
- `desktop_bridge.py`: **Approach 2** - Local client to bridge PWA commands to local Shell/PowerShell.
- `scripts/`: Helper scripts for testing.

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11+
- Node.js (for PWA)
- A Telegram Bot Token (from @BotFather)

### 2. Installation
```bash
pip install -r requirements.txt
```

### 3. Configuration
Copy `.env.example` to `.env` and fill in your:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `FILTER_COMMAND` (e.g., `powershell -Command "$input | findstr /i 'insight'"`)

### 4. Running Approach 1 (Desktop Hub)
This is for high-performance, local mic capture.
```bash
python main_hub.py
```

### 5. Running Approach 2 (PWA + Bridge)
This is for recording on mobile and executing on desktop.

**Step A: Start Backend Server**
```bash
python server.py
```

**Step B: Start Desktop Bridge**
```bash
python desktop_bridge.py
```

**Step C: Launch PWA**
```bash
cd pwa
npm install
npm run dev
```

## 🛠 Features
- **Semantic Segmentation:** Grouping sentences into logical units before analysis.
- **Shell-as-Stdin:** Transcription is fed directly to your custom shell scripts.
- **Interactive Telegram Bot:** Results are pushed to chat; bot context allows querying the data.
