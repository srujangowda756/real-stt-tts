import logging
import re

import httpx
from config import setting
from common_functions.http_utils import check

log = logging.getLogger(__name__)

# Phrases Whisper-type models commonly invent from silence or noise.
HALLUCINATIONS = {"you", "thank you", "thanks", "thanks for watching", "thank you for watching", "bye"}


def clean_transcript(data: dict) -> str:
    """Drop non-speech segments and junk; return "" when nothing real was said."""
    segments = data.get("segments") or []
    if segments:
        kept = [
            s for s in segments
            if not (
                s.get("no_speech_prob", 0) > setting.STT_NO_SPEECH_MAX
                and s.get("avg_logprob", 0) < setting.STT_LOGPROB_MIN
            )
        ]
        text = " ".join((s.get("text") or "").strip() for s in kept)
    else:
        text = data.get("text") or ""
    text = text.strip()
    if not re.search(r"[^\W_]", text):  # no letters or digits at all
        return ""
    if re.sub(r"[^\w\s]", "", text.lower()).strip() in HALLUCINATIONS:
        return ""
    return text


async def stt(client: httpx.AsyncClient, audio: bytes) -> str:
    form = {"model": setting.STT, "response_format": "verbose_json"}
    if setting.STT_LANGUAGE:
        form["language"] = setting.STT_LANGUAGE
    r = await client.post(
        f"{setting.BASE_URL}/audio/transcriptions",
        headers=setting.auth_headers,
        files={"file": ("audio.webm", audio, "audio/webm")},
        data=form,
    )
    check(r, "stt")
    body = r.json()
    text = clean_transcript(body)
    raw = (body.get("text") or "").strip()
    if raw and not text:
        log.info("stt dropped as non-speech: %r", raw)  # watch these while tuning the thresholds
    return text
