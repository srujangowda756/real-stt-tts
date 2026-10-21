
from fastapi import WebSocket , WebSocketDisconnect,APIRouter
import httpx
from config import setting
from common_functions.stt import stt
from common_functions.tts import tts
from common_functions.llm import llm

websocket_app = APIRouter()


@websocket_app.websocket("/ws")
async def voice_socket(ws: WebSocket):
    await ws.accept()
    history = [{"role": "system", "content":  setting.SYSTEM_PROMPT}]

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            while True:
                audio = await ws.receive_bytes()
                try:
                    await ws.send_json({"type": "status", "state": "thinking"})
                    text = await stt(client, audio)
                    if not text:
                        await ws.send_json({"type": "status", "state": "listening"})
                        continue

                    await ws.send_json({"type": "transcript", "text": text})
                    history.append({"role": "user", "content": text})

                    reply = await llm(client, history)
                    history.append({"role": "assistant", "content": reply})
                    await ws.send_json({"type": "reply", "text": reply})

                    await ws.send_bytes(await tts(client, reply))
                except httpx.HTTPError as e:
                    await ws.send_json({"type": "error", "message": str(e)})
        except WebSocketDisconnect:
            pass