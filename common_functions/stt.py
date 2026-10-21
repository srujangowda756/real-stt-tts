import httpx
from config import setting
from common_functions.http_utils import check

async def stt(client: httpx.AsyncClient, audio: bytes) -> str:
    r = await client.post(
        f"{setting.BASE_URL}/audio/transcriptions",
        headers=setting.auth_headers,
        files={"file": ("audio.webm", audio, "audio/webm")},
        data={"model": setting.STT, "response_format": "json"},
    )
    check(r, "stt")
    return r.json()["text"].strip()