"""Deterministic documentary Shorts renderer: no LLM calls, only curated scripts + sourced stock footage."""
from __future__ import annotations
import asyncio, json, os, random, subprocess, sys, time
from pathlib import Path
import requests
import edge_tts
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "documentary_output"
LIBRARY = DATA / "documentary_topics.json"
STATE = DATA / "documentary_queue.json"
PIXABAY = "https://pixabay.com/api/videos/"
VOICE = os.getenv("DOCUMENTARY_VOICE", "ar-EG-ShakirNeural")
FONT = "Noto Sans Arabic"

def run(*args):
    subprocess.run([str(x) for x in args], check=True)

def choose_topic(topics):
    requested = os.getenv("DOCUMENTARY_TOPIC_ID", "").strip()
    if requested:
        for topic in topics:
            if topic["id"] == requested:
                return topic
        raise RuntimeError(f"Unknown DOCUMENTARY_TOPIC_ID: {requested}")
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"completed":[]}
    completed = set(state.get("completed", []))
    for topic in topics:
        if topic["id"] not in completed:
            return topic
    raise RuntimeError("All curated topics have been used. Add more reviewed scripts before repeating topics.")

def find_video(query, key, required_terms=None):
    response = requests.get(PIXABAY, params={"key":key,"q":query,"per_page":50,"safesearch":"true"}, timeout=45)
    response.raise_for_status()
    hits = response.json().get("hits", [])
    stop = {"in","the","and","with","close","up","face","body","moving","wild","feeding","behavior","documentary","natural","habitat"}
    terms = [str(x).lower() for x in (required_terms or []) if str(x).strip()]
    if not terms:
        terms = [x.lower() for x in query.replace("-", " ").split() if len(x) >= 4 and x.lower() not in stop]
    terms = list(dict.fromkeys(terms))
    candidates=[]
    for hit in hits:
        haystack = " ".join([str(hit.get("tags","")), str(hit.get("user",""))]).lower()
        normalized = haystack.replace("-", " ").replace("_", " ")
        matched = [term for term in terms if term in normalized]
        if not matched:
            continue
        videos=hit.get("videos") or {}
        for quality in ("large","medium","small","tiny"):
            item=videos.get(quality)
            if item and item.get("url") and item.get("width",0)>0 and item.get("height",0)>0:
                relevance=len(matched)
                resolution=item.get("width",0)*item.get("height",0)
                candidates.append((relevance,resolution,item["url"],hit.get("id"),hit.get("tags","")))
                break
    if not candidates:
        raise RuntimeError(f"No Pixabay clip passed subject relevance check for '{query}'. Required subject terms: {terms}. Refusing unrelated footage.")
    candidates.sort(reverse=True)
    relevance,resolution,url,asset_id,tags=candidates[0]
    print(f"VISUAL_MATCH_OK asset={asset_id} matched_terms={relevance} tags={tags}")
    return url, asset_id

def download(url, target):
    with requests.get(url, stream=True, timeout=(30,180)) as response:
        response.raise_for_status()
        with target.open("wb") as f:
            for chunk in response.iter_content(1024*1024):
                if chunk: f.write(chunk)
    if target.stat().st_size < 100_000:
        raise RuntimeError(f"Downloaded scene asset is unexpectedly small: {target}")

async def tts(text, target):
    await edge_tts.Communicate(text, VOICE, rate="+0%", volume="+0%").save(str(target))

def seconds(path):
    p=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)],capture_output=True,text=True,check=True)
    return max(1.0,float(p.stdout.strip()))

