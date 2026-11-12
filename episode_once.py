"""One-off 5-minute Arabic drama episode generator (never used by the Shorts workflow)."""
from __future__ import annotations
import asyncio, json, os, subprocess, sys, time
from pathlib import Path
from urllib.parse import urlparse
import requests
import edge_tts
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE = os.getenv("AGNES_API_BASE", "https://apihub.agnes-ai.com").rstrip("/")
MODEL = os.getenv("AGNES_VIDEO_MODEL", "agnes-video-2.5-flash")
OUT = Path("episode_output")
DURATION = 10
SCENES = [
("A cinematic wide establishing shot of an Egyptian prison exterior at dawn. Adam, a 32-year-old Egyptian man with short black hair, trimmed beard, athletic build, wearing a faded dark jacket, walks out through the gate alone. Slow tracking camera, realistic live-action drama, consistent character design, 16:9.",
 "الراوي", "خرج آدم من السجن بعد سنوات طويلة، لكنه لم يخرج مهزوماً. كان يخفي حقيقة واحدة: إنه الرجل الذي يخشاه كبار رجال الأعمال."),
("Adam stands alone on a Cairo street, looks at a folded photograph of a little girl, then puts it in his pocket. Traffic and morning light, emotional close-up, cinematic realism.",
 "آدم", "من النهارده، محدش يعرف أنا مين. هبدأ من الصفر، بعيد عن الماضي وعن كل اللي كنت أملكه."),
("Inside a modest office, Rayan, a 35-year-old Egyptian man in a charcoal suit, discreetly approaches Adam. They speak privately beside a parked black car.",
 "ريان", "سيدي، رجوعك هيقلب موازين البلد. إمبراطوريتك مستنياك، وكل رجالتك مستعدين."),
("Adam calmly raises a hand to stop Rayan. Close-up, restrained emotion, city reflections on glass.",
 "آدم", "قلتلك يا ريان، مفيش إمبراطورية دلوقتي. عايز أعيش من غير ما حد يعرف اسمي."),
("Exterior of Safwan Company headquarters, modern glass tower in Cairo. Layan, a confident Egyptian businesswoman in her late twenties, elegant navy suit, enters with purpose.",
 "الراوي", "وفي نفس اليوم، دخل آدم شركة صفوان، الشركة اللي بتديرها ليان، سيدة أعمال قوية بتحارب عشان تحافظ على إرث عيلتها."),
("Adam in simple janitor uniform pushes a cleaning cart through a polished corporate lobby. Employees pass without noticing him.",
 "المدير", "إنت الجديد؟ خلي بالك، هنا مفيش مكان للغلط. شغلتك تنظف وتسكت."),
("Layan notices the manager humiliating Adam and steps in. Medium shot, natural office lighting.",
 "ليان", "كفاية يا أستاذ فؤاد. هو لسه أول يوم ليه، واحنا بنحترم كل الناس هنا."),
("Adam quietly thanks Layan as she walks away. A subtle warm close-up, restrained chemistry.",
 "آدم", "شكراً يا فندم. مش متعود حد يدافع عن عامل النظافة."),
("Layan pauses and turns back, sincere expression.",
 "ليان", "الاحترام مش بالمنصب يا آدم. كل واحد فينا يستاهل يتعامل بكرامة."),
("In a shadowy luxury office, villain Shaw, a wealthy Egyptian businessman in his fifties with silver hair and black suit, studies Safwan Company documents with an accomplice.",
 "شاو", "صفوان لازم تقع قبل نهاية الأسبوع. لو ليان رفضت تبيع، هنخليها تندم."),
("Fouad, the corrupt company manager, secretly hands a USB drive to Shaw in a parking garage.",
 "فؤاد", "كل بيانات الشركة معايا. أول ما أبعتهالك، هتقدر تسيطر على الحسابات."),
("Adam overhears the conversation while cleaning the corridor outside a boardroom. His expression turns serious.",
 "الراوي", "آدم سمع الخطة بالصدفة. كان يقدر ينهي الموضوع بمكالمة واحدة، لكنه قرر يحمي ليان من غير ما يكشف هويته."),
("Adam discreetly uses a phone in a quiet stairwell, speaking to an unseen executive. Dramatic close-up, no visible logos.",
 "آدم", "ريان، جمّد التحويلات المشبوهة فوراً. بس من غير ما حد يعرف إن أنا اللي طلبت."),
("Layan in a tense board meeting sees the fraudulent transfer blocked. Executives look confused; she remains composed.",
 "ليان", "مين وقف التحويل؟ الحسابات كانت هتتسحب في ثواني! لازم أعرف مين أنقذ الشركة."),
("Fouad angrily confronts Adam in a service hallway, pointing at his mop. Adam remains calm.",
 "فؤاد", "إنت مالك ومال اللي بيحصل؟ خليك في شغلك بدل ما أقطع عيشك."),
("Adam looks directly at Fouad, controlled but firm.",
 "آدم", "أنا بعمل شغلي، بس مش هسكت على ظلم حد ولا على سرقة الشركة."),
("Shaw's men seize Layan outside the company at night and force her into a black SUV. Non-graphic suspense, no weapons shown.",
 "الراوي", "لما فشلت خطته، شاو قرر يخطف ليان ويجبرها تمضي على التنازل عن الشركة."),
("Adam finds Layan's dropped phone near the curb, calls Rayan, and looks toward the road with urgency.",
 "آدم", "ريان، عايز مكان ليان حالاً. والمرادي مش هسيب حد يقرب منها."),
("At an abandoned industrial warehouse, Layan is held in a chair but unharmed. Shaw approaches with a contract.",
 "شاو", "وقّعي يا ليان، وساعتها هتخرجي من هنا سليمة. الشركة بقت ملكي."),
("Adam walks into the warehouse as the doors open behind him. Dramatic silhouette, cinematic backlight, guards turn in surprise.",
 "آدم", "ابعد عنها يا شاو. الليلة دي انتهت، ومش هتلمسها."),
("Shaw laughs dismissively, then recognizes Adam. Tight alternating close-ups.",
 "شاو", "إنت؟ مستحيل! أنا كنت فاكر إنك اختفيت للأبد."),
("Rayan arrives with security officers. Adam stands between Layan and Shaw; the guards lower their hands and step aside.",
 "ريان", "انتهى كل شيء يا شاو. أوامر آدم اتنفذت، وكل الأدلة وصلت للشرطة."),
("Layan looks at Adam in disbelief as he removes his janitor cap. Emotional close-up.",
 "ليان", "آدم... إنت مين بالضبط؟ وليه كل الناس دي بتسمع كلامك؟"),
("Adam reveals his identity with quiet dignity. A dramatic slow push-in, warehouse lights flare softly.",
 "آدم", "أنا آدم صفوان... الرجل اللي كان بيمتلك شركات في العالم كله. بس عمري ما كنت عايز أشتري احترامك."),
("Layan remembers a childhood rescue; a soft flashback-like warm light overlays her expression, then returns to present.",
 "ليان", "إنت نفس الشخص اللي أنقذني وأنا طفلة؟ كنت بدور عليك من سنين!"),
("Adam and Layan stand outside the company at sunrise, city skyline behind them. Hopeful cinematic ending, natural expressions.",
 "آدم", "كنت فاكر إن القوة في الفلوس والنفوذ. لحد ما عرفتك، فهمت إن أغلى حاجة هي إن حد يحبك بصدق."),
("Layan smiles through tears; they walk together toward the sunrise, then a final elegant wide shot of Safwan headquarters.",
 "ليان", "وأنا اخترتك من غير ما أعرف إنك سيد العالم. اخترتك لما كنت مجرد آدم، الإنسان اللي احترم كل الناس."),
("A tasteful wedding celebration in an elegant garden in Cairo, Adam and Layan smiling among family, warm golden lights, cinematic finale.",
 "الراوي", "وهكذا انتهت حكاية الرجل اللي أخفى إمبراطوريته، وبدأ من جديد عامل نظافة. لأن الحب الحقيقي لا يحتاج تاجاً ولا عرشاً."),
("Adam and Layan exchange wedding rings in a close cinematic shot, family applauds softly, warm golden light, elegant Egyptian garden celebration.",
 "ليان", "من النهارده هنكتب حكايتنا سوا، من غير أسرار ولا أقنعة. أهم حاجة إننا فضلنا على حقيقتنا."),
("Final wide aerial shot of Cairo at sunrise, Safwan headquarters in the distance, Adam and Layan walk together into a hopeful future, cinematic end frame.",
 "الراوي", "دي كانت حكاية آدم وليان. حكاية بتفكرنا إن أعظم انتصار مش إنك تحكم العالم، لكن إنك تكسب قلب يستاهلك.")
]
VOICES = {"الراوي":"ar-EG-ShakirNeural","آدم":"ar-EG-ShakirNeural","ريان":"ar-SA-HamedNeural","المدير":"ar-SA-HamedNeural","شاو":"ar-SA-HamedNeural","ليان":"ar-EG-SalmaNeural"}

