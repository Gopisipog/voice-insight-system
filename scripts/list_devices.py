import pyaudio

def list_audio_devices():
    p = pyaudio.PyAudio()
    print("\n--- Available Audio Input Sources ---")
    print(f"{'ID':<5} {'Name':<50} {'Channels':<10}")
    
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        # We look for devices with input channels
        if dev['maxInputChannels'] > 0:
            print(f"{i:<5} {dev['name']:<50} {dev['maxInputChannels']:<10}")
            
    print("\n--- Available Audio Output Sources (For Loopback) ---")
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if dev['maxOutputChannels'] > 0:
            print(f"{i:<5} {dev['name']:<50}")
            
    print("\nTIP: Look for 'Stereo Mix' or 'Wave Out Mix'.")
    print("If you don't see them, right-click the speaker icon in your system tray -> 'Sound Settings' -> 'Manage sound devices' and Enable 'Stereo Mix'.")
    p.terminate()

if __name__ == "__main__":
    list_audio_devices()
