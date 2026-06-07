import { useState, useEffect, useRef } from 'react'
import './App.css'

function App() {
  const VITE_SERVER_PORT = import.meta.env.VITE_SERVER_PORT || '';
  const VITE_BACKEND_HOST = import.meta.env.VITE_BACKEND_HOST || 'localhost';
  const PROTO = window.location.protocol === 'https:' ? 'https:' : 'http:';
  const WS_PROTO = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const PORT_SUFFIX = VITE_SERVER_PORT ? `:${VITE_SERVER_PORT}` : '';
  const BASE_HTTP = `${PROTO}//${VITE_BACKEND_HOST}${PORT_SUFFIX}`;
  const [segments, setSegments] = useState([]);
  const [selectedSegment, setSelectedSegment] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [command, setCommand] = useState('powershell -Command "$input | ForEach-Object { $_.ToUpper() }"');
  const [output, setOutput] = useState('');
  const [status, setStatus] = useState('Checking Connection...');
  
  const socketRef = useRef(null);
  const audioSocketRef = useRef(null);
  const mediaRecorderRef = useRef(null);

  // Core Connection Handler
  useEffect(() => {
    let reconnectTimer;
    const connect = () => {
      // Close any existing sockets before reconnecting
      if (socketRef.current) socketRef.current.close();
      if (audioSocketRef.current) audioSocketRef.current.close();

      const BACKEND = `${WS_PROTO}//${VITE_BACKEND_HOST}${PORT_SUFFIX}`;
      socketRef.current = new WebSocket(`${BACKEND}/ws/live`);
      socketRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'new_segment') {
          setSegments(prev => [{ id: Date.now(), ...data }, ...prev]);
        }
      };

      audioSocketRef.current = new WebSocket(`${BACKEND}/ws/audio`);
      audioSocketRef.current.onopen = () => setStatus('System Ready');
      audioSocketRef.current.onerror = (e) => console.error('WS error:', e);
      audioSocketRef.current.onclose = () => {
        setStatus('Offline - Retrying...');
        clearTimeout(reconnectTimer);
        reconnectTimer = setTimeout(connect, 5000);
      };
    };
    connect();
    return () => {
      clearTimeout(reconnectTimer);
      socketRef.current?.close();
      audioSocketRef.current?.close();
    };
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, sampleRate: 16000 } });
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioCtx.createMediaStreamSource(stream);
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      source.connect(processor);
      // Don't connect processor to destination (no need to hear mic audio)

      let audioChunks = [];
      let lastSendTime = Date.now();
      processor.onaudioprocess = (event) => {
        try {
          if (audioSocketRef.current?.readyState === WebSocket.OPEN) {
            const input = event.inputBuffer.getChannelData(0);
            // Copy the data into a new buffer
            const copy = new Float32Array(input);
            audioChunks.push(copy);
            
            // Send every ~1s worth of audio (~16000 samples at 16kHz)
            const totalSamples = audioChunks.reduce((sum, c) => sum + c.length, 0);
            if (totalSamples >= 16000 || Date.now() - lastSendTime > 1000) {
              const merged = new Float32Array(totalSamples);
              let offset = 0;
              for (const chunk of audioChunks) {
                merged.set(chunk, offset);
                offset += chunk.length;
              }
              audioSocketRef.current.send(merged.buffer);
              audioChunks = [];
              lastSendTime = Date.now();
            }
          }
        } catch (e) {
          console.error('Audio send error:', e);
        }
      };

      mediaRecorderRef.current = { processor, source, audioCtx, stream };
      setIsRecording(true);
      setStatus('Streaming Audio...');
      fetch(`${BASE_HTTP}/toggle-mic?active=true`, { method: 'POST' });
    } catch (err) {
      setStatus('Mic Error: ' + err.message);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      const { processor, source, audioCtx, stream } = mediaRecorderRef.current;
      processor.disconnect();
      source.disconnect();
      audioCtx.close();
      stream.getTracks().forEach(t => t.stop());
      setIsRecording(false);
      setStatus('System Ready');
      fetch(`${BASE_HTTP}/toggle-mic?active=false`, { method: 'POST' });
    }
  };

  const executeOnInput = async () => {
    if (!selectedSegment) return;
    setOutput('Executing against $input...');
    try {
      const res = await fetch(`${BASE_HTTP}/run-command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          command: command, 
          input: selectedSegment.text 
        })
      });
      const data = await res.json();
      setOutput(data.output || 'Command executed. (No output returned)');
    } catch (err) {
      setOutput('Backend unreachable.');
    }
  };

  return (
    <div className="dashboard">
      <nav className="sidebar">
        <div className="logo-container">
          <div className="logo">VoiceInsight</div>
          <div className="status-badge">{status}</div>
        </div>
        
        <button 
          className={`mic-btn ${isRecording ? 'listening' : ''}`} 
          onClick={isRecording ? stopRecording : startRecording}
        >
          {isRecording ? 'Stop Stream' : 'Open Voice Stream'}
        </button>
        
        <div className="command-section">
          <label className="section-label">Active Input ($input)</label>
          <div className="armed-preview">
            {selectedSegment ? (
              <p>"{selectedSegment.text.substring(0, 80)}..."</p>
            ) : (
              <span className="placeholder">Select a segment to load it...</span>
            )}
          </div>

          <label className="section-label">Pipeline Command</label>
          <textarea 
            className="command-input"
            value={command} 
            onChange={(e) => setCommand(e.target.value)}
            placeholder="e.powershell -Command '$input | ...'"
          />
          
          <button 
            className="execute-btn" 
            onClick={executeOnInput} 
            disabled={!selectedSegment}
          >
            Run Command on Segment
          </button>
        </div>

        <div className="download-section">
          <button className="download-btn" onClick={() => window.open('https://github.com/Gopisipog/voice-insight-system/releases/latest', '_blank')}>
            ⬇ Download Desktop App
          </button>
          <span className="download-hint">Windows • macOS • Linux</span>
        </div>
      </nav>

      <main className="content">
        <header className="content-header">
          <h2>Semantic Segments</h2>
          <span className="hint">Click a block to load it into $input</span>
        </header>

        <div className="segments-list">
          {segments.length === 0 && <div className="empty-state">Speak to generate insights...</div>}
          {segments.map((s) => (
            <div 
              key={s.id} 
              className={`segment-card ${selectedSegment?.id === s.id ? 'selected' : ''}`} 
              onClick={() => setSelectedSegment(s)}
            >
              <div className="segment-meta">{s.timestamp}</div>
              <div className="segment-text">{s.text}</div>
              {selectedSegment?.id === s.id && <div className="armed-tag">LOADED</div>}
            </div>
          ))}
        </div>

        <div className="console-area">
          <div className="console-header">$output</div>
          <div className="console-body">
            <pre>{output || 'System idle. Waiting for execution...'}</pre>
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
