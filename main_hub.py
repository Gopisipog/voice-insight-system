import time
import asyncio
import os
import threading
import queue
import numpy as np
import pyaudio
from core.transcriber import Transcriber
from core.segmenter import SemanticSegmenter
from core.shell_runner import ShellRunner
from core.bot_manager import BotManager
from dotenv import load_dotenv

load_dotenv()

class VoiceInsightHub:
    def __init__(self):
        self.transcriber = Transcriber(
            model_size=os.getenv("WHISPER_MODEL", "base"),
            device=os.getenv("WHISPER_DEVICE", "cpu")
        )
        self.segmenter = SemanticSegmenter()
        self.runner = ShellRunner()
        self.bot = BotManager()
        self.filter_command = os.getenv("FILTER_COMMAND", "powershell -Command \"$input | findstr /i 'gap'\"")
        self.audio_queue = queue.Queue()
        self.is_running = True

    def _mic_callback_thread(self):
        """
        Background thread to capture audio and put into a queue.
        """
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        RECORD_SECONDS = 5 # Accumulate 5 seconds of audio

        p = pyaudio.PyAudio()
        try:
            stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
            print("* Microphone listening thread started...")
            
            while self.is_running:
                frames = []
                for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                    if not self.is_running: break
                    try:
                        data = stream.read(CHUNK, exception_on_overflow=False)
                        frames.append(data)
                    except Exception as e:
                        print(f"Mic read error: {e}")
                        break
                
                if frames:
                    # Convert to numpy array
                    audio_data = np.frombuffer(b''.join(frames), dtype=np.int16).astype(np.float32) / 32768.0
                    self.audio_queue.put(audio_data)

            stream.stop_stream()
            stream.close()
        except Exception as e:
            print(f"Failed to open microphone: {e}")
        finally:
            p.terminate()

    async def processing_worker(self):
        """
        Async worker that pulls chunks from the queue and transcribes them.
        """
        print("* Transcription worker started...")
        while self.is_running:
            try:
                # Use run_in_executor for the blocking transcription call
                if not self.audio_queue.empty():
                    audio_data = self.audio_queue.get_nowait()
                    
                    # Transcription is CPU intensive, run in thread to avoid blocking loop
                    loop = asyncio.get_running_loop()
                    text = await loop.run_in_executor(None, self.transcriber.transcribe_stream, audio_data)
                    
                    if text and text.strip():
                        print(f"Transcribed: {text}")
                        await self.process_text_units(text)
                else:
                    await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Worker Exception: {e}")
                await asyncio.sleep(1)

    async def process_text_units(self, text):
        """Processes text segments into conceptual units and runs shell logic."""
        units = self.segmenter.add_text(text)
        for unit in units:
            print(f"Processing Unit: {unit}")
            
            # Execute shell command
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self.runner.run_command, self.filter_command, unit)
            
            if result.strip():
                print(f"Insight Found: {result}")
                # Use the bot instance directly (this is now in the same loop)
                await self.bot.application.bot.send_message(
                    chat_id=self.bot.chat_id, 
                    text=f"🎯 *New Insight Found*\n\n*Input:* {unit}\n\n*Output:* {result}",
                    parse_mode='Markdown'
                )

    async def run(self):
        # 1. Start Mic thread
        mic_thread = threading.Thread(target=self._mic_callback_thread, daemon=True)
        mic_thread.start()

        # 2. Setup Bot
        # Add handlers before starting
        from telegram.ext import CommandHandler, MessageHandler, filters
        self.bot.application.add_handler(CommandHandler('start', self.bot.start))
        self.bot.application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.bot.handle_message))

        # 3. Start Bot and Processing Worker
        print("* Starting full-system loop...")
        async with self.bot.application:
            await self.bot.application.initialize()
            await self.bot.application.start()
            await self.bot.application.updater.start_polling()
            
            # Run the transcription worker alongside the bot
            await self.processing_worker()
            
            # Cleanup (if loop ends)
            await self.bot.application.updater.stop()
            await self.bot.application.stop()

if __name__ == "__main__":
    hub = VoiceInsightHub()
    try:
        asyncio.run(hub.run())
    except KeyboardInterrupt:
        hub.is_running = False
        print("Shutting down...")
