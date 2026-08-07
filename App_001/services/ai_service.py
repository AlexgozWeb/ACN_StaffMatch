import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

AUTH_URL       = os.getenv("AICORE_AUTH_URL")
BASE_URL       = os.getenv("AICORE_BASE_URL")
CLIENT_ID      = os.getenv("AICORE_CLIENT_ID")
CLIENT_SECRET  = os.getenv("AICORE_CLIENT_SECRET")
RESOURCE_GROUP = os.getenv("AICORE_RESOURCE_GROUP")
DEPLOYMENT_ID  = os.getenv("AICORE_DEPLOYMENT_CLAUDE")

_token_cache = {"token": None, "exp": 0}

def get_token() -> str:
    if _token_cache["token"] and time.time() < _token_cache["exp"]:
        return _token_cache["token"]
    resp = requests.post(
        f"{AUTH_URL}/oauth/token",
        data={"grant_type": "client_credentials"},
        auth=(CLIENT_ID, CLIENT_SECRET),
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["exp"] = time.time() + data.get("expires_in", 3600) - 60
    return _token_cache["token"]

def call_claude(system_prompt: str, user_message: str, max_tokens: int = 2048) -> str:
    token = get_token()
    resp = requests.post(
        f"{BASE_URL}/v2/inference/deployments/{DEPLOYMENT_ID}/invoke",
        headers={
            "Authorization": f"Bearer {token}",
            "AI-Resource-Group": RESOURCE_GROUP,
            "Content-Type": "application/json",
        },
        json={
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]
