"""
Configuration for streaming voice bot.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Gemini Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash-exp"
GEMINI_WS_URL = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={GEMINI_API_KEY}"

# Model Settings - Ultra-fast, natural responses
GEMINI_TEMPERATURE = 0.5  # Balanced for speed and naturalness
GEMINI_TOP_P = 0.9
GEMINI_MAX_TOKENS = 80   # Very short responses for minimal latency

# Audio Configuration
SMARTFLO_SAMPLE_RATE = 8000  # μ-law 8kHz
GEMINI_SAMPLE_RATE = 16000   # PCM 16kHz for Gemini
AUDIO_CHUNK_MS = 10          # 10ms chunks for ultra-low latency

# Server Configuration
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000

# Performance Targets
MAX_AUDIO_LATENCY_MS = 50    # Max latency for audio forwarding
TARGET_RESPONSE_TIME_MS = 150 # Target time from user stop to bot start

# Logging
LOG_LEVEL = "INFO"
ENABLE_LATENCY_LOGGING = True
