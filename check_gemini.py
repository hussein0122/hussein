"""Non-destructive Gemini API smoke test; never prints credentials or response payloads."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        print("ERROR: GEMINI_API_KEY is not configured.", file=sys.stderr)
        return 2

    model = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Reply with one short word."},
            {"role": "user", "content": "Say READY."},
        ],
        "temperature": 0,
        "max_tokens": 8,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("empty model response")
    except urllib.error.HTTPError as exc:
        # Do not print request headers, key, or provider response body.
        print(f"ERROR: Gemini API returned HTTP {exc.code}. Check key validity, model access, and free-tier quota.", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError):
        print("ERROR: Could not reach Gemini API. Check network connectivity and retry.", file=sys.stderr)
        return 1
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
        print("ERROR: Gemini responded, but the response format was unexpected.", file=sys.stderr)
        return 1

    print(f"OK: Gemini API authentication and model response succeeded ({model}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
