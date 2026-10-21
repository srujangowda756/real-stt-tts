
import httpx

def check(r: httpx.Response, stage: str):
    if r.status_code >= 400:
        raise httpx.HTTPError(f"{stage} {r.status_code}: {r.text}")