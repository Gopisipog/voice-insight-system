import os
import time
import tempfile
import numpy as np
import scipy.io.wavfile as wav
import whisper
from openai import OpenAI

class Transcriber:
    def __init__(self, model_size="small", device="cpu", compute_type="int8"):
        """
        Initializes the Transcriber.
        Uses OpenAI API if OPENAI_API_KEY is present, otherwise falls back to local.
        """
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        
        if self.api_key and "sk-" in self.api_key:
            print("🚀 High-Fidelity Mode: OpenAI API enabled.")
            self.client = OpenAI(api_key=self.api_key)
        else:
            print(f"🏠 Local Mode: Loading Whisper '{model_size}' on {device}...")
            self.model = whisper.load_model(model_size, device=device)
        
    def transcribe_file(self, file_path):
        """
        Transcribes an audio file using the best available engine.
        Accepts: file path (str), numpy array, or BytesIO object.
        """
        try:
            # Handle file-like objects (BytesIO) from the PWA stream
            cleanup_temp = False
            if hasattr(file_path, 'read'):
                import tempfile
                # Use tempfile to avoid path issues
                data = file_path.read()
                if len(data) < 100:  # Too small to be valid audio
                    return None
                suffix = ".webm"
                temp_fd, temp_path = tempfile.mkstemp(suffix=suffix)
                os.close(temp_fd)
                with open(temp_path, "wb") as f:
                    f.write(data)
                file_path = temp_path
                cleanup_temp = True

            if self.client:
                # Use OpenAI API (High Fidelity)
                file_to_send = open(file_path, "rb") if isinstance(file_path, str) else file_path

                response = self.client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=file_to_send,
                    response_format="text"
                )
                result = response.strip()
                if cleanup_temp and os.path.exists(temp_path):
                    os.remove(temp_path)
                return result
            else:
                # Local Fallback (openai-whisper)
                result = self.model.transcribe(file_path, beam_size=5)
                if cleanup_temp and os.path.exists(temp_path):
                    os.remove(temp_path)
                return result["text"].strip() if result["text"] else None
        except Exception as e:
            print(f"Transcription error: {e}")
            return None

    def transcribe_stream(self, audio_data):
        """
        Transcribes raw numpy audio data.
        """
        if self.client:
            temp_wav = "temp_stream_chunk.wav"
            try:
                int_data = (audio_data * 32767).astype(np.int16)
                wav.write(temp_wav, 16000, int_data)
                text = self.transcribe_file(temp_wav)
                if os.path.exists(temp_wav): os.remove(temp_wav)
                return text
            except Exception as e:
                print(f"Stream-to-API error: {e}")
                return None
        else:
            # Local mode (openai-whisper)
            try:
                # Ensure float32 numpy array
                if isinstance(audio_data, np.ndarray):
                    audio_to_transcribe = audio_data.astype(np.float32)
                else:
                    audio_to_transcribe = np.frombuffer(audio_data, dtype=np.float32)
                
                result = self.model.transcribe(audio_to_transcribe, beam_size=5)
                return result["text"].strip() if result["text"] else None
            except Exception as e:
                print(f"Local stream error: {e}")
                return None

if __name__ == "__main__":
    pass
