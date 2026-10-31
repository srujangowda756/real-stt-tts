import httpx
from config import setting
from common_functions.http_utils import check


async def _chat(client: httpx.AsyncClient, messages: list, **extra) -> str:
    r = await client.post(
        f"{setting.BASE_URL}/chat/completions",
        headers=setting.json_headers,
        json={
            "model": setting.LLM,
            "messages": messages,
            "reasoning_effort": "low",
            "max_completion_tokens": 2048,  # reasoning tokens count against this
            **extra,
        },
    )
    check(r, "llm")
    content = r.json()["choices"][0]["message"]["content"] or ""
    return content.strip()


async def llm(client: httpx.AsyncClient, messages: list) -> str:
    """Plain text reply."""
    return await _chat(client, messages)


async def llm_json(client: httpx.AsyncClient, messages: list) -> str:
    """JSON-mode reply (the prompt must mention JSON). Returns the raw string."""
    return await _chat(client, messages, response_format={"type": "json_object"})
