# Smartflo-Gemini Live Bridge 🎙️

Production-ready Python backend service that connects **Tata Tele Smartflo** inbound calls to **Google Gemini Live (Realtime API)** using WebSockets for real-time voice AI conversations.

## 🎯 Features

- ✅ Full-duplex WebSocket audio streaming
- ✅ Real-time bidirectional communication between Smartflo and Gemini Live
- ✅ FastAPI-based high-performance server
- ✅ Concurrent audio forwarding using asyncio
- ✅ Production-ready error handling and logging
- ✅ Supports 8kHz PCM telephony audio
- ✅ Configurable voice (Aoede by default)
- ✅ Health check endpoints
- ✅ Easy deployment with ngrok

## 📋 Prerequisites

- Python 3.8 or higher
- Google Cloud account with Gemini API access
- Gemini API Key (get from [Google AI Studio](https://makersuite.google.com/app/apikey))
- Tata Tele Smartflo account
- ngrok account (for public HTTPS/WSS exposure)

## 🚀 Installation

### 1. Clone or Create Project

```powershell
# Navigate to your project directory
cd e:\Tata-tele
```

### 2. Create Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Update the `.env` file:
```
GOOGLE_API_KEY=your-actual-google-api-key-here
```

## 🏃 Running the Server

### Local Development

```powershell
# Make sure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Run with Python
python server.py

# OR run with uvicorn directly
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

The server will start on `http://localhost:8000`

### Verify Server is Running

Open your browser and visit:
- Health check: http://localhost:8000/health
- Root endpoint: http://localhost:8000/

You should see JSON responses confirming the server is running.

## 🌐 Exposing with ngrok

To connect Smartflo to your local server, you need to expose it publicly using ngrok.

### 1. Install ngrok

Download from: https://ngrok.com/download

Or using chocolatey:
```powershell
choco install ngrok
```

### 2. Configure ngrok (First Time Only)

```powershell
# Add your authtoken from ngrok dashboard
ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN
```

### 3. Start ngrok Tunnel

In a **new terminal window** (keep server running in the first):

```powershell
ngrok http 8000
```

You'll see output like:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
```

### 4. Get Your WebSocket URL

Your Smartflo WebSocket URL will be:
```
wss://abc123.ngrok-free.app/smartflo/ws
```

⚠️ **Important:** Replace `https://` with `wss://` for the WebSocket connection!

## 📞 Configuring Smartflo

### Step 1: Log into Smartflo Dashboard
Go to your Tata Tele Smartflo portal.

### Step 2: Create/Edit Call Flow
1. Navigate to **Call Flows**
2. Create a new flow or edit an existing one
3. Add a **WebSocket** node

### Step 3: Configure WebSocket Node
- **WebSocket URL:** `wss://your-ngrok-url.ngrok-free.app/smartflo/ws`
- **Protocol:** WebSocket
- **Audio Format:** PCM 8kHz 16-bit (or whatever Smartflo sends)

### Step 4: Save and Test
- Save the call flow
- Assign it to a phone number
- Make a test call!

## 🔧 Configuration Options

### Changing the AI Voice

Edit `server.py` and change the `VOICE_NAME` variable:

```python
VOICE_NAME = "Aoede"  # Options: Aoede, Charon, Fenrir, Kore, Puck
```

### Customizing System Instructions

Edit the `system_instruction` in the `send_setup_messages()` method:

```python
"system_instruction": {
    "parts": [
        {
            "text": "Your custom instructions here..."
        }
    ]
}
```

### Audio Configuration

Modify `GEMINI_AUDIO_CONFIG` if needed:

```python
GEMINI_AUDIO_CONFIG = {
    "encoding": "pcm_s16le",  # 16-bit PCM
    "sample_rate": 8000,  # 8kHz for telephony
}
```

## 📊 Monitoring and Logs

The server provides detailed logging:

```powershell
# Watch logs in real-time
python server.py
```

Log levels:
- `INFO`: Connection events, message forwarding
- `DEBUG`: Detailed audio chunk information
- `ERROR`: Connection failures, processing errors

## 🐛 Troubleshooting

### API Key Issues
```
Error: Google API key not configured
```
**Solution:** Check your `.env` file has the correct `GOOGLE_API_KEY`

### Connection Failed to Gemini
```
Failed to connect to Gemini Live
```
**Solution:** 
- Verify API key is valid
- Check internet connection
- Ensure Gemini API is enabled in your Google Cloud project

### Smartflo Not Connecting
```
Smartflo disconnected
```
**Solution:**
- Verify ngrok is running
- Check WebSocket URL in Smartflo config starts with `wss://`
- Ensure server is running and accessible

### No Audio Received
```
Received empty audio data from Smartflo
```
**Solution:**
- Check Smartflo audio format matches server configuration
- Verify microphone permissions in Smartflo setup

## 📁 Project Structure

```
e:\Tata-tele\
├── server.py              # Main FastAPI server
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create this)
├── .env.example          # Example environment file
└── README.md             # This file
```

## 🔒 Production Deployment

For production, consider:

1. **Use a proper hosting service** (not ngrok):
   - AWS EC2 with Elastic IP
   - Google Cloud Compute Engine
   - DigitalOcean Droplet
   - Heroku or Railway

2. **Add HTTPS/WSS with proper certificates**:
   - Let's Encrypt SSL
   - Nginx reverse proxy

3. **Environment management**:
   - Use secrets management (AWS Secrets Manager, etc.)
   - Never commit `.env` file

4. **Add monitoring**:
   - Application Performance Monitoring (APM)
   - Error tracking (Sentry)
   - Log aggregation (ELK stack)

5. **Scale with**:
   - Load balancer
   - Multiple server instances
   - Redis for session management

## 🛠️ Development Commands

```powershell
# Install in development mode
pip install -r requirements.txt

# Run with auto-reload
uvicorn server:app --reload

# Run with custom host/port
uvicorn server:app --host 0.0.0.0 --port 5000

# Format code (optional)
pip install black
black server.py
```

## 📝 API Endpoints

### WebSocket Endpoint
- **URL:** `wss://your-domain.com/smartflo/ws`
- **Purpose:** Bidirectional audio streaming
- **Protocol:** WebSocket

### Health Check
- **URL:** `GET /health`
- **Response:**
```json
{
  "status": "healthy",
  "google_api_configured": true,
  "model": "gemini-2.0-flash-live-001",
  "voice": "Aoede",
  "audio_config": {
    "encoding": "pcm_s16le",
    "sample_rate": 8000
  }
}
```

### Root
- **URL:** `GET /`
- **Purpose:** Basic health check

## 🤝 Support

For issues related to:
- **Smartflo:** Contact Tata Tele support
- **Gemini API:** Check [Google AI documentation](https://ai.google.dev/docs)
- **This server:** Check logs and error messages

## 📄 License

This is a reference implementation for educational and development purposes.

## 🎉 Quick Start Summary

1. Install Python dependencies: `pip install -r requirements.txt`
2. Create `.env` file with your Google API key
3. Run server: `python server.py`
4. In new terminal, run ngrok: `ngrok http 8000`
5. Copy ngrok URL (change `https://` to `wss://`)
6. Configure in Smartflo: `wss://your-ngrok-url.ngrok-free.app/smartflo/ws`
7. Make a test call! 📞

---

**Built with ❤️ for seamless AI voice conversations**
