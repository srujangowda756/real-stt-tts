import httpx
from config import setting
from common_functions.http_utils import check

async def tts(client: httpx.AsyncClient, text: str) -> bytes:
    r = await client.post(
        f"{setting.BASE_URL}/audio/speech",
        headers=setting.json_headers,
        json={
            "model": setting.TTS,
            "voice": "troy",
            "input":  text,
            "response_format": "wav",
        },
    )
    check(r, "tts")
    return r.content