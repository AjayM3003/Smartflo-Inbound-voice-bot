"""
Real-time streaming orchestrator.
Coordinates bidirectional audio streaming between Smartflo and Gemini Live.
"""
import asyncio
import logging
import time
from smartflo.session import SmartfloAudioSession
from gemini_live.client import GeminiLiveClient
from audio.converter import AudioConverter

logger = logging.getLogger(__name__)


class StreamingOrchestrator:
    """
    Orchestrates real-time bidirectional streaming:
    Smartflo ↔ Backend ↔ Gemini Live API
    
    Zero buffering, immediate forwarding, <300ms latency.
    """
    
    def __init__(self, smartflo_session: SmartfloAudioSession):
        self.smartflo_session = smartflo_session
        self.gemini_client = GeminiLiveClient()
        self.converter = AudioConverter()
        
        # State
        self.running = False
        self.tasks = []
        
        # Performance tracking
        self.audio_in_count = 0
        self.audio_out_count = 0
        self.last_user_audio_time = 0
        self.response_start_time = None
        
    async def start(self):
        """
        Start the streaming pipeline.
        Implements fully asynchronous bidirectional streaming.
        """
        try:
            logger.info("🚀 Starting streaming orchestrator...")
            
            # Connect to Gemini Live
            await self.gemini_client.connect()
            
            self.running = True
            
            # Set up bidirectional streaming callbacks
            self._setup_callbacks()
            
            # Launch concurrent tasks
            tasks = [
                asyncio.create_task(self._forward_smartflo_to_gemini()),
                asyncio.create_task(self._forward_gemini_to_smartflo()),
                asyncio.create_task(self._health_check())
            ]
            
            self.tasks = tasks
            
            # Wait for all tasks
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Error in streaming orchestrator: {e}", exc_info=True)
        finally:
            await self.stop()
    
    def _setup_callbacks(self):
        """Setup callbacks for bidirectional audio flow."""
        
        # Smartflo → Gemini
        async def handle_smartflo_audio(ulaw_data: bytes):
            """Process audio from Smartflo, convert, forward to Gemini immediately."""
            try:
                # Detect if user is interrupting bot response
                if self.response_start_time is not None:
                    # User is speaking while bot is responding - interrupt!
                    logger.info("🔇 User interrupting - stopping bot response")
                    self.response_start_time = None
                
                self.last_user_audio_time = time.time()
                self.audio_in_count += 1
                
                # Convert μ-law 8kHz → PCM 16kHz
                pcm_data = self.converter.smartflo_to_gemini(ulaw_data)
                
                # Send to Gemini IMMEDIATELY
                await self.gemini_client.send_audio_chunk(pcm_data)
                
            except Exception as e:
                logger.error(f"Error in audio-in pipeline: {e}")
        
        # Gemini → Smartflo
        async def handle_gemini_audio(pcm_data: bytes):
            """Process audio from Gemini, convert, forward to Smartflo immediately."""
            try:
                # Track response latency
                if self.response_start_time is None:
                    response_latency = (time.time() - self.last_user_audio_time) * 1000
                    logger.info(f"⚡ First response in {response_latency:.0f}ms")
                    self.response_start_time = time.time()
                
                self.audio_out_count += 1
                
                # Convert Gemini PCM 24kHz → μ-law 8kHz
                ulaw_data = self.converter.gemini_to_smartflo(pcm_data, gemini_rate=24000)
                
                # Send to Smartflo IMMEDIATELY
                await self.smartflo_session.send_audio(ulaw_data)
                
            except Exception as e:
                logger.error(f"Error in audio-out pipeline: {e}")
        
        # Transcript callback (for logging/debugging)
        async def handle_transcript(text: str, partial: bool = False):
            """Handle partial/final transcripts from Gemini."""
            prefix = "[Partial]" if partial else "[Final]"
            logger.info(f"📝 {prefix} {text}")
        
        # Set callbacks
        self.smartflo_session.on_audio_callback = handle_smartflo_audio
        self.gemini_client.audio_callback = handle_gemini_audio
        self.gemini_client.transcript_callback = handle_transcript
    
    async def _forward_smartflo_to_gemini(self):
        """
        Task: Forward audio from Smartflo to Gemini.
        Runs continuously, zero buffering.
        """
        try:
            logger.info("▶️  Smartflo → Gemini audio forwarding started")
            
            # The actual forwarding happens in the callback
            # This task just keeps the session alive
            while self.running and self.smartflo_session.connected:
                await asyncio.sleep(1)
        
        except Exception as e:
            logger.error(f"Error in Smartflo→Gemini task: {e}")
    
    async def _forward_gemini_to_smartflo(self):
        """
        Task: Receive events from Gemini and forward audio to Smartflo.
        Runs continuously, processes events immediately.
        """
        try:
            logger.info("◀️  Gemini → Smartflo audio forwarding started")
            
            # Receive events from Gemini (blocks until connection closes)
            await self.gemini_client.receive_events()
        
        except Exception as e:
            logger.error(f"Error in Gemini→Smartflo task: {e}")
    
    async def _health_check(self):
        """
        Task: Monitor connection health and log statistics.
        """
        try:
            logger.info("💓 Health check started")
            
            while self.running:
                try:
                    await asyncio.sleep(30)  # Check every 30 seconds to reduce overhead
                    
                    logger.info(
                        f"📊 Stats: Audio IN: {self.audio_in_count}, "
                        f"Audio OUT: {self.audio_out_count}"
                    )
                    
                    # Reset response tracking for next turn
                    if self.audio_out_count > 0:
                        self.response_start_time = None
                except asyncio.CancelledError:
                    break
        
        except Exception as e:
            logger.error(f"Error in health check: {e}")
    
    async def stop(self):
        """Stop the orchestrator and cleanup."""
        logger.info("🛑 Stopping streaming orchestrator...")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Close connections
        await self.gemini_client.close()
        await self.smartflo_session.close()
        
        logger.info("✅ Streaming orchestrator stopped")
