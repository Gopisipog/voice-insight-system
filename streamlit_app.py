"""
Voice Insight System - Streamlit Cloud Edition
Deploy on Streamlit Community Cloud.
Uses OpenAI Whisper API (no local model needed).
"""

import os
import io
import sys
import time
import tempfile
from pathlib import Path

import streamlit as st
import openai

# --- Core modules (use segmenter + shell_runner, but NOT local whisper) ---
# Streamlit Cloud has limited RAM, so we skip local Whisper loading
# and use OpenAI API for transcription.

# Set page config
st.set_page_config(
    page_title="Voice Insight System",
    page_icon="🎙️",
    layout="wide",
)

# --- Constants ---
DEMO_AUDIO_FILES = {
    "None - Upload your own": None,
}

# --- Session state ---
if "segments" not in st.session_state:
    st.session_state.segments = []
if "selected_segment" not in st.session_state:
    st.session_state.selected_segment = None
if "transcript_history" not in st.session_state:
    st.session_state.transcript_history = ""
if "api_key_configured" not in st.session_state:
    st.session_state.api_key_configured = bool(os.getenv("OPENAI_API_KEY", "")) or bool(os.getenv("OPENAI_API_KEY", "").startswith("sk-"))
if "openai_api_key" not in st.session_state:
    st.session_state.openai_api_key = os.getenv("OPENAI_API_KEY", "")


def init_core_modules():
    """Lazy-load core modules (only when needed)."""
    if "segmenter" not in st.session_state:
        from core.segmenter import SemanticSegmenter
        st.session_state.segmenter = SemanticSegmenter()
    if "shell_runner" not in st.session_state:
        from core.shell_runner import ShellRunner
        st.session_state.shell_runner = ShellRunner()


def convert_to_wav(audio_bytes: bytes) -> bytes:
    """Convert audio bytes to proper 16-bit 16kHz mono WAV using ffmpeg."""
    import subprocess
    
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp_in:
        tmp_in.write(audio_bytes)
        in_path = tmp_in.name
    
    out_path = os.path.join(tempfile.gettempdir(), "converted_output.wav")
    
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", in_path, "-ar", "16000", "-ac", "1", "-sample_fmt", "s16", out_path],
            capture_output=True, timeout=15, check=True
        )
        with open(out_path, "rb") as f:
            result = f.read()
        return result
    except:
        return None  # ffmpeg not available
    finally:
        try: os.unlink(in_path)
        except: pass
        try: os.unlink(out_path)
        except: pass


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """Transcribe audio using OpenAI Whisper API.
    Converts to proper WAV format for best accuracy.
    """
    client = openai.OpenAI(api_key=st.session_state.get("openai_api_key", os.getenv("OPENAI_API_KEY")))
    
    with st.spinner("🧠 Transcribing audio with Whisper..."):
        try:
            # Strategy 1: Convert to proper WAV using ffmpeg (best quality)
            wav_bytes = convert_to_wav(audio_bytes)
            
            if wav_bytes:
                # Send converted WAV to Whisper API
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=("audio.wav", wav_bytes, "audio/wav"),
                    response_format="text",
                )
                text = response.strip()
                if text:
                    return text
            
            # Strategy 2: Try original bytes as-is
            ext = Path(filename).suffix.lower()
            mime_map = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4", 
                        ".webm": "audio/webm", ".ogg": "audio/ogg", ".flac": "audio/flac"}
            mime = mime_map.get(ext, "audio/webm")
            
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=(filename, audio_bytes, mime),
                response_format="text",
            )
            return response.strip()
        
        except Exception as e:
            st.error(f"Transcription error: {e}")
            
            # Strategy 3: Last resort - try raw PCM interpretation
            try:
                import numpy as np
                import scipy.io.wavfile as wav
                import io as io_module
                
                # Try to interpret as raw PCM int16
                raw_data = np.frombuffer(audio_bytes, dtype=np.int16)
                if len(raw_data) > 2000:  # At least 0.1 sec of audio
                    buf = io_module.BytesIO()
                    wav.write(buf, 16000, raw_data)
                    response = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=("raw_audio.wav", buf.getvalue(), "audio/wav"),
                        response_format="text",
                    )
                    return response.strip()
            except:
                pass
            
            return ""


def process_text(text: str) -> list:
    """Run text through segmenter and return knowledge blocks."""
    init_core_modules()
    segmenter = st.session_state.segmenter
    
    # Feed text to segmenter and collect blocks
    blocks = segmenter.add_text(text)
    
    # Also flush any remaining buffer
    if segmenter.buffer.strip():
        segmenter.buffer = ""  # Reset for next input
    
    return blocks