def ffmpeg(*args):
    exe = os.getenv("FFMPEG", "ffmpeg")
    subprocess.run([exe, *map(str,args)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

def headers():
    key=os.getenv("AGNES_API_KEY","").strip()
    if not key: raise RuntimeError("Missing AGNES_API_KEY GitHub Actions secret.")
    return {"Authorization":f"Bearer {key}","Content-Type":"application/json"}

def create_video(prompt, idx):
    body={"model":MODEL,"prompt":prompt,"mode":"text","seconds":str(DURATION),"size":"720P","aspect_ratio":"16:9","n":1}
    for attempt in range(5):
        r=requests.post(f"{BASE}/v1/videos",headers=headers(),json=body,timeout=120)
        if r.status_code==429:
            time.sleep(min(90,15*(attempt+1))); continue
        r.raise_for_status()
        data=r.json()
        vid=data.get("video_id") or data.get("id") or data.get("task_id")
        if not vid: raise RuntimeError(f"Agnes response for scene {idx} did not include a video id.")
        return str(vid)
    raise RuntimeError(f"Agnes rate limit persisted for scene {idx}; stopped without retrying indefinitely.")

def poll_video(video_id, idx):
    deadline=time.time()+5400
    while time.time()<deadline:
        r=requests.get(f"{BASE}/agnesapi",headers=headers(),params={"video_id":video_id,"model_name":MODEL},timeout=90)
        r.raise_for_status()
        data=r.json()
        status=str(data.get("status","")).lower()
        if status in ("completed","succeeded","success"):
            url=data.get("video_url") or data.get("url")
            if not url and isinstance(data.get("output"),dict): url=data["output"].get("url") or data["output"].get("video_url")
            if not url: raise RuntimeError(f"Scene {idx} completed but no video URL was returned.")
            return url
        if status in ("failed","error"):
            raise RuntimeError(f"Agnes failed scene {idx}: {str(data.get('error','unknown'))[:300]}")
        time.sleep(25)
    raise TimeoutError(f"Scene {idx} timed out waiting for Agnes.")

def download(url, path):
    host=urlparse(url).hostname or ""
    if not host or not url.startswith("https://"): raise RuntimeError("Agnes returned a non-HTTPS media URL.")
    with requests.get(url,stream=True,timeout=(30,300)) as r:
        r.raise_for_status()
        with open(path,"wb") as f:
            for chunk in r.iter_content(1024*1024):
                if chunk: f.write(chunk)

async def make_tts(text, voice, path):
    await edge_tts.Communicate(text,voice,rate="+0%",volume="+0%").save(str(path))

def upload_youtube(path):
    scopes=["https://www.googleapis.com/auth/youtube.upload","https://www.googleapis.com/auth/youtube.readonly","https://www.googleapis.com/auth/yt-analytics.readonly"]
    creds=Credentials(token=None,refresh_token=os.environ["YT_REFRESH_TOKEN"].strip(),token_uri="https://oauth2.googleapis.com/token",client_id=os.environ["YT_CLIENT_ID"].strip(),client_secret=os.environ["YT_CLIENT_SECRET"].strip(),scopes=scopes)
    creds.refresh(Request())
    yt=build("youtube","v3",credentials=creds,cache_discovery=False)
    body={"snippet":{"title":"سيد العالم: عامل النظافة الذي أخفى إمبراطوريته | الحلقة الأولى","description":"حلقة درامية عربية قصيرة. جميع الشخصيات والأحداث خيالية.","categoryId":"22","tags":["دراما","مسلسل عربي","قصة آدم وليان"]},"status":{"privacyStatus":"public","selfDeclaredMadeForKids":False}}
    media=MediaFileUpload(str(path),mimetype="video/mp4",chunksize=8*1024*1024,resumable=True)
    req=yt.videos().insert(part="snippet,status",body=body,media_body=media)
    response=None
    while response is None:
        _,response=req.next_chunk()
    print("YOUTUBE_VIDEO_ID="+response["id"])
    print("YOUTUBE_URL=https://www.youtube.com/watch?v="+response["id"])

def main():
    required=["YT_CLIENT_ID","YT_CLIENT_SECRET","YT_REFRESH_TOKEN","AGNES_API_KEY"]
    missing=[x for x in required if not os.getenv(x,"").strip()]
    if missing: raise RuntimeError("Missing GitHub Actions secrets: "+", ".join(missing))
    # Validate the API key and model access before consuming video-generation quota.
    check=requests.get(f"{BASE}/v1/models",headers=headers(),timeout=60)
    check.raise_for_status()
    print("Agnes API authentication endpoint responded successfully.")
    OUT.mkdir(exist_ok=True)
    if len(SCENES) * DURATION != 300:
        raise RuntimeError(f"Episode plan is {len(SCENES) * DURATION}s, not exactly 300s.")
    # Submit scenes sequentially with a conservative interval for free-tier RPM limits.
    ids=[]
    for i,(prompt,_,_) in enumerate(SCENES,1):
        print(f"Submitting animated scene {i}/{len(SCENES)}...")
        ids.append(create_video(prompt,i))
        if i<len(SCENES): time.sleep(62)
    clips=[]
    for i,vid in enumerate(ids,1):
        print(f"Waiting for animated scene {i}/{len(ids)}...")
        url=poll_video(vid,i)
        p=OUT/f"scene_{i:02d}.mp4"; download(url,p); clips.append(p)
    normalized=[]
    for i,p in enumerate(clips,1):
        q=OUT/f"norm_{i:02d}.mp4"
        ffmpeg("-y","-i",p,"-t",str(DURATION),"-vf","scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps=24,format=yuv420p","-an","-c:v","libx264","-preset","veryfast","-crf","22",q)
        normalized.append(q)
    concat=OUT/"concat.txt"
    concat.write_text("".join(f"file '{p.resolve()}'\n" for p in normalized),encoding="utf-8")
    silent=OUT/"episode_silent.mp4"
    ffmpeg("-y","-f","concat","-safe","0","-i",concat,"-t","300","-c","copy",silent)
    # One Egyptian Arabic voice line per scene; each audio cell is padded/cropped to exactly 10 seconds.
    audio_cells=[]
    for i,(_,speaker,line) in enumerate(SCENES,1):
        voice=VOICES[speaker]
        raw=OUT/f"voice_{i:02d}.mp3"
        asyncio.run(make_tts(line,voice,raw))
        cell=OUT/f"audio_{i:02d}.wav"
        ffmpeg("-y","-i",raw,"-af","apad=pad_dur=10,atrim=0:10","-ar","48000","-ac","2",cell)
        audio_cells.append(cell)
    ac=OUT/"audio_concat.txt"
    ac.write_text("".join(f"file '{p.resolve()}'\n" for p in audio_cells),encoding="utf-8")
    voice_track=OUT/"dialogue.wav"
    ffmpeg("-y","-f","concat","-safe","0","-i",ac,"-t","300","-ar","48000","-ac","2",voice_track)
    # Original, synthetic low-volume cinematic ambience; no third-party music asset.
    final=OUT/"episode_5min.mp4"
    ffmpeg("-y","-i",silent,"-i",voice_track,"-f","lavfi","-i","anoisesrc=color=pink:amplitude=0.015:sample_rate=48000:duration=300","-filter_complex","[1:a]volume=1.0[v];[2:a]lowpass=f=180,volume=0.12[m];[v][m]amix=inputs=2:duration=first:dropout_transition=2[a]","-map","0:v:0","-map","[a]","-t","300","-c:v","copy","-c:a","aac","-b:a","192k","-movflags","+faststart",final)
    probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","json",str(final)],capture_output=True,text=True,check=True)
    seconds=float(json.loads(probe.stdout)["format"]["duration"])
    if abs(seconds-300)>0.8: raise RuntimeError(f"Final duration is {seconds:.2f}s, expected 300s.")
    print(f"Final render verified: {seconds:.2f} seconds, 1280x720.")
    upload_youtube(final)

if __name__=="__main__":
    try: main()
    except Exception as e:
        print(f"EPISODE FAILED: {type(e).__name__}: {e}",file=sys.stderr)
        raise
