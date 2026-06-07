"""
Voice Insight System - Demo Runner
Runs the core pipeline: Transcription → Semantic Segmentation → Shell Filtering
Demonstrates the system capabilities without Telegram dependency.
"""
import os
import sys
import time

# Set HF cache to E: drive (has more space)
os.environ["HF_HOME"] = r"E:\.hf-cache"

from core.transcriber import Transcriber
from core.segmenter import SemanticSegmenter
from core.shell_runner import ShellRunner

def main():
    print("=" * 60)
    print("🎙️  VOICE INSIGHT SYSTEM - DEMO")
    print("=" * 60)
    
    # 1. Initialize core components
    print("\n[1/4] Initializing Transcriber (Whisper tiny)...")
    transcriber = Transcriber(model_size="tiny", device="cpu")
    
    print("\n[2/4] Initializing Semantic Segmenter...")
    segmenter = SemanticSegmenter()
    
    print("\n[3/4] Initializing Shell Runner...")
    runner = ShellRunner()
    
    # 2. Find a sample audio file or generate a test
    print("\n[4/4] Setting up filter command...")
    filter_cmd = os.getenv("FILTER_COMMAND", 
                           'powershell -Command "$input | findstr /i \'gap\'"')
    print(f"    Filter: {filter_cmd}")
    
    print("\n" + "=" * 60)
    print("🔄 SIMULATING VOICE INPUT (text-based for demo)")
    print("=" * 60 + "\n")
    
    # Simulate streaming voice input with semantic segmentation
    test_transcripts = [
        "Um, so I was thinking about the market gap in our current product line.",
        "There's a huge opportunity for a new feature that addresses customer pain points.",
        "The team needs to focus on improving the user interface for better adoption.",
        "I identified a gap in how we handle customer onboarding and retention.",
        "Testing the audio pipeline makes sure everything works smoothly end to end.",
    ]
    
    print("Processing voice transcripts through the pipeline...\n")
    
    for i, text in enumerate(test_transcripts):
        print(f"  [{i+1}] Raw Transcript: \"{text}\"")
        
        # Run through semantic segmenter
        units = segmenter.add_text(text)
        
        if units:
            for unit in units:
                print(f"      → Segment produced: \"{unit}\"")
                # Run through shell filter
                result = runner.run_command(filter_cmd, unit)
                if result.strip():
                    print(f"      🔍 Insight Found: {result.strip()}")
                else:
                    print(f"      ✓ No insight trigger (filter didn't match)")
        else:
            print(f"      → Buffered (waiting for more context)")
        
        print()
        time.sleep(0.5)  # Simulate real-time
    
    # Force flush any remaining buffer
    print("Force-flushing remaining buffer...")
    if segmenter.buffer.strip():
        print(f"  Final buffer: \"{segmenter.buffer}\"")
        result = runner.run_command(filter_cmd, segmenter.buffer)
        if result.strip():
            print(f"  🔍 Insight Found: {result.strip()}")
    
    print("\n" + "=" * 60)
    print("✅ DEMO COMPLETE")
    print("=" * 60)
    print("\nThe Voice Insight System pipeline works as follows:")
    print("  1. 🎤 Audio Capture (mic / file / browser)")
    print("  2. 📝 Transcription via Whisper (faster-whisper)")
    print("  3. 🧠 Semantic Segmentation (knowledge blocks of ~3 sentences)")
    print("  4. 🔬 Shell Command Filtering (custom PowerShell/CMD scripts)")
    print("  5. 📬 (Optional) Telegram Bot notification")
    print("\nTwo deployment approaches available:")
    print("  • main_hub.py     - Local desktop hub (mic→transcribe→shell→Telegram)")
    print("  • server.py       - Backend server + PWA (record on mobile, execute on desktop)")
    
if __name__ == "__main__":
    main()