def execute_command(command: str, input_text: str) -> str:
    """Run a shell command against input text."""
    init_core_modules()
    runner = st.session_state.shell_runner
    return runner.run_command(command, input_text)


def analyze_with_deepseek(text: str, instruction: str = "") -> str:
    """Analyze transcribed text using DeepSeek's chat API (much cheaper than OpenAI)."""
    api_key = st.session_state.get("deepseek_api_key", os.getenv("DEEPSEEK_API_KEY"))
    if not api_key or "sk-your" in api_key or api_key == "":
        return None  # No DeepSeek key configured
    
    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1"
    )
    
    system_prompt = instruction or "You are an insightful analysis assistant. Extract key insights, patterns, and action items from the transcribed speech. Be concise and specific."
    
    with st.spinner("🧠 Analyzing with DeepSeek..."):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this transcribed speech:\n\n{text}"}
                ],
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            st.warning(f"DeepSeek analysis error: {e}")
            return None


# ============================================================
# UI
# ============================================================

st.title("🎙️ Voice Insight System")
st.markdown("Upload audio → Transcribe → Segment into knowledge blocks → Filter with commands")

# --- Sidebar: API Key ---
with st.sidebar:
    st.header("🔑 Configuration")
    
    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        value=os.getenv("OPENAI_API_KEY", ""),
        help="Get your key at https://platform.openai.com/api-keys",
    )
    if api_key and api_key.startswith("sk-"):
        st.session_state.openai_api_key = api_key
        st.session_state.api_key_configured = True
        st.success("✅ API Key configured")
    elif api_key and not api_key.startswith("sk-"):
        st.warning("⚠️ Invalid key format (should start with 'sk-')")
    elif os.getenv("OPENAI_API_KEY"):
        st.session_state.api_key_configured = True
        st.success("✅ API Key from environment")
    else:
        st.warning("⚠️ Enter an OpenAI API key to transcribe audio")
    
    st.divider()
    
    st.header("🧠 DeepSeek Analysis")
    
    deepseek_key = st.text_input(
        "DeepSeek API Key (optional)",
        type="password",
        value=os.getenv("DEEPSEEK_API_KEY", ""),
        help="Get your key at https://platform.deepseek.com/api_keys. Much cheaper than OpenAI for text analysis.",
    )
    if deepseek_key:
        st.session_state.deepseek_api_key = deepseek_key
        if deepseek_key and not deepseek_key.startswith("sk-your"):
            st.success("✅ DeepSeek configured")
    
    deepseek_instruction = st.text_area(
        "Analysis instruction (optional)",
        value="Extract key insights, patterns, and action items from this speech. Be concise.",
        height=60,
        help="Custom instruction for DeepSeek on how to analyze the transcription",
    )
    
    st.divider()
    
    st.header("🔧 Pipeline Command")
    default_command = os.getenv("FILTER_COMMAND", 'powershell -Command "$input | findstr /i \'gap\'"')
    pipeline_command = st.text_area(
        "Command ($input = transcribed text)",
        value=default_command,
        height=80,
        help="Use $input to reference the transcribed text. Default: find lines with 'gap'",
    )
    
    st.divider()
    st.caption("Built with ❤️ using OpenAI Whisper + Streamlit")

# --- Main Area ---

col1, col2 = st.columns([1, 1])

