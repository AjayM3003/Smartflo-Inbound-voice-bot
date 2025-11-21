"""
Tata Tele Smartflo to Google Gemini Live WebSocket Bridge
Production-ready FastAPI server for real-time audio streaming
"""

import os
import asyncio
import json
import logging
from typing import Optional
from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import websockets
from websockets.exceptions import ConnectionClosed

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Smartflo-Gemini Bridge",
    description="WebSocket bridge between Tata Tele Smartflo and Google Gemini Live",
    version="1.0.0"
)

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash-live-001"
GEMINI_WS_URL = f"wss://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:connectBidiStream?key={GOOGLE_API_KEY}"

# Audio configuration for Gemini
GEMINI_AUDIO_CONFIG = {
    "encoding": "pcm_s16le",  # 16-bit PCM
    "sample_rate": 8000,  # 8kHz for telephony
}

# Voice configuration
VOICE_NAME = "Aoede"  # Can be changed to other available voices


class GeminiLiveConnection:
    """Manages connection to Google Gemini Live API"""
    
    def __init__(self):
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
    
    async def connect(self):
        """Establish connection to Gemini Live"""
        try:
            logger.info(f"Connecting to Gemini Live: {GEMINI_MODEL}")
            self.websocket = await websockets.connect(
                GEMINI_WS_URL,
                ping_interval=20,
                ping_timeout=10,
                max_size=10_000_000  # 10MB max message size
            )
            self.connected = True
            logger.info("Successfully connected to Gemini Live")
            
            # Send initial setup configuration
            await self.send_setup_messages()
            
        except Exception as e:
            logger.error(f"Failed to connect to Gemini Live: {e}")
            raise
    
    async def send_setup_messages(self):
        """Send initial configuration to Gemini Live"""
        try:
            # Setup message with model configuration
            setup_message = {
                "setup": {
                    "model": f"models/{GEMINI_MODEL}",
                    "generation_config": {
                        "response_modalities": ["AUDIO"],
                        "speech_config": {
                            "voice_config": {
                                "prebuilt_voice_config": {
                                    "voice_name": VOICE_NAME
                                }
                            }
                        }
                    },
                    "system_instruction": {
                        "parts": [
                            {
                                "text": "You are a helpful voice assistant for Tata Tele customers. "
                                        "Provide concise, clear, and friendly responses. "
                                        "Keep your answers brief and to the point since this is a phone call."
                            }
                        ]
                    }
                }
            }
            
            await self.websocket.send(json.dumps(setup_message))
            logger.info("Sent setup configuration to Gemini Live")
            
            # Wait for setup acknowledgment
            response = await self.websocket.recv()
            logger.info(f"Received setup response: {response}")
            
        except Exception as e:
            logger.error(f"Error sending setup messages: {e}")
            raise
    
    async def send_audio_chunk(self, audio_data: bytes):
        """Send audio chunk to Gemini Live"""
        if not self.connected or not self.websocket:
            raise Exception("Not connected to Gemini Live")
        
        try:
            # Create realtime input message with media chunk
            message = {
                "realtime_input": {
                    "media_chunks": [
                        {
                            "mime_type": f"audio/{GEMINI_AUDIO_CONFIG['encoding']}",
                            "data": audio_data.hex()  # Send as hex string
                        }
                    ]
                }
            }
            
            await self.websocket.send(json.dumps(message))
            
        except Exception as e:
            logger.error(f"Error sending audio chunk: {e}")
            raise
    
    async def receive_messages(self):
        """Receive messages from Gemini Live"""
        if not self.connected or not self.websocket:
            raise Exception("Not connected to Gemini Live")
        
        try:
            async for message in self.websocket:
                yield message
        except ConnectionClosed:
            logger.warning("Gemini Live connection closed")
            self.connected = False
        except Exception as e:
            logger.error(f"Error receiving from Gemini Live: {e}")
            self.connected = False
    
    async def close(self):
        """Close connection to Gemini Live"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("Closed Gemini Live connection")


async def forward_smartflo_to_gemini(
    smartflo_ws: WebSocket,
    gemini_conn: GeminiLiveConnection
):
    """
    Forward audio from Smartflo to Gemini Live
    """
    try:
        logger.info("Starting Smartflo -> Gemini audio forwarding")
        
        while True:
            # Receive audio data from Smartflo
            audio_data = await smartflo_ws.receive_bytes()
            
            if not audio_data:
                logger.warning("Received empty audio data from Smartflo")
                continue
            
            logger.debug(f"Received {len(audio_data)} bytes from Smartflo")
            
            # Forward to Gemini Live
            await gemini_conn.send_audio_chunk(audio_data)
            
    except WebSocketDisconnect:
        logger.info("Smartflo disconnected")
    except Exception as e:
        logger.error(f"Error in Smartflo -> Gemini forwarding: {e}")
        raise


async def forward_gemini_to_smartflo(
    smartflo_ws: WebSocket,
    gemini_conn: GeminiLiveConnection
):
    """
    Forward audio from Gemini Live back to Smartflo
    """
    try:
        logger.info("Starting Gemini -> Smartflo audio forwarding")
        
        async for message in gemini_conn.receive_messages():
            try:
                # Parse Gemini response
                response_data = json.loads(message)
                
                # Log the response type for debugging
                logger.debug(f"Received from Gemini: {list(response_data.keys())}")
                
                # Check for server content (audio output)
                if "serverContent" in response_data:
                    server_content = response_data["serverContent"]
                    
                    # Check for model turn with parts
                    if "modelTurn" in server_content:
                        parts = server_content["modelTurn"].get("parts", [])
                        
                        for part in parts:
                            # Extract audio data from inline_data
                            if "inlineData" in part:
                                inline_data = part["inlineData"]
                                
                                if "data" in inline_data:
                                    # Audio data is in hex format, convert to bytes
                                    audio_hex = inline_data["data"]
                                    audio_bytes = bytes.fromhex(audio_hex)
                                    
                                    logger.debug(f"Sending {len(audio_bytes)} bytes to Smartflo")
                                    
                                    # Send audio back to Smartflo
                                    await smartflo_ws.send_bytes(audio_bytes)
                
                # Handle tool calls or other response types if needed
                elif "toolCall" in response_data:
                    logger.info("Received tool call from Gemini")
                
                # Handle setup complete
                elif "setupComplete" in response_data:
                    logger.info("Gemini setup completed successfully")
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response: {e}")
            except Exception as e:
                logger.error(f"Error processing Gemini response: {e}")
                
    except Exception as e:
        logger.error(f"Error in Gemini -> Smartflo forwarding: {e}")
        raise


@app.get("/")
async def root():
    """Health check endpoint"""
    return JSONResponse({
        "status": "running",
        "service": "Smartflo-Gemini Bridge",
        "model": GEMINI_MODEL,
        "version": "1.0.0"
    })


@app.get("/health")
async def health():
    """Detailed health check"""
    api_key_configured = bool(GOOGLE_API_KEY and GOOGLE_API_KEY != "your-api-key-here")
    
    return JSONResponse({
        "status": "healthy" if api_key_configured else "misconfigured",
        "google_api_configured": api_key_configured,
        "model": GEMINI_MODEL,
        "voice": VOICE_NAME,
        "audio_config": GEMINI_AUDIO_CONFIG
    })


@app.websocket("/smartflo/ws")
async def smartflo_websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for Smartflo calls
    Handles bidirectional audio streaming between Smartflo and Gemini Live
    """
    gemini_conn = None
    
    try:
        # Accept Smartflo connection
        await websocket.accept()
        logger.info(f"Smartflo connected from {websocket.client}")
        
        # Validate API key
        if not GOOGLE_API_KEY or GOOGLE_API_KEY == "your-api-key-here":
            logger.error("Google API key not configured")
            await websocket.close(code=1008, reason="Server misconfigured: API key missing")
            return
        
        # Initialize and connect to Gemini Live
        gemini_conn = GeminiLiveConnection()
        await gemini_conn.connect()
        
        # Run both forwarding directions concurrently
        await asyncio.gather(
            forward_smartflo_to_gemini(websocket, gemini_conn),
            forward_gemini_to_smartflo(websocket, gemini_conn)
        )
        
    except WebSocketDisconnect:
        logger.info("Smartflo disconnected normally")
    except Exception as e:
        logger.error(f"Error in WebSocket handler: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason=f"Server error: {str(e)}")
        except:
            pass
    finally:
        # Clean up Gemini connection
        if gemini_conn:
            await gemini_conn.close()
        logger.info("WebSocket session ended")


if __name__ == "__main__":
    import uvicorn
    
    # Check for API key before starting
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "your-api-key-here":
        logger.error("GOOGLE_API_KEY not set in environment variables!")
        logger.error("Please create a .env file with: GOOGLE_API_KEY=your-actual-api-key")
        exit(1)
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )
