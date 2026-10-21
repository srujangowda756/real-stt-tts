# Real-Time Voice Agent (STT + LLM + TTS)

A real-time voice assistant backend powered by FastAPI, WebSockets, and Groq APIs.

## Architecture

```
User (Audio WebM) ──WebSocket──> FastAPI Server
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
            1. STT (Whisper-large-v3)      2. LLM (gpt-oss-120b)
                     │                               │
                     └───────────────┬───────────────┘
                                     ▼
                            3. TTS (Orpheus-v1)
                                     │
WebSocket ◄── WAV Audio Stream ──────┘
```

## Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/srujangowda756/real-stt-tts.git
cd real-stt-tts
```

### 2. Create and activate virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Copy `.env.example` to `.env` and add your Groq API key:
```bash
cp .env.example .env
```
Inside `.env`:
```env
GROQ_API_KEY=your_groq_api_key_here
```

## Running the Server

Start the development server with Uvicorn:
```bash
uvicorn main:app --reload --port 8000
```

The WebSocket endpoint will be accessible at:
`ws://localhost:8000/ws`

## WebSocket Events

- **Receive from client**: Raw audio binary (`audio/webm`)
- **Send to client**:
  - `{"type": "status", "state": "thinking" | "listening"}`
  - `{"type": "transcript", "text": "..."}`
  - `{"type": "reply", "text": "..."}`
  - `{"type": "error", "message": "..."}`
  - Binary bytes (`audio/wav`) of the generated speech reply