with col1:
    st.header("📤 Upload Audio")
    
    # File upload (best option for accuracy)
    uploaded_file = st.file_uploader(
        "📁 Choose an audio file (best accuracy)",
        type=["wav", "mp3", "m4a", "webm", "ogg", "flac", "mp4"],
        help="Upload a recording of your voice or meeting",
    )
    
    # Browser mic recording
    st.markdown("**... or record directly from your browser:**")
    audio_data = st.audio_input("🎤 Click to record voice message")
    
    # Transcription trigger
    audio_bytes = None
    filename = None
    
    if uploaded_file is not None:
        audio_bytes = uploaded_file.read()
        filename = uploaded_file.name
        st.audio(audio_bytes, format=uploaded_file.type or "audio/webm")
        st.info(f"✅ Loaded {len(audio_bytes)} bytes from file")
    elif audio_data is not None:
        audio_bytes = audio_data.read()
        filename = "recording.webm"
        st.audio(audio_bytes)
        st.info(f"✅ Recorded {len(audio_bytes)} bytes from microphone. Click 'Transcribe & Analyze' below.")
    
    if audio_bytes and st.button("🎯 Transcribe & Analyze", type="primary", disabled=not st.session_state.api_key_configured):
        # Transcribe
        text = transcribe_audio(audio_bytes, filename or "audio.webm")
        
        if text:
            st.success(f"📝 Transcription: _{text}_")
            
            # Store in history
            if st.session_state.transcript_history:
                st.session_state.transcript_history += " " + text
            else:
                st.session_state.transcript_history = text
            
            # Process into segments
            new_blocks = process_text(text)
            for block in new_blocks:
                st.session_state.segments.append({
                    "id": int(time.time() * 1000) + len(st.session_state.segments),
                    "text": block,
                    "timestamp": time.strftime("%H:%M:%S"),
                })
            
            # Also add raw if no blocks formed
            if not new_blocks and len(text) > 20:
                st.session_state.segments.append({
                    "id": int(time.time() * 1000),
                    "text": text,
                    "timestamp": time.strftime("%H:%M:%S"),
                })
    
    # Show transcript history
    if st.session_state.transcript_history:
        with st.expander("📜 Full Transcript History"):
            st.text(st.session_state.transcript_history)

with col2:
    st.header("🧠 Knowledge Blocks")
    
    if not st.session_state.segments:
        st.info("Upload audio and click Transcribe to see segments here")
    else:
        for i, seg in enumerate(st.session_state.segments):
            is_selected = st.session_state.selected_segment == seg["id"]
            border = "2px solid #FF4B4B" if is_selected else "1px solid #ddd"
            
            with st.container():
                st.markdown(
                    f"""<div style="border:{border}; border-radius:8px; padding:12px; margin:8px 0; 
                    cursor:pointer; {'background:#FFF0F0' if is_selected else 'background:#FAFAFA'}">
                    <small style="color:#888;">{seg['timestamp']}</small>
                    <p style="margin:4px 0;">{seg['text']}</p>
                    </div>""",
                    unsafe_allow_html=True,
                )
                col_a, col_b = st.columns([1, 4])
                with col_a:
                    if st.button(f"🎯 Select #{i+1}", key=f"sel_{seg['id']}"):
                        st.session_state.selected_segment = seg["id"]
                        st.rerun()

# --- Command Execution Section ---
st.divider()
st.header("⚡ Execute Command on Selected Segment")

col_cmd1, col_cmd2 = st.columns([3, 1])

with col_cmd1:
    selected_seg_text = ""
    for seg in st.session_state.segments:
        if seg["id"] == st.session_state.selected_segment:
            selected_seg_text = seg["text"]
            break
    
    st.text_area(
        "Selected Input ($input)",
        value=selected_seg_text,
        height=80,
        disabled=True,
        key="input_display",
    )

with col_cmd2:
    st.markdown("##### &nbsp;")
    
    has_deepseek = st.session_state.get("deepseek_api_key") and not st.session_state.deepseek_api_key.startswith("sk-your")
    
    if has_deepseek and st.button("🧠 Analyze with DeepSeek", disabled=not selected_seg_text):
        with st.spinner("Analyzing..."):
            result = analyze_with_deepseek(selected_seg_text, deepseek_instruction)
            if result:
                st.session_state.last_output = f"[DeepSeek Analysis]\n{result}"
                st.balloons()
    
    if st.button("▶️ Run Command", type="primary", disabled=not selected_seg_text):
        with st.spinner("Executing..."):
            result = execute_command(pipeline_command, selected_seg_text)
            st.session_state.last_output = result
            
            # Also check for insights with the default filter
            if "gap" in result.lower() or "insight" in result.lower():
                st.balloons()

# Output display
if "last_output" in st.session_state and st.session_state.last_output:
    st.markdown("**📤 Output:**")
    
    output = st.session_state.last_output
    if "Error" in output[:20]:
        st.error(output)
    else:
        st.code(output, language="text")
        
        # Extract insights
        lines = [l for l in output.split("\n") if l.strip()]
        if lines:
            st.markdown("**🔍 Filtered Insights:**")
            for line in lines:
                st.markdown(f"- {line}")

# --- History Section ---
if st.session_state.segments:
    st.divider()
    with st.expander("🗑️ Session Management"):
        if st.button("Clear All Segments"):
            st.session_state.segments = []
            st.session_state.selected_segment = None
            st.session_state.transcript_history = ""
            if "last_output" in st.session_state:
                del st.session_state.last_output
            st.rerun()
