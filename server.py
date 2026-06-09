import os
import json
import threading
import queue
import time
import asyncio
import numpy as np
import io
import tempfile

# PyAudio is optional (only for local mic capture, not available on Render/cloud)
try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    pyaudio = None
    HAS_PYAUDIO = False
    print("* PyAudio not available - local mic capture disabled")
from fastapi import FastAPI, WebSocket, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

# Lazy initialization of heavy ML components
transcriber = None
segmenter = None
shell_runner = None
bot = None

def _init_components():
    """Initialize heavy components on first use (after server starts)."""
    global transcriber, segmenter, shell_runner, bot
    if transcriber is not None:
        return

    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("OMP_NUM_THREADS", "2")

    from core.transcriber import Transcriber
    from core.segmenter import SemanticSegmenter
    from core.shell_runner import ShellRunner
    try:
        from core.bot_manager import BotManager
    except ImportError:
        BotManager = None

    model_size = os.getenv("WHISPER_MODEL", "small").strip()
    transcriber = Transcriber(model_size=model_size)
    segmenter = SemanticSegmenter()
    shell_runner = ShellRunner()
    try:
        bot = BotManager()
    except Exception as e:
        print(f"Bot init skipped: {e}")
        bot = None
    print("ML Components initialized")

active_websockets = []
mic_active = False
audio_buffer = bytearray()      # Raw PCM float32 bytes from browser
audio_queue = queue.Queue()      # Numpy arrays from local mic

async def broadcast_segment(unit: str):
    print(f"-> Broadcasting: {unit[:50]}...")
    message = json.dumps({"type": "new_segment", "text": unit, "timestamp": new_timestamp()})
    for ws in active_websockets[:]:
        try:
            await ws.send_text(message)
        except:
            if ws in active_websockets:
                active_websockets.remove(ws)

def new_timestamp():
    return time.strftime("%H:%M:%S")

async def transcription_worker():
    print("* Transcription worker active")
    last_processed_time = time.time()

    while True:
        try:
            # 1. Local Mic (numpy arrays from PyAudio/Stereo Mix)
            if not audio_queue.empty():
                data = audio_queue.get_nowait()
                text = transcriber.transcribe_stream(data)
                if text:
                    print(f"  Transcribed: {text[:60]}...")
                    for unit in segmenter.add_text(text):
                        await broadcast_segment(unit)

            # 2. PWA Stream (raw float32 PCM bytes from browser AudioContext)
            if len(audio_buffer) > 0 and len(audio_buffer) % 64000 < 4096:
                print(f"  Buffer size: {len(audio_buffer)} bytes")
            MIN_BYTES = 8000 * 4  # 0.5 seconds of float32 at 16kHz
            if len(audio_buffer) >= MIN_BYTES and (time.time() - last_processed_time > 2):
                WINDOW_SAMPLES = 48000  # 3 seconds at 16kHz
                WINDOW_BYTES = WINDOW_SAMPLES * 4

                chunk = audio_buffer[-min(WINDOW_BYTES, len(audio_buffer)):]
                chunk = chunk[:len(chunk) - (len(chunk) % 4)]

                if len(chunk) >= 8000 * 4:
                    audio_np = np.frombuffer(bytes(chunk), dtype=np.float32).copy()

                    loop = asyncio.get_running_loop()
                    text = await loop.run_in_executor(None, transcriber.transcribe_stream, audio_np)

                    if text:
                        print(f"  PWA Transcribed: {text[:60]}...")
                        new_units = segmenter.add_text(text)
                        for unit in new_units:
                            await broadcast_segment(unit)
                        if new_units and len(audio_buffer) > WINDOW_BYTES:
                            audio_buffer[0:len(audio_buffer) - WINDOW_BYTES] = b""

                    for unit in segmenter.flush():
                        await broadcast_segment(unit)

                    last_processed_time = time.time()

            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Worker Error: {e}")
            await asyncio.sleep(1)

