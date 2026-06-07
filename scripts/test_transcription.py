import sys
import os
# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.transcriber import Transcriber

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_transcription.py <path_to_audio_file>")
        return

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    transcriber = Transcriber(model_size="tiny") # Use tiny for fast testing
    text = transcriber.transcribe_file(file_path)
    print(f"\n--- Result ---\n{text}")

if __name__ == "__main__":
    main()
