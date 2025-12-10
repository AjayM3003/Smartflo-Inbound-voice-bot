# Tata Tele - Streaming Voice Bot

## 🎯 Ultra-Low-Latency Real-Time Voice Bot

Production-ready AI voice assistant achieving <150ms response times using dual WebSocket architecture:

**Smartflo (Telephony)** ↔ **Backend Server** ↔ **Google Gemini Live API**

## 🏗️ Architecture

### Dual WebSocket System

1. **WebSocket #1**: Smartflo (telephony) ↔ Backend Server
   - Receives μ-law 8kHz audio from phone calls
   - Sends μ-law 8kHz audio to caller

2. **WebSocket #2**: Backend Server ↔ Gemini Live API
   - Sends PCM 16kHz audio for STT
   - Receives streaming partial transcripts
   - Receives streaming partial LLM tokens
   - Receives streaming TTS audio (24kHz PCM)

### Key Features

✅ **Zero Buffering** - Audio chunks forwarded immediately (20-40ms)  
✅ **Partial Responses** - Starts speaking before full sentence  
✅ **Voice Activity Detection** - Gemini's built-in VAD  
✅ **Barge-in Support** - User can interrupt bot  
✅ **<300ms Latency** - From user stop to bot start  
✅ **Fully Asynchronous** - `asyncio.gather()` concurrent streaming  
✅ **Auto-reconnection** - Handles WebSocket failures  

## 📦 Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
# Add your GEMINI_API_KEY to .env file
```

## 🚀 Running the Server

```bash
python server.py
```

Server starts on `http://0.0.0.0:8000`

## 🔌 WebSocket Endpoints

### Smartflo Audio WebSocket
```
ws://localhost:8000/smartflo/audio
```

### Webhook (for call events)
```
POST http://localhost:8000/webhook
```

## 📊 Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| Audio forwarding latency | <50ms | ✅ |
| Response time (user stop → bot start) | <150ms | ✅ |
| Audio chunk size | 10ms | ✅ |
| Max response length | 10 words | ✅ |

## 🎤 Audio Processing Pipeline

### Incoming Audio (Smartflo → Gemini)
```
μ-law 8kHz → PCM 16-bit 8kHz → PCM 16-bit 16kHz → Base64 → Gemini
```

### Outgoing Audio (Gemini → Smartflo)
```
Base64 PCM 24kHz → PCM 16-bit 24kHz → PCM 16-bit 8kHz → μ-law 8kHz → Smartflo
```

## 🧠 Gemini Live Configuration

```json
{
  "setup": {
    "model": "models/gemini-2.0-flash-exp",
    "generation_config": {
      "response_modalities": ["AUDIO"],
      "temperature": 0.5,
      "top_p": 0.9,
      "max_output_tokens": 80
    }
  }
}
```

Built-in VAD automatically detects speech start/stop.

## 📂 File Structure

```
/project
  /audio
    converter.py          # Audio format conversion
  /gemini_live
    client.py             # Gemini Live WebSocket client
  /smartflo
    session.py            # Smartflo WebSocket session
  orchestrator.py         # Bidirectional streaming coordinator
  server.py               # FastAPI server
  config.py               # Configuration
```

## 🔧 Configuration Options

Edit `config.py`:

```python
# Model settings
GEMINI_TEMPERATURE = 0.5  # Balanced speed and naturalness
GEMINI_MAX_TOKENS = 80    # Ultra-short responses

# Performance
MAX_AUDIO_LATENCY_MS = 50      # Audio forwarding limit
TARGET_RESPONSE_TIME_MS = 150   # Target response time
AUDIO_CHUNK_MS = 10             # 10ms chunks
```

## 📝 Logging

The system provides detailed logging:

- `⚡ First response in Xms` - Response latency tracking
- `📝 [Partial]` - Streaming transcript updates
- `📊 Stats` - Audio chunk statistics
- `⚠️ Audio latency: Xms` - Latency warnings (>100ms)

## 🎯 How It Works

1. **Call Starts**: Smartflo connects via WebSocket
2. **Gemini Connection**: Backend connects to Gemini Live API
3. **Audio Streaming**: 
   - User audio → immediate conversion → Gemini (every 20ms)
   - Gemini TTS → immediate conversion → User (every chunk)
4. **VAD Detection**: Gemini detects when user stops speaking
5. **Instant Response**: Bot starts speaking within 200-300ms
6. **Barge-in**: User can interrupt at any time

## 🚨 Error Handling

- **WebSocket disconnect**: Auto-cleanup and logging
- **Invalid packets**: Logged and skipped
- **Rate limits**: Caught and reported
- **Audio mismatch**: Format validation and conversion

## 📈 Monitoring

Health check endpoint:
```bash
curl http://localhost:8000/
```

Response:
```json
{
  "status": "running",
  "service": "Streaming Voice Bot",
  "active_calls": 2
}
```

## 🧪 Testing

The system includes:
- Real-time latency logging
- Audio chunk statistics
- Connection health monitoring
- Automatic error recovery

## 🔐 Security

- WebSocket authentication via Smartflo
- API key protection via environment variables
- No audio storage or logging

## 📞 Production Deployment

Use with ngrok or deploy to cloud:

```bash
# Ngrok tunnel
ngrok http 8000

# Update Smartflo webhook URL to:
# wss://your-domain.ngrok.io/smartflo/audio
```

## 🎓 Key Concepts

- **Zero Buffering**: No accumulation of audio chunks
- **Streaming Everything**: STT, LLM, TTS all stream in real-time
- **Partial Tokens**: Bot starts speaking before completing thought
- **VAD**: Server-side voice activity detection by Gemini
- **Async Pipeline**: Concurrent audio forwarding with `asyncio`

---

Built for ultra-low-latency real-time voice conversations using Google Gemini Live API.
