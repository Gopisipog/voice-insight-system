import os
import time
import tempfile
import numpy as np
import scipy.io.wavfile as wav
from openai import OpenAI

# Try faster-whisper first (lightweight, CTranslate2), fallback to openai-whisper (PyTorch)
BACKEND = None
WHISPER_MODEL = None
try:
    from faster_whisper import WhisperModel
    BACKEND = "faster-whisper"
except ImportError:
    try:
        import whisper as _whisper
        BACKEND = "openai-whisper"
        WHISPER_MODEL = _whisper
    except ImportError:
        BACKEND = None


class Transcriber:
    def __init__(self, model_size="small", device="cpu", compute_type="int8"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        self.model = None
        self.backend = BACKEND

        if self.api_key and "sk-" in self.api_key:
            self.client = OpenAI(api_key=self.api_key)
            self.backend = "api"
        
        if self.backend == "faster-whisper":
            self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        elif self.backend == "openai-whisper":
            self.model = WHISPER_MODEL.load_model(model_size, device=device)

    def transcribe_file(self, path_or_bytesio):
        try:
            if isinstance(path_or_bytesio, (bytes, bytearray)):
                fd, tmp = tempfile.mkstemp(suffix=".webm")
                os.close(fd)
                with open(tmp, "wb") as f:
                    f.write(path_or_bytesio)
                result = self.transcribe_file(tmp)
                os.unlink(tmp)
                return result

            if hasattr(path_or_bytesio, "read"):
                data = path_or_bytesio.read()
                return self.transcribe_file(data)

            path = str(path_or_bytesio)

            if self.backend == "api":
                with open(path, "rb") as f:
                    r = self.client.audio.transcriptions.create(
                        model="whisper-1", file=f, response_format="text"
                    )
                    return r.strip()

            elif self.backend == "faster-whisper":
                segs, _ = self.model.transcribe(path, beam_size=5)
                text = " ".join(s.text for s in segs)
                return text.strip() or None

            elif self.backend == "openai-whisper":
                r = self.model.transcribe(path, beam_size=5)
                return r["text"].strip() or None

            return None
        except Exception as e:
            return None

    def transcribe_stream(self, audio_data):
        """Transcribe raw numpy float32 audio array."""
        try:
            if not isinstance(audio_data, np.ndarray):
                audio_data = np.frombuffer(audio_data, dtype=np.float32)

            if self.backend == "api":
                fd, tmp = tempfile.mkstemp(suffix=".wav")
                os.close(fd)
                ints = (audio_data * 32767).astype(np.int16)
                wav.write(tmp, 16000, ints)
                text = self.transcribe_file(tmp)
                os.unlink(tmp)
                return text

            elif self.backend == "faster-whisper":
                segs, _ = self.model.transcribe(audio_data, beam_size=5)
                text = " ".join(s.text for s in segs)
                return text.strip() or None

            elif self.backend == "openai-whisper":
                r = self.model.transcribe(audio_data, beam_size=5)
                return r["text"].strip() or None

            return None
        except Exception as e:
            return None
