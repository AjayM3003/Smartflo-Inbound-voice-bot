"""
Smartflo Audio WebSocket Session.
Handles incoming audio from Smartflo and outgoing audio to caller.
"""
import asyncio
import base64
import json
import logging
import time
from typing import Callable, Optional
from fastapi import WebSocket
from audio.converter import AudioConverter

logger = logging.getLogger(__name__)


class SmartfloAudioSession:
    """
    Manages WebSocket connection with Smartflo for real-time audio streaming.
    """
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.connected = False
        self.stream_sid: Optional[str] = None
        self.call_sid: Optional[str] = None
        
        # Callbacks
        self.on_audio_callback: Optional[Callable] = None
        self.on_start_callback: Optional[Callable] = None
        self.on_stop_callback: Optional[Callable] = None
        
        # Audio converter
        self.converter = AudioConverter()
        
        # Statistics
        self.audio_chunks_received = 0
        self.audio_chunks_sent = 0
        self.start_time = None
        
    async def accept(self):
        """Accept the WebSocket connection."""
        await self.websocket.accept()
        self.connected = True
        self.start_time = time.time()
        logger.info("✅ Smartflo WebSocket connected")
    
    async def handle_events(self):
        """
        Main event loop - processes incoming Smartflo events.
        Forwards audio chunks immediately with minimal latency.
        """
        try:
            async for message in self.websocket.iter_text():
                try:
                    data = json.loads(message)
                    event_type = data.get("event")
                    
                    if event_type == "connected":
                        await self._handle_connected(data)
                    
                    elif event_type == "start":
                        await self._handle_start(data)
                    
                    elif event_type == "media":
                        # CRITICAL: Forward audio immediately
                        await self._handle_media(data)
                    
                    elif event_type == "stop":
                        await self._handle_stop(data)
                        break
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from Smartflo: {e}")
                except Exception as e:
                    logger.error(f"Error processing Smartflo event: {e}")
        
        except Exception as e:
            logger.error(f"Error in Smartflo event loop: {e}")
        finally:
            self.connected = False
            logger.info(f"📊 Session stats: Received {self.audio_chunks_received} chunks, Sent {self.audio_chunks_sent} chunks")
    
    async def _handle_connected(self, message: dict):
        """Handle 'connected' event."""
        logger.info("🔗 Smartflo connected event")
    
    async def _handle_start(self, message: dict):
        """Handle 'start' event with stream metadata."""
        start_data = message.get("start", {})
        self.stream_sid = message.get("streamSid") or start_data.get("streamSid")
        self.call_sid = start_data.get("callSid")
        
        caller_from = start_data.get("from")
        caller_to = start_data.get("to")
        
        logger.info(f"📞 Call started: {self.call_sid}")
        logger.info(f"   From: {caller_from} → To: {caller_to}")
        
        # Trigger start callback
        if self.on_start_callback:
            await self.on_start_callback()
    
    async def _handle_media(self, message: dict):
        """
        Handle incoming audio chunk from Smartflo.
        Forward to Gemini IMMEDIATELY with zero buffering.
        """
        media = message.get("media", {})
        payload_b64 = media.get("payload")
        
        if not payload_b64:
            return
        
        try:
            # Decode base64 μ-law audio
            ulaw_data = base64.b64decode(payload_b64)
            self.audio_chunks_received += 1
            
            # Forward to callback IMMEDIATELY (no buffering!)
            if self.on_audio_callback:
                await self.on_audio_callback(ulaw_data)
        
        except Exception as e:
            logger.error(f"Error processing media: {e}")
    
    async def _handle_stop(self, message: dict):
        """Handle 'stop' event - stream ended."""
        stop_data = message.get("stop", {})
        reason = stop_data.get("reason", "Unknown")
        
        duration = time.time() - self.start_time if self.start_time else 0
        logger.info(f"📞 Call ended: {reason} (duration: {duration:.1f}s)")
        
        # Trigger stop callback
        if self.on_stop_callback:
            await self.on_stop_callback()
    
    async def send_audio(self, ulaw_data: bytes):
        """
        Send audio chunk to Smartflo (to caller).
        Must be μ-law 8kHz, multiple of 160 bytes.
        
        Args:
            ulaw_data: μ-law encoded audio
        """
        if not self.connected or not self.stream_sid:
            return
        
        try:
            # Ensure multiple of 160 bytes (required by Smartflo)
            if len(ulaw_data) % 160 != 0:
                padding = 160 - (len(ulaw_data) % 160)
                ulaw_data = ulaw_data + (b'\xff' * padding)  # Silent padding
            
            # Base64 encode
            payload_b64 = base64.b64encode(ulaw_data).decode('utf-8')
            
            # Send immediately
            message = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": payload_b64
                }
            }
            
            await self.websocket.send_text(json.dumps(message))
            self.audio_chunks_sent += 1
        
        except Exception as e:
            logger.error(f"Error sending audio to Smartflo: {e}")
    
    async def close(self):
        """Close the WebSocket connection."""
        if self.connected:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.debug(f"Error closing websocket: {e}")
            finally:
                self.connected = False
                logger.info("Closed Smartflo WebSocket")