def mic_thread_logic():
    global mic_active
    if not HAS_PYAUDIO:
        print("* Local mic thread disabled (PyAudio not available)")
        return
    p = pyaudio.PyAudio()

    device_id = os.getenv("WHISPER_INPUT_DEVICE_ID")
    if device_id:
        try:
            device_id = int(device_id)
        except:
            device_id = None

    try:
        # Use native device rate, resample in numpy to 16kHz
        dev_info = p.get_device_info_by_index(device_id) if device_id else None
        native_rate = int(dev_info['defaultSampleRate']) if dev_info else 16000
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=native_rate,
            input=True,
            frames_per_buffer=1024,
            input_device_index=device_id
        )
        secs_per_read = int(native_rate / 1024 * 3)
        print(f"* Local Audio Stream Started (Device: {device_id}, {native_rate}Hz).")
        
        read_timeout = 0  # ms - will use small reads for quick exit
        while True:
            if mic_active:
                # Read smaller chunks to stay responsive
                frames = []
                for _ in range(secs_per_read):
                    try:
                        frames.append(stream.read(1024, exception_on_overflow=False))
                    except Exception:
                        break
                if frames:
                    raw = np.frombuffer(b''.join(frames), dtype=np.int16).astype(np.float32) / 32768.0
                    
                    # Resample to 16kHz if needed
                    if native_rate != 16000:
                        from scipy import signal
                        ratio = 16000 / native_rate
                        new_len = int(len(raw) * ratio)
                        audio_data = signal.resample(raw, new_len)
                    else:
                        audio_data = raw
                    audio_queue.put(audio_data)
            else:
                time.sleep(0.5)
    except Exception as e:
        print(f"* Audio Device Error: {e}")
    finally:
        p.terminate()

@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_components()
    threading.Thread(target=mic_thread_logic, daemon=True).start()
    task = asyncio.create_task(transcription_worker())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class CommandRequest(BaseModel):
    command: str
    input: str

@app.websocket("/ws/audio")
async def audio_websocket(websocket: WebSocket):
    """Receives raw float32 PCM audio from browser AudioContext."""
    global audio_buffer
    await websocket.accept()
    print("Audio stream opened.")
    bytes_received = 0
    try:
        while True:
            data = await websocket.receive_bytes()
            bytes_received += len(data)
            audio_buffer.extend(data)
            if bytes_received < 64000 and bytes_received % 64000 < 4096:
                print(f"  Audio received: {bytes_received} bytes so far")
            if len(audio_buffer) > 10 * 1024 * 1024:
                audio_buffer = audio_buffer[-1024 * 1024:]
    except:
        print(f"Audio stream closed. Total received: {bytes_received} bytes")

@app.websocket("/ws/live")
async def live_ui_websocket(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        if websocket in active_websockets:
            active_websockets.remove(websocket)

@app.websocket("/ws/bridge")
async def bridge_websocket(websocket: WebSocket):
    """Handles desktop bridge connections for executing shell commands."""
    await websocket.accept()
    print("Bridge connected.")
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "run_command":
                input_text = data.get("input", "")
                result = shell_runner.run_command(
                    os.getenv("FILTER_COMMAND", 'powershell -Command "$input | findstr /i \'insight\'"'),
                    input_text
                )
                await websocket.send_json({
                    "type": "command_result",
                    "output": result
                })
    except:
        print("Bridge disconnected.")

@app.post("/toggle-mic")
async def toggle_mic(active: bool):
    global mic_active, audio_buffer
    mic_active = active
    if active:
        audio_buffer = bytearray()
    return {"status": "ok"}

@app.post("/run-command")
async def execute_command(req: CommandRequest):
    result = shell_runner.run_command(req.command, req.input)
    return {"output": result}

@app.get("/health")
async def health_check():
    return {"status": "ok", "transcriber": transcriber is not None}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVER_PORT", "9000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
