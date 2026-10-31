import asyncio
import re
import struct

import httpx

from config import setting
from common_functions.http_utils import check

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_CLAUSE_END = re.compile(r"(?<=[,;:])\s+")


def clean_for_tts(text: str) -> str:
    """Orpheus reads [bracketed] words as vocal directions, so remove the brackets."""
    text = text.replace("[", "").replace("]", "")
    return re.sub(r"\s+", " ", text).strip()


def _pack(parts: list[str], limit: int) -> list[str]:
    chunks, current = [], ""
    for part in parts:
        candidate = f"{current} {part}".strip()
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = part
    if current:
        chunks.append(current)
    return chunks


def split_text(text: str, limit: int | None = None) -> list[str]:
    """Cut text into pieces of at most `limit` characters: sentences first, then
    commas, then spaces, and only as a last resort in the middle of a word."""
    limit = limit or setting.TTS_CHUNK_CHARS
    text = clean_for_tts(text)
    if len(text) <= limit:
        return [text] if text else []

    for pattern in (_SENTENCE_END, _CLAUSE_END):
        parts = pattern.split(text)
        if len(parts) > 1:
            pieces = []
            for part in parts:
                pieces.extend(split_text(part, limit) if len(part) > limit else [part])
            return _pack(pieces, limit)

    words = []
    for word in text.split(" "):
        words.extend(word[i : i + limit] for i in range(0, len(word), limit))
    return _pack(words, limit)


def _parse_wav(data: bytes) -> tuple[tuple[int, int, int, int], bytes]:
    """Return ((format_tag, channels, sample_rate, bits), raw_audio). Tolerates streaming
    headers whose data size is 0 or 0xFFFFFFFF."""
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("TTS did not return a WAV file")
    pos, fmt, pcm = 12, None, None
    while pos + 8 <= len(data):
        chunk_id = data[pos : pos + 4]
        size = struct.unpack("<I", data[pos + 4 : pos + 8])[0]
        body = pos + 8
        if chunk_id == b"fmt ":
            tag, channels, rate, _, _, bits = struct.unpack("<HHIIHH", data[body : body + 16])
            fmt = (tag, channels, rate, bits)
        elif chunk_id == b"data":
            end = body + size
            if size in (0, 0xFFFFFFFF) or end > len(data):
                end = len(data)
            pcm = data[body:end]
            break
        pos = body + size + (size & 1)
    if fmt is None or pcm is None:
        raise ValueError("Unsupported WAV layout")
    return fmt, pcm


def merge_wavs(parts: list[bytes], lead_silence_ms: int = 0) -> bytes:
    parsed = [_parse_wav(p) for p in parts]
    fmt = parsed[0][0]
    if any(f != fmt for f, _ in parsed):
        raise ValueError("TTS pieces have different audio formats")
    tag, channels, rate, bits = fmt
    block = channels * bits // 8
    fill = b"\x80" if bits == 8 else b"\x00"
    silence = fill * (int(rate * lead_silence_ms / 1000) * block)
    pcm = silence + b"".join(p for _, p in parsed)
    header = (
        b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVE"
        + b"fmt " + struct.pack("<IHHIIHH", 16, tag, channels, rate, rate * block, block, bits)
        + b"data" + struct.pack("<I", len(pcm))
    )
    return header + pcm


async def _speak(client: httpx.AsyncClient, text: str) -> bytes:
    r = await client.post(
        f"{setting.BASE_URL}/audio/speech",
        headers=setting.json_headers,
        json={
            "model": setting.TTS,
            "voice": "troy",
            "input": text,
            "response_format": "wav",
        },
    )
    check(r, "tts")
    return r.content


async def tts(client: httpx.AsyncClient, text: str) -> bytes:
    """Speak text of any length: split it, generate the pieces concurrently, return one WAV."""
    pieces = split_text(text)
    if not pieces:
        raise ValueError("nothing to speak")
    audios = await asyncio.gather(*(_speak(client, p) for p in pieces))
    if len(audios) == 1 and setting.TTS_LEAD_SILENCE_MS == 0:
        return audios[0]
    return merge_wavs(list(audios), setting.TTS_LEAD_SILENCE_MS)
