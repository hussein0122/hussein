"""Non-destructive Gemini API smoke test; transient 5xx must not block engine retries."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/openai"


def main() -> int:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        print("ERROR: GEMINI_API_KEY is not configured.", file=sys.stderr)
        return 2

    model = os.getenv("LLM_MODEL", "gemini-3.8-flash").strip()
    url = f"{API_ROOT}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Reply with one short word."},
            {"role": "user", "content": "Say READY."},
        ],
        "temperature": 0,
        "max_tokens": 8,
    }

    for attempt in range(1, 4):
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty model response")
            print(f"OK: Gemini API authentication and model response succeeded ({model}).")
            return 0
        except urllib.error.HTTPError as exc:
            try:
                body = json.loads(exc.read().decode("utf-8"))
                error = body.get("error", {})
                detail = error.get("message", "") if isinstance(error, dict) else ""
            except Exception:
                detail = ""
            if exc.code >= 500:
                if attempt < 3:
                    delay = 5 * (2 ** (attempt - 1))
                    print(f"WARNING: Gemini HTTP {exc.code}; smoke-test retry {attempt}/3 in {delay}s.")
                    time.sleep(delay)
                    continue
                print(
                    f"::warning::Gemini returned HTTP {exc.code} after smoke-test retries. "
                    "Continuing to the engine, which has its own longer retry window. "
                    + (f"Provider detail: {detail[:250]}" if detail else "")
                )
                return 0
            if exc.code == 429:
                reason = "Gemini rate limit or quota was reached; check quota and retry later."
            elif exc.code in (401, 403):
                reason = "Gemini rejected the API key or its API permissions."
            elif exc.code == 404:
                reason = f"Model '{model}' was not found or is not enabled for this API key."
            else:
                reason = f"Gemini returned HTTP {exc.code}."
            if detail:
                reason += f" Provider detail: {detail[:300]}"
            print(f"ERROR: {reason}", file=sys.stderr)
            return 1
        except (urllib.error.URLError, TimeoutError):
            if attempt < 3:
                delay = 5 * (2 ** (attempt - 1))
                print(f"WARNING: Gemini network issue; smoke-test retry {attempt}/3 in {delay}s.")
                time.sleep(delay)
                continue
            print(
                "::warning::Gemini smoke test could not reach the service after retries. "
                "Continuing to the engine's own retry window."
            )
            return 0
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
            print("ERROR: Gemini responded, but the response format was unexpected.", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
