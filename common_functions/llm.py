from config import setting
import httpx
from common_functions.http_utils import check

async def llm(client: httpx.AsyncClient, history: list) -> str:
    r = await client.post(
        f"{setting.BASE_URL}/chat/completions",
        headers=setting.json_headers,
        json={
            "model": setting.LLM,
            "messages": history,
            "reasoning_effort": "low",
            "max_completion_tokens": 1024,
        },
    )
    check(r, "llm")
    return r.json()["choices"][0]["message"]["content"].strip()
