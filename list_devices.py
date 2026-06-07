"""List available audio input devices for voice capture."""
import pyaudio

p = pyaudio.PyAudio()
print("=== Audio Input Devices ===")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info.get('maxInputChannels', 0) > 0:
        print(f"  [{i}] {info.get('name')} - {info.get('maxInputChannels')}ch, {info.get('defaultSampleRate')}Hz")
p.terminate()