def ass_time(value):
    h=int(value//3600); m=int((value%3600)//60); s=value%60
    return f"{h}:{m:02d}:{s:05.2f}"

def make_ass(path, caption, duration):
    safe=caption.replace("\\","\\\\").replace("{","(").replace("}",")")
    content=f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,{FONT},64,&H00FFFFFF,&H0000FFFF,&H00101010,&H90000000,-1,0,0,0,100,100,0,0,1,4,2,2,70,70,230,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,{ass_time(0)},{ass_time(duration)},Main,,0,0,0,,{safe}
"""
    path.write_text(content,encoding="utf-8")

def render_scene(video, voice, caption, target):
    duration=seconds(voice)+0.65
    ass=target.with_suffix(".ass")
    make_ass(ass,caption,duration)
    vf=f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,eq=contrast=1.06:saturation=1.12:gamma=0.98,subtitles={ass.as_posix()}"
    run("ffmpeg","-y","-stream_loop","-1","-i",video,"-i",voice,"-t",f"{duration:.2f}","-vf",vf,"-map","0:v:0","-map","1:a:0","-af","loudnorm=I=-16:TP=-1.5:LRA=11","-c:v","libx264","-preset","veryfast","-crf","20","-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart",target)
    return duration

def upload(path, topic):
    scopes=["https://www.googleapis.com/auth/youtube.upload","https://www.googleapis.com/auth/youtube.readonly"]
    creds=Credentials(token=None,refresh_token=os.environ["YT_REFRESH_TOKEN"].strip(),token_uri="https://oauth2.googleapis.com/token",client_id=os.environ["YT_CLIENT_ID"].strip(),client_secret=os.environ["YT_CLIENT_SECRET"].strip(),scopes=scopes)
    creds.refresh(Request())
    yt=build("youtube","v3",credentials=creds,cache_discovery=False)
    title=topic["title"][:95]
    description=topic["description"]+"\n\nفيديو وثائقي تعليمي. لقطات المصادر المرئية من Pixabay، والسيناريو من مكتبة ShortsPilot AR التحريرية.\n\n#shorts #وثائقي #معلومات"
    body={"snippet":{"title":title,"description":description,"categoryId":"27","tags":topic.get("tags",[])[:15]+["shorts","وثائقي"]},"status":{"privacyStatus":os.getenv("YT_PRIVACY","public"),"selfDeclaredMadeForKids":False}}
    media=MediaFileUpload(str(path),mimetype="video/mp4",chunksize=8*1024*1024,resumable=True)
    req=yt.videos().insert(part="snippet,status",body=body,media_body=media)
    result=None
    while result is None:
        _,result=req.next_chunk()
    print("YOUTUBE_VIDEO_ID="+result["id"])
    print("YOUTUBE_URL=https://youtube.com/shorts/"+result["id"])
    return result["id"]

def main():
    required=["PIXABAY_API_KEY","YT_CLIENT_ID","YT_CLIENT_SECRET","YT_REFRESH_TOKEN"]
    missing=[x for x in required if not os.getenv(x,"").strip()]
    if missing: raise RuntimeError("Missing required GitHub Actions secrets: "+", ".join(missing))
    DATA.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
    library=json.loads(LIBRARY.read_text(encoding="utf-8"))
    topics=library.get("topics",[])
    if not topics: raise RuntimeError("Documentary topic library is empty.")
    topic=choose_topic(topics)
    print(f"OFFLINE DOCUMENTARY: {topic['id']} — {topic['title']}")
    print("LLM_DISABLED=true; script, narration and scene plan are pre-authored.")
    clips=[]
    for index,scene in enumerate(topic["scenes"],1):
        print(f"Preparing scene {index}/{len(topic['scenes'])}: {scene['visual']}")
        url,asset_id=find_video(scene["query"],os.environ["PIXABAY_API_KEY"],scene.get("required_terms"))
        raw=OUT/f"{topic['id']}_{index:02d}_source.mp4"
        voice=OUT/f"{topic['id']}_{index:02d}.mp3"
        clip=OUT/f"{topic['id']}_{index:02d}.mp4"
        download(url,raw)
        asyncio.run(tts(scene["narration"],voice))
        render_scene(raw,voice,scene["caption"],clip)
        clips.append(clip)
        print(f"PIXABAY_ASSET_ID={asset_id}")
    concat=OUT/f"{topic['id']}_concat.txt"
    concat.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in clips),encoding="utf-8")
    final=OUT/f"{topic['id']}_documentary_short.mp4"
    run("ffmpeg","-y","-f","concat","-safe","0","-i",concat,"-c","copy","-movflags","+faststart",final)
    duration=seconds(final)
    if duration<15 or duration>180: raise RuntimeError(f"Rendered duration outside Shorts target: {duration:.1f}s")
    print(f"RENDER_OK duration={duration:.1f}s size={final.stat().st_size}")
    video_id=upload(final,topic)
    state=json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"completed":[]}
    state.setdefault("completed",[]).append(topic["id"])
    state["last_video_id"]=video_id
    state["last_title"]=topic["title"]
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")
    print("TOPIC_MARKED_COMPLETE=true")

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print(f"DOCUMENTARY_FAILED: {type(exc).__name__}: {exc}",file=sys.stderr)
        raise
