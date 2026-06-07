import os
import time
import tempfile
import numpy as np
import scipy.io.wavfile as wav
from openai import OpenAI

class Transcriber:
    def __init__(self, model_size="small", device="cpu", compute_type="int8"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        self.model = None
        
        if self.api_key and "sk-" in self.api_key:
            print("OpenAI API enabled.")
            self.client = OpenAI(api_key=self.api_key)
        else:
            print(f"Local Mode: Loading Whisper '{model_size}' on {device}...")
            import whisper
            self.model = whisper.load_model(model_size, device=device)
        else:
            print("⚠️ No transcription backend available! Install faster-whisper or set OPENAI_API_KEY.")
        
    def transcribe_file(self, file_path):
        """
        Transcribes an audio file using the best available engine.
        Accepts: file path (str), numpy array, or BytesIO object.
        """
        try:
            if self.client:
                return self._transcribe_api(file_path)
            elif self.backend == "faster-whisper":
                return self._transcribe_faster(file_path)
            elif self.backend == "openai-whisper":
                return self._transcribe_whisper(file_path)
            else:
                return None
        except Exception as e:
            print(f"Transcription error: {e}")
            return None

    def transcribe_stream(self, audio_data):
        """
        Transcribes raw numpy audio data.
        """
        if self.client:
            temp_wav = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    int_data = (audio_data * 32767).astype(np.int16)
                    wav.write(tmp.name, 16000, int_data)
                    temp_wav = tmp.name
                
                text = self.transcribe_file(temp_wav)
                return text
            except Exception as e:
                print(f"Stream-to-API error: {e}")
                return None
            finally:
                if temp_wav and os.path.exists(temp_wav):
                    try: os.unlink(temp_wav)
                    except: pass
        
        elif self.backend == "faster-whisper":
            try:
                if isinstance(audio_data, np.ndarray):
                    audio_to_transcribe = audio_data.astype(np.float32)
                else:
                    audio_to_transcribe = np.frombuffer(audio_data, dtype=np.float32)
                
                segments, _ = self.model.transcribe(audio_to_transcribe, beam_size=5)
                text = " ".join(seg.text for seg in segments)
                return text.strip() if text.strip() else None
            except Exception as e:
                print(f"faster-whisper stream error: {e}")
                return None
        
        elif self.backend == "openai-whisper":
            try:
                if isinstance(audio_data, np.ndarray):
                    audio_to_transcribe = audio_data.astype(np.float32)
                else:
                    audio_to_transcribe = np.frombuffer(audio_data, dtype=np.float32)
                
                result = self.model.transcribe(audio_to_transcribe, beam_size=5)
                return result["text"].strip() if result["text"] else None
            except Exception as e:
                print(f"openai-whisper stream error: {e}")
                return None
        
        return None

    def _transcribe_api(self, file_path):
        """Transcribe using OpenAI Whisper API."""
        if hasattr(file_path, 'read'):
            data = file_path.read()
            if len(data) < 100:
                return None
            suffix = ".webm"
            fd, tmp_path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            with open(tmp_path, "wb") as f:
                f.write(data)
            result = self._send_to_api(tmp_path)
            os.unlink(tmp_path)
            return result
        else:
            return self._send_to_api(file_path)
    
    def _send_to_api(self, path):
        """Send file path to OpenAI API."""
        with open(path, "rb") as f:
            response = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="text"
            )
        return response.strip()
    
    def _transcribe_faster(self, file_path):
        """Transcribe using faster-whisper (CTranslate2)."""
        segments, _ = self.model.transcribe(str(file_path), beam_size=5)
        text = " ".join(seg.text for seg in segments)
        return text.strip() if text.strip() else None
    
    def _transcribe_whisper(self, file_path):
        """Transcribe using openai-whisper (PyTorch)."""
        result = self.model.transcribe(str(file_path), beam_size=5)
        return result["text"].strip() if result["text"] else None
