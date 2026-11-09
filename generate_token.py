"""Create a local YouTube OAuth token for ShortsPilot AR.

Place the downloaded Google OAuth Desktop JSON beside this script as credentials.json.
Run: python generate_token.py
The script opens Google's consent page, saves token.json, and writes token_b64.txt.
Never commit or share credentials.json, token.json, or token_b64.txt.
"""
from __future__ import annotations

import base64
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = Path(__file__).resolve().parent
CLIENT_FILE = ROOT / "credentials.json"
TOKEN_FILE = ROOT / "token.json"
B64_FILE = ROOT / "token_b64.txt"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> int:
    if not CLIENT_FILE.is_file():
        print("ERROR: credentials.json not found. Put your downloaded OAuth Desktop JSON beside this script and rename it credentials.json.")
        return 2

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
    credentials = flow.run_local_server(
        host="localhost",
        port=0,
        authorization_prompt_message="Open this URL in your browser: {url}",
        success_message="YouTube authorization complete. You can close this browser tab.",
        open_browser=True,
    )
    TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")
    encoded = base64.b64encode(TOKEN_FILE.read_bytes()).decode("ascii")
    B64_FILE.write_text(encoded + "\n", encoding="ascii")
    print("\nSUCCESS: token.json created.")
    print("SUCCESS: token_b64.txt created.")
    print("Next: copy the complete one-line contents of token_b64.txt into GitHub Actions secret YT_TOKEN_JSON_B64.")
    print("Do not paste the token or Base64 value into chat or commit these files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
