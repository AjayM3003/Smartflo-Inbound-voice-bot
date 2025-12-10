"""
FastAPI server for streaming voice bot.
Dual WebSocket architecture: Smartflo ↔ Backend ↔ Gemini Live
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from smartflo.session import SmartfloAudioSession
from orchestrator import StreamingOrchestrator
from config import SERVER_HOST, SERVER_PORT, LOG_LEVEL

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Active sessions
active_sessions = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 Starting Streaming Voice Bot Server...")
    yield
    logger.info("🛑 Shutting down server...")
    # Cleanup active sessions
    for call_id, session in list(active_sessions.items()):
        try:
            await session.stop()
        except:
            pass


app = FastAPI(
    title="Streaming Voice Bot",
    description="Ultra-low-latency real-time voice bot using Gemini Live API",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "running",
        "service": "Streaming Voice Bot",
        "active_calls": len(active_sessions)
    }


@app.post("/webhook")
async def smartflo_webhook(request: Request):
    """
    Webhook endpoint for Smartflo call events.
    Receives ANSWERED, RINGING, HANGUP events.
    """
    try:
        body = await request.json()
        call_id = body.get("call_id")
        event_type = body.get("event_type", "ANSWERED")
        
        logger.info(f"📞 Webhook: {event_type} for call {call_id}")
        
        return JSONResponse({
            "status": "ok",
            "call_id": call_id,
            "message": "Call acknowledged"
        })
    
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.websocket("/smartflo/audio")
async def smartflo_audio_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for Smartflo audio streaming.
    
    This is WebSocket #1: Smartflo ↔ Backend
    Receives μ-law audio from Smartflo, sends μ-law audio back.
    """
    call_id = None
    orchestrator = None
    
    try:
        logger.info("=" * 80)
        logger.info("🔌 Smartflo WebSocket connection attempt")
        
        # Create session
        session = SmartfloAudioSession(websocket)
        await session.accept()
        
        # Create orchestrator (will connect to Gemini)
        orchestrator = StreamingOrchestrator(session)
        
        # Start streaming in background
        stream_task = asyncio.create_task(orchestrator.start())
        
        # Handle Smartflo events (blocks until connection closes)
        await session.handle_events()
        
        # Wait for streaming to complete
        await stream_task
        
    except WebSocketDisconnect:
        logger.info("📞 Smartflo WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in Smartflo WebSocket: {e}", exc_info=True)
    finally:
        if orchestrator:
            await orchestrator.stop()
        if call_id and call_id in active_sessions:
            del active_sessions[call_id]
        logger.info("=" * 80)


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {SERVER_HOST}:{SERVER_PORT}")
    
    uvicorn.run(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level=LOG_LEVEL.lower()
    )
