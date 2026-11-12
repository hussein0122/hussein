"""Verify Gemini through the exact OpenAI-compatible endpoint used by the engine."""
from __future__ import annotations
import json
import os
import sys
import time
import urllib.error
import urllib.request

CHAT_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
MODEL = "gemini-3.8-flash"

def request_model(key: str) -> tuple[int, str]:
    payload = {"model": MODEL, "messages": [{"role": "user", "content": "Reply with the single word OK."}], "max_tokens": 8}
    request = urllib.request.Request(
        CHAT_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            json.loads(response.read().decode("utf-8"))
            return response.status, ""
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("error", {}).get("message", "")
        except Exception:
            detail = ""
        return exc.code, detail[:400]
    except Exception as exc:
        return 0, f"{type(exc).__name__}: {exc}"

def main() -> int:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        print("ERROR: GEMINI_API_KEY is not configured.", file=sys.stderr)
        return 2
    status, detail = 0, ""
    for attempt in range(1, 4):
        status, detail = request_model(key)
        if status == 200:
            break
        if status in (401, 403):
            print(f"ERROR: Google rejected the Gemini API key or API access (HTTP {status}). {detail}", file=sys.stderr)
            return 1
        if status == 404:
            print(f"ERROR: {MODEL} is not available through the engine endpoint. {detail}", file=sys.stderr)
            return 1
        if status in (429, 503, 0):
            print(f"WARNING: Gemini temporary response on probe {attempt}/3: HTTP {status}. {detail}")
            if attempt < 3:
                time.sleep(5 * attempt)
                continue
            # Preserve the current model; do not fall back to a retired model.
            break
        print(f"ERROR: Gemini probe failed with HTTP {status}. {detail}", file=sys.stderr)
        return 1
    github_env = os.getenv("GITHUB_ENV")
    if github_env:
        with open(github_env, "a", encoding="utf-8") as env_file:
            env_file.write(f"LLM_MODEL={MODEL}\n")
    if status == 200:
        print(f"OK: {MODEL} responded through the exact endpoint used by the video engine.")
    else:
        print(f"WARNING: Keeping {MODEL} after temporary service trouble; engine retries remain enabled.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
