import asyncio
import json
import logging

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import setting
from common_functions.stt import stt
from common_functions.tts import tts
from websocket.session import (
    ConfigError,
    InterviewConfig,
    Session,
    generate_questions,
    parse_config,
    plan_turn,
)

log = logging.getLogger(__name__)
websocket_app = APIRouter(prefix="/v1/interviews")


async def receive_config(ws: WebSocket) -> InterviewConfig:
    msg = await asyncio.wait_for(ws.receive(), timeout=setting.CONFIG_TIMEOUT)
    if msg["type"] == "websocket.disconnect":
        raise WebSocketDisconnect(msg.get("code", 1000))
    if msg.get("text") is None:
        raise ConfigError("First message must be a text config message.")
    return parse_config(msg["text"])


def message_kind(raw: str) -> str | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data.get("type") if isinstance(data, dict) else None


def ended_event(session: Session) -> dict:
    return {
        "type": "ended",
        "reason": "finished" if session.finished else "user",
        "complete": session.finished,
        "transcript": session.grouped_transcript(),
    }


async def send_turn(ws, client, session: Session, text, turn):
    audio = await tts(client, turn.reply)
    session.commit(text, turn)
    await ws.send_json({"type": "reply", "text": turn.reply})
    if not session.finished:
        await ws.send_json(
            {"type": "progress", "current": session.idx + 1, "total": len(session.questions)}
        )
    await ws.send_bytes(audio)


async def handle_audio(ws, client, session: Session, audio: bytes):
    await ws.send_json({"type": "status", "state": "thinking"})
    text = await stt(client, audio)
    if not text:
        await ws.send_json({"type": "status", "state": "listening"})
        return
    await ws.send_json({"type": "transcript", "text": text})
    turn = await plan_turn(client, session, text)
    await send_turn(ws, client, session, text, turn)


async def handle_silence(ws, client, session: Session):
    await ws.send_json({"type": "status", "state": "thinking"})
    await send_turn(ws, client, session, None, session.silence_turn())

#=====function starts from here=====
@websocket_app.websocket("/stream")
async def voice_socket(ws: WebSocket):
    await ws.accept()
    try:
        cfg = await receive_config(ws)
    except ConfigError as e:
        await ws.send_json({"type": "error", "message": str(e)})
        await ws.close(code=1008)
        return
    except asyncio.TimeoutError:
        await ws.send_json({"type": "error", "message": "No config received."})
        await ws.close(code=1008)
        return
    except WebSocketDisconnect:
        return

    async with httpx.AsyncClient(timeout=setting.TIMEOUT) as client:
        try:
            try:  # own questions, or generate them from role / field / type / difficulty
                questions = cfg.questions or await generate_questions(client, cfg)
            except WebSocketDisconnect:
                raise
            except (ConfigError, httpx.HTTPError) as e:
                await ws.send_json({"type": "error", "message": str(e)})
                await ws.close(code=1011)
                return
            except Exception:
                log.exception("question generation failed")
                await ws.send_json({"type": "error", "message": "Could not prepare the interview."})
                await ws.close(code=1011)
                return

            session = Session(cfg=cfg, questions=questions)
            await ws.send_json({"type": "ready", "questions": questions})

            try:  # the server always speaks first
                turn = await plan_turn(client, session, None)
                await send_turn(ws, client, session, None, turn)
            except WebSocketDisconnect:
                raise
            except Exception:
                log.exception("opening turn failed")
                await ws.send_json({"type": "error", "message": "Could not start the session."})
                await ws.close(code=1011)
                return

            while True:
                msg = await ws.receive()
                if msg["type"] == "websocket.disconnect":
                    break

                frame_text = msg.get("text")
                audio = msg.get("bytes")
                kind = message_kind(frame_text) if frame_text is not None else None

                if kind == "end":
                    # Reply with the transcript so far, then close.
                    await ws.send_json(ended_event(session))
                    await ws.close(code=1000)
                    return
                if session.finished or (audio is None and kind != "silence"):
                    continue  # interview over, or nothing usable
                try:
                    if audio is not None:
                        await handle_audio(ws, client, session, audio)
                    else:
                        await handle_silence(ws, client, session)
                    if session.finished:
                        await ws.send_json(ended_event(session))
                except WebSocketDisconnect:
                    raise
                except httpx.HTTPError as e:
                    await ws.send_json({"type": "error", "message": str(e)})
                except Exception:
                    log.exception("turn failed")
                    await ws.send_json(
                        {"type": "error", "message": "Something went wrong on that turn. Try again."}
                    )
        except WebSocketDisconnect:
            pass
