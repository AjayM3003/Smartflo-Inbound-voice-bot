"""
Gemini Live API WebSocket client.
Handles real-time bidirectional streaming with Gemini.
"""
import asyncio
import json
import logging
import time
from typing import Callable, Optional
import websockets
from audio.converter import AudioConverter
from config import (
    GEMINI_WS_URL,
    GEMINI_MODEL,
    GEMINI_TEMPERATURE,
    GEMINI_TOP_P,
    GEMINI_MAX_TOKENS
)

logger = logging.getLogger(__name__)


class GeminiLiveClient:
    """
    WebSocket client for Gemini Live API.
    Provides real-time STT → LLM → TTS streaming.
    """
    
    def __init__(self):
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.converter = AudioConverter()
        
        # Callbacks
        self.audio_callback: Optional[Callable] = None
        self.transcript_callback: Optional[Callable] = None
        self.vad_callback: Optional[Callable] = None  # VAD events
        
        # VAD state tracking
        self.user_speaking = False
        self.bot_speaking = False
        
    async def connect(self):
        """Establish WebSocket connection to Gemini Live API."""
        try:
            logger.info(f"Connecting to Gemini Live API...")
            self.ws = await websockets.connect(
                GEMINI_WS_URL,
                max_size=10_000_000,
                ping_interval=10,
                ping_timeout=5
            )
            self.connected = True
            logger.info("✅ Connected to Gemini Live API")
            
            # Send session configuration immediately
            await self._send_config()
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Gemini: {e}")
            self.connected = False
            raise
    
    async def _send_config(self):
        """Send setup message to Gemini Live API."""
        config = {
            "setup": {
                "model": f"models/{GEMINI_MODEL}",
                "generation_config": {
                    "response_modalities": ["AUDIO"],
                    "speech_config": {
                        "voice_config": {
                            "prebuilt_voice_config": {
                                "voice_name": "Puck"
                            }
                        }
                    },
                    "temperature": GEMINI_TEMPERATURE,
                    "top_p": GEMINI_TOP_P,
                    "max_output_tokens": GEMINI_MAX_TOKENS
                },
                "system_instruction": {
                    "parts": [{
                        "text": (
                            "You are Asha, Tata Tele assistant. Speak Hinglish. "
                            "CRITICAL: Keep ALL responses under 10 words. Be extremely brief. "
                            "One question at a time only. No explanations. "
                            "First message: 'Namaste! Main Asha. Kaise madad karoon?' "
                            "Then: Ultra-short responses like 'Ji boliye', 'Theek hai', 'Aapka number?', 'Samajh gayi'. "
                            "Never give long answers. Speed is critical."
                        )
                    }]
                },
                "tools": []
            }
        }
        
        await self.ws.send(json.dumps(config))
        logger.info("📤 Sent Gemini Live configuration (VAD enabled)")
    
    async def send_audio_chunk(self, pcm_data: bytes):
        """
        Send audio chunk to Gemini immediately (no buffering).
        
        Args:
            pcm_data: PCM 16-bit audio chunk at 16kHz
        """
        if not self.connected or not self.ws:
            return
        
        try:
            # Mark user as speaking (VAD state)
            if not self.user_speaking:
                self.user_speaking = True
                logger.debug("🎤 User started speaking")
            
            # Base64 encode
            audio_b64 = self.converter.to_base64(pcm_data)
            
            # Send in realtime_input format
            message = {
                "realtime_input": {
                    "media_chunks": [{
                        "mime_type": "audio/pcm",
                        "data": audio_b64
                    }]
                }
            }
            
            await self.ws.send(json.dumps(message))
            
        except Exception as e:
            logger.error(f"Error sending audio to Gemini: {e}")
    
    async def receive_events(self):
        """
        Receive and process real-time events from Gemini.
        Forwards audio chunks immediately with <100ms latency.
        """
        if not self.connected or not self.ws:
            raise RuntimeError("Not connected to Gemini")
        
        try:
            async for message in self.ws:
                start_time = time.time()
                
                try:
                    data = json.loads(message)
                    
                    # Handle server content messages
                    if "serverContent" in data:
                        server_content = data["serverContent"]
                        
                        # Check for model turn (includes audio output)
                        if "modelTurn" in server_content:
                            model_turn = server_content["modelTurn"]
                            
                            # Bot started speaking (VAD detected user stopped)
                            if not self.bot_speaking:
                                self.bot_speaking = True
                                self.user_speaking = False
                                logger.info("🤖 Bot speaking (VAD: user stopped)")
                                
                                if self.vad_callback:
                                    await self.vad_callback("user_stopped")
                            
                            # Bot started speaking
                            if not self.bot_speaking:
                                self.bot_speaking = True
                                logger.info("🤖 Bot started speaking")
                            
                            # Handle parts (audio and text)
                            for part in model_turn.get("parts", []):
                                # Audio output (TTS)
                                if "inlineData" in part:
                                    inline_data = part["inlineData"]
                                    mime_type = inline_data.get("mimeType", "")
                                    
                                    if mime_type.startswith("audio/") and self.audio_callback:
                                        audio_b64 = inline_data.get("data", "")
                                        if audio_b64:
                                            # Decode and forward immediately
                                            audio_data = self.converter.from_base64(audio_b64)
                                            await self.audio_callback(audio_data)
                                            
                                            # Log latency
                                            latency_ms = (time.time() - start_time) * 1000
                                            if latency_ms > 50:
                                                logger.warning(f"⚠️  Audio latency: {latency_ms:.0f}ms")
                                
                                # Text output (transcripts/responses)
                                if "text" in part and self.transcript_callback:
                                    text = part["text"]
                                    if text:
                                        await self.transcript_callback(text, partial=False)
                        
                        # Turn complete signal (VAD: bot finished speaking)
                        if "turnComplete" in server_content and server_content["turnComplete"]:
                            self.bot_speaking = False
                            logger.info("✅ Turn complete - waiting for user")
                            
                            if self.vad_callback:
                                await self.vad_callback("turn_complete")
                        
                        # Interrupted signal (user interrupted bot)
                        if "interrupted" in server_content and server_content["interrupted"]:
                            self.bot_speaking = False
                            self.user_speaking = True
                            logger.info("🔇 Bot interrupted by user")
                            
                            if self.vad_callback:
                                await self.vad_callback("interrupted")
                            
                            # Trigger VAD callback
                            if self.vad_callback:
                                await self.vad_callback("turn_complete")
                        
                        # Interrupted signal (user started speaking while bot was talking)
                        if "interrupted" in server_content and server_content["interrupted"]:
                            self.bot_speaking = False
                            logger.info("🔇 Bot interrupted by user speech")
                            
                            if self.vad_callback:
                                await self.vad_callback("interrupted")
                    
                    # Handle setup completion
                    if "setupComplete" in data:
                        logger.info("✅ Gemini Live setup complete - VAD enabled")
                    
                    # Handle tool call responses (future use)
                    if "toolCallCancellation" in data:
                        logger.debug("Tool call cancelled")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from Gemini: {e}")
                except Exception as e:
                    logger.error(f"Error processing Gemini event: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Gemini WebSocket connection closed")
            self.connected = False
        except Exception as e:
            logger.error(f"Error in Gemini receive loop: {e}")
            self.connected = False
            raise
    
    async def close(self):
        """Close the WebSocket connection."""
        if self.ws:
            await self.ws.close()
            self.connected = False
            logger.info("Closed Gemini WebSocket connection")
