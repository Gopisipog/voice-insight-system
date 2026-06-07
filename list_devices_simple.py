import pyaudio
p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    ch = info.get('maxInputChannels', 0)
    if ch > 0:
        print(f'[{i}] {info["name"]} - {ch}ch, {info.get("defaultSampleRate", 0):.0f}Hz')
p.terminate()
