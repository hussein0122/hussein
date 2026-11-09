"""Conservative YouTube comment replies. Requires a separately authorized token."""
from __future__ import annotations
import json, os, re, sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB = Path(os.getenv("COMMENT_DB", "data/comment_replies.sqlite3"))
SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"

def service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    token_path = Path(os.getenv("YT_COMMENTS_TOKEN_FILE", "comment_token.json"))
    if not token_path.exists():
        raise RuntimeError("Missing separately authorized comment_token.json")
    creds = Credentials.from_authorized_user_file(str(token_path), [SCOPE])
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json(), encoding="utf-8")
        try: token_path.chmod(0o600)
        except OSError: pass
    if not creds.valid or not creds.has_scopes([SCOPE]):
        raise RuntimeError("Comment token is invalid or lacks youtube.force-ssl scope")
    return build("youtube", "v3", credentials=creds, cache_discovery=False)

def safe_reply(text: str) -> str | None:
    clean = re.sub(r"\s+", " ", text).strip()
    low = clean.lower()
    if not clean or len(clean) > 1000: return None
    if re.search(r"https?://|www\.|t\.me/|bit\.ly/", low): return None
    if len(re.findall(r"(.)\1{5,}", low)) or len(re.findall(r"\b(تابع|اشترك|ربح سريع|كريبتو)\b", low)) >= 3: return None
    if re.search(r"\b(غبي|حمار|كلب|كس|fuck|shit|idiot)\b", low): return None
    if "?" in clean or "؟" in clean:
        return "شكرًا على سؤالك ❤️ هنراجع النقطة ونتأكد من المعلومة قبل ما نرد عليك."
    if re.search(r"\b(شكرا|شكرًا|جميل|رائع|حلو)\b", low):
        return "شكرًا جدًا على دعمك ❤️"
    return "شكرًا على تعليقك ومشاركتك ❤️"

def main() -> int:
    if os.getenv("AUTO_REPLY_ENABLED", "false").lower() not in ("1","true","yes"):
        print("Auto replies disabled; skipping.")
        return 0
    limit = max(1, min(50, int(os.getenv("AUTO_REPLY_DAILY_LIMIT", "20"))))
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB)
    db.execute("CREATE TABLE IF NOT EXISTS replied (comment_id TEXT PRIMARY KEY, replied_at TEXT NOT NULL)")
    today = datetime.now(timezone.utc).date().isoformat()
    sent = db.execute("SELECT COUNT(*) FROM replied WHERE substr(replied_at,1,10)=?", (today,)).fetchone()[0]
    if sent >= limit:
        print("Daily reply limit reached.")
        return 0
    yt = service()
    channel = yt.channels().list(part="id", mine=True).execute()
    items = channel.get("items", [])
    if not items: raise RuntimeError("No authorized YouTube channel found")
    channel_id = items[0]["id"]
    threads = yt.commentThreads().list(part="snippet", allThreadsRelatedToChannelId=channel_id,
                                       order="time", maxResults=100, textFormat="plainText").execute()
    for thread in threads.get("items", []):
        if sent >= limit: break
        top = thread["snippet"]["topLevelComment"]
        cid = top["id"]
        exists = db.execute("SELECT 1 FROM replied WHERE comment_id=?", (cid,)).fetchone()
        if exists: continue
        # Never reply to our own channel's comments.
        if top["snippet"].get("authorChannelId", {}).get("value") == channel_id: continue
        reply = safe_reply(top["snippet"].get("textDisplay", ""))
        if not reply: continue
        yt.comments().insert(part="snippet", body={"snippet":{"parentId":cid,"textOriginal":reply}}).execute()
        db.execute("INSERT OR IGNORE INTO replied VALUES (?,?)", (cid, datetime.now(timezone.utc).isoformat()))
        db.commit(); sent += 1
    print(f"Replies sent in this run: {sent}")
    db.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
