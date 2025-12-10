# Start Tata Tele Streaming Voice Bot
# Quick startup script

Write-Host "🚀 Starting Tata Tele Streaming Voice Bot..." -ForegroundColor Green
Write-Host ""

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "❌ Error: .env file not found!" -ForegroundColor Red
    Write-Host "Please create .env file with GEMINI_API_KEY" -ForegroundColor Yellow
    exit 1
}

# Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Error: Python not found!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Environment OK" -ForegroundColor Green
Write-Host "📡 Starting server on http://0.0.0.0:8000" -ForegroundColor Cyan
Write-Host ""

# Start server
python server.py
