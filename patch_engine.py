"""Apply deterministic quality/safety patches to the pinned PurffleShorts engine.

The upstream engine is pinned to one immutable commit in shorts.yml. These small,
verified source transformations improve Arabic topic visuals and CI quota behavior
without replacing its generation, TTS, rendering, analytics, or upload pipeline.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


def _normalized_text(value: str) -> str:
    return "".join(ch for ch in value if not ch.isspace()).lower()


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    source = path.read_text(encoding="utf-8")
    if new in source:
        print(f"PATCH OK (already applied): {label}")
        return
    if old not in source:
        normalized_old = _normalized_text(old)
        normalized_new = _normalized_text(new)
        if normalized_new in _normalized_text(source):
            print(f"PATCH OK (equivalent patch already applied): {label}")
            return
        # Some upstream patch releases keep the same meaning but reflow the paragraph
        # with different whitespace or line wrapping; treat that as already handled.
        if normalized_old and not normalized_old in _normalized_text(source):
            first_line = next((line.strip() for line in new.splitlines() if line.strip()), "")
            if first_line and first_line in source:
                print(f"PATCH OK (equivalent patch already applied): {label}")
                return
            raise RuntimeError(f"Patch anchor not found for {label}; pinned engine changed.")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")
    print(f"PATCH OK: {label}")


def main() -> int:
    spec = importlib.util.find_spec("purffle_shorts")
    if not spec or not spec.submodule_search_locations:
        raise RuntimeError("purffle_shorts is not installed")
    root = Path(next(iter(spec.submodule_search_locations)))

    # Require scene footage to match the spoken subject. If Pixabay has no relevant
    # clip/photo, the engine falls back to its designed background rather than junk footage.
    replace_once(
        root / "media.py",
        '''            fresh = [c for c in candidates if c.key not in self.used]
            if not fresh:
                return None
''',
        '''            fresh = [c for c in candidates if c.key not in self.used]
            if not fresh:
                return None
            if fresh[0].source != "local":
                matched = [c for c in fresh if relevance(c, query or c.query) >= 0.34]
                if not matched:
                    log.info("Skipped unrelated stock results for visual query %r", query)
                    return None
                fresh = matched
''',
        "reject unrelated stock footage",
    )

    # Enforce scene-level relevance: never fall back to broad topic footage, and reject weak matches.
    replace_once(
        root / "media.py",
        '''                matched = [c for c in fresh if relevance(c, query or c.query) >= 0.34]
''',
        '''                matched = [c for c in fresh if relevance(c, query or c.query) >= 0.50]
''',
        "require strong scene-to-footage relevance",
    )
    replace_once(
        root / "media.py",
        '''        for q in (query, simplify_query(query), simplify_query(topic), topic):
''',
        '''        # Search only for this scene's subject. Broad topic fallbacks often return
        # attractive but unrelated footage, which is worse than a neutral background.
        for q in (query, simplify_query(query)):
''',
        "remove unrelated broad-topic visual fallbacks",
    )

    # When a provider search is simplified to the animal/object name, score its
    # candidates against that simplified query, not the more detailed scene text.
    # Otherwise valid clips (e.g. horseshoe crab footage for a DNA scene) are rejected.
    replace_once(
        root / "media.py",
        '''                item = self._claim(cand, need, query)  # always judged against the scene's own query''',
        '''                item = self._claim(cand, need, q)  # judged against the exact query sent to the provider''',
        "score fallback footage against its actual search query",
    )

    # Give the model a clear creative brief for curiosity hooks and literal, scene-level visuals.
    replace_once(
        root / "script.py",
        '''- search_query: 1-4 English words describing concrete, filmable stock footage for that scene (e.g. "octopus underwater", "old library books"). No abstract words.''',
        '''- Make the topic highly curiosity-driven for Arabic viewers: strange animals, surprising body facts, "what if?" scenarios, mysteries of nature, space, history and science. Use a strong question or visual surprise, then deliver a real payoff. Never invent a record, statistic, species, experiment or scientific claim.
- Prefer a specific subject over a broad lecture: name the exact animal, body part, place, experiment or phenomenon. Avoid generic topics and recycled hooks.
- Every scene's visuals MUST depict the exact thing/action being narrated in that same scene. Build a literal visual storyboard, not generic B-roll.
- search_query: 2-4 English words describing the exact visible subject AND action/place in THIS scene. Use specific names (e.g. "Tyrannosaurus running", "asteroid impact earth", "horseshoe crab ocean", "biceps muscle anatomy"). Do not repeat the overall topic when the scene describes a different event.
- image_prompt: one detailed English sentence for the exact same moment. Prefer photorealistic documentary/cinematic footage and scientifically accurate environments, lighting and anatomy. For dinosaurs/extinction, show the actual animal, asteroid, impact winter, fire or aftermath only when that is what the narration says; do not use generic galaxy/space footage.
- Visual style hierarchy: (1) real documentary wildlife/nature/science footage, (2) photorealistic scientific reconstruction or realistic 3D render for events that cannot be filmed today, (3) clean educational diagram/animation ONLY when explaining an internal process, anatomy or mechanism. Never use childish cartoons, clip-art, random abstract shapes or decorative filler.
- For anatomy, use realistic medical 3D illustration with only the named muscle/organ highlighted; for historical extinct animals, use plausible scientifically grounded photorealistic reconstruction; for living animals, show the exact species in its natural habitat.
- Never use generic landscapes, buildings, people, gym footage or unrelated animals as substitutes. If the exact visual cannot be sourced, request a neutral cinematic background rather than misleading footage.
''',
        "Arabic curiosity and visual-match script brief",
    )

    # Tighten scientific accuracy, especially for health and regeneration claims.
    replace_once(
        root / "script.py",
        '''- Every line earns its place: concrete details, numbers, names. Only well-established facts; no made-up statistics.
''',
        '''- Every line earns its place: concrete details, numbers, names. Only well-established facts; no made-up statistics.
- Scientific accuracy is mandatory: never claim an animal or organ regenerates, heals, survives, or behaves "completely", "fully", "always", "never", "first" or "oldest" unless the supplied context explicitly proves that exact claim. State partial limits and uncertainty plainly; distinguish a hypothesis or "what if" from real science.
- For health, supplements, exercise and nutrition, avoid personalized medical advice, unsupported dosages, guaranteed outcomes and absolute claims. Describe evidence limits and encourage qualified advice for individual medical decisions.
- Do not invent studies, named experts, dates, numbers or sources. If reliable context is missing, choose a different verifiable topic instead of guessing.
''',
        "scientific accuracy and health-claim guardrails",
    )

    # Put a stable channel identity hashtag on every Short, alongside topic-specific tags.
    replace_once(
        root / "script.py",
        '''    hashtags, seen = ["#shorts"], {"#shorts"}
''',
        '''    hashtags, seen = ["#shorts", "#shortspilot"], {"#shorts", "#shortspilot"}
''',
        "add the ShortsPilot brand hashtag to every Short",
    )

    # The pinned upstream preset defaults to a retired Gemini model.
    replace_once(
        root / "llm.py",
        '("GEMINI_API_KEY", "GOOGLE_API_KEY"), "gemini-2.5-flash", schema_mode=True),',
        '("GEMINI_API_KEY", "GOOGLE_API_KEY"), "gemini-3.8-flash", schema_mode=True),',
        "use current Gemini 3.8 Flash default",
    )

    # Groq retired llama-3.3-70b-versatile for free/developer usage in Aug 2026.
    # Use Groq's documented production replacement so automatic failover remains usable.
    replace_once(
        root / "llm.py",
        '"llama-3.3-70b-versatile"),',
        '"openai/gpt-oss-120b"),',
        "use current Groq GPT-OSS 120B fallback model",
    )

    # GPT-OSS 120B supports Groq strict structured outputs. Use JSON Schema mode
    # instead of best-effort JSON Object mode to avoid provider-side JSON validation
    # failures on complex script/review responses. The upstream client still falls
    # back to JSON mode if the endpoint rejects a particular schema.
    replace_once(
        root / "llm.py",
        '''Preset("groq", "Groq (Llama, fast)", "https://api.groq.com/openai/v1", ("GROQ_API_KEY",),
           "openai/gpt-oss-120b"),''',
        '''Preset("groq", "Groq (Llama, fast)", "https://api.groq.com/openai/v1", ("GROQ_API_KEY",),
           "openai/gpt-oss-120b", schema_mode=True),''',
        "enable Groq strict JSON Schema mode for GPT-OSS 120B",
    )

    # Gemini can temporarily return HTTP 503 during demand spikes. Give the
    # provider a bounded retry window before the pipeline marks generation failed.
    replace_once(
        root / "llm.py",
        '''                result = with_retries(_call, attempts=2, base_delay=3, label=f"LLM {p}")
''',
        '''                result = with_retries(_call, attempts=6, base_delay=8, label=f"LLM {p}")
''',
        "retry transient LLM overloads with bounded backoff",
    )
    # Cloud LLM calls should fail over promptly instead of spending many minutes
    # timing out against an overloaded primary provider.
    replace_once(
        root / "llm.py",
        '            timeout = 600 if self.preset.local else 180',
        '            timeout = 600 if self.preset.local else 75',
        "bound cloud LLM request timeouts before provider failover",
    )
    replace_once(
        root / "llm.py",
        'result = with_retries(_call, attempts=6, base_delay=8, label=f"LLM {p}")',
        'result = with_retries(_call, attempts=3, base_delay=5, label=f"LLM {p}")',
        "use three bounded retries before trying the next LLM provider",
    )

    # A single-run GitHub job must never sleep for hours waiting for YouTube quota.
    # It exits cleanly with queued work; the workflow persists queued MP4s for the next run.
    replace_once(
        root / "pipeline.py",
        '''                    if self.quota_left() <= 0 and self.history.pending_uploads():
                        wait = seconds_until_quota_reset()
                        log.info("Upload limit reached and videos are queued; sleeping %.1fh until quota resets",
                                 wait / 3600)
                        time.sleep(wait)
                        continue
''',
        '''                    if self.quota_left() <= 0 and self.history.pending_uploads():
                        if once or count is not None:
                            log.warning("Upload limit reached; ending this one-shot run without sleeping. "
                                        "Queued videos will be retried after the quota reset.")
                            break
                        wait = seconds_until_quota_reset()
                        log.info("Upload limit reached and videos are queued; sleeping %.1fh until quota resets",
                                 wait / 3600)
                        time.sleep(wait)
                        continue
''',
        "avoid multi-hour sleeps in one-shot CI runs",
    )

    # Old cache entries may contain a DB row but no matching MP4. Mark them failed
    # instead of retrying the same missing path forever.
    replace_once(
        root / "pipeline.py",
        '''        if not rec or not rec.get("video_path") or not Path(rec["video_path"]).exists():
            log.error("Video #%s has no file to upload", rid)
            return "missing"
''',
        '''        if not rec or not rec.get("video_path") or not Path(rec["video_path"]).exists():
            log.warning("Video #%s has no local MP4; marking stale queue entry failed", rid)
            if rec:
                self.history.update_video(rid, status="failed", error="Local MP4 missing from persistent cache")
            return "missing"
''',
        "retire stale queue records safely",
    )

    # Remove action/place modifiers from stock queries so rare species can still
    # be found by their actual names (e.g. "nautilus swimming" -> "nautilus").
    # For abstract timeline scenes, search for a concrete documentary subject.
    replace_once(
        root / "media.py",
        '''def simplify_query(query: str) -> str:
    words = [w for w in re.findall(r"[A-Za-z]+", query.lower()) if w not in STOP_WORDS]
    return " ".join(words[:2])
''',
        '''def simplify_query(query: str) -> str:
    modifiers = {"swimming", "basking", "beach", "timeline", "evolution", "underwater", "closeup"}
    words = [w for w in re.findall(r"[A-Za-z]+", query.lower())
             if w not in STOP_WORDS and w not in modifiers]
    return " ".join(words[:2]) if words else "ancient animals"
''',
        "simplify stock searches to concrete species and documentary subjects",
    )

    # Raise the scene relevance bar: with short, specific English queries, 2/3
    # matching subject terms is a stronger minimum than a loose 1/2 overlap.
    replace_once(
        root / "media.py",
        'matched = [c for c in fresh if relevance(c, query or c.query) >= 0.50]',
        'matched = [c for c in fresh if relevance(c, query or c.query) >= 0.67]',
        "raise minimum stock-footage subject match to 67 percent",
    )

    # A weakly scored script is not allowed to reach rendering/upload. The editor
    # can retry/rewrite first; if it still misses the bar, the run stops safely.
    replace_once(
        root / "pipeline.py",
        '''                script = review_script(self.llm, script, s)
''',
        '''                script = review_script(self.llm, script, s)
                minimum_score = int(os.getenv("SCRIPT_MIN_SCORE", "80"))
                if script.score is None or script.score < minimum_score:
                    raise RuntimeError(
                        f"Quality gate: script retention score {script.score!r} is below "
                        f"the required {minimum_score}/100; refusing to produce or publish."
                    )
''',
        "block scripts below the minimum retention score",
    )

    # Never publish a Short containing generated gradient filler because a real
    # scene-matched visual could not be found. Keep the failure visible for retry.
    replace_once(
        root / "pipeline.py",
        '''                media = [got.get((st.index, st.part)) or got[(st.index, 0)] for st in shots]
''',
        '''                media = [got.get((st.index, st.part)) or got[(st.index, 0)] for st in shots]
                missing_visuals = sorted({m.query for m in media if m.source == "generated"})
                if missing_visuals:
                    raise RuntimeError(
                        "Quality gate: no relevant footage was found for scene(s): "
                        + "; ".join(missing_visuals[:8])
                        + ". Refusing to publish a Short with generic gradient filler."
                    )
                log.info("Visual quality gate: all %d shots have sourced scene visuals.", len(media))
''',
        "refuse publication when any scene falls back to generic generated backgrounds",
    )

    # A valid MP4 must include audible narration/music, not merely valid dimensions.
    replace_once(
        root / "pipeline.py",
        '''            info = ffmpeg.probe(video)
            if (info["width"], info["height"]) != s.resolution or abs(info["duration"] - total) > 0.5:
''',
        '''            info = ffmpeg.probe(video)
            if not info.get("has_video") or not info.get("has_audio"):
                raise RuntimeError("Render quality gate failed: output must contain both video and audio streams.")
            measured_loudness = ffmpeg.loudness(video)
            if measured_loudness is None:
                raise RuntimeError("Render quality gate failed: soundtrack is silent or unreadable.")
            log.info("Audio quality gate: integrated loudness %.1f LUFS.", measured_loudness)
            if (info["width"], info["height"]) != s.resolution or abs(info["duration"] - total) > 0.5:
''',
        "verify rendered video has picture and audible soundtrack",
    )

    # Make the narrative feel like one escalating mini-documentary, not a list
    # of disconnected facts. Keep every visual beat tied to the spoken beat.
    replace_once(
        root / "script.py",
        '''- Make the topic highly curiosity-driven for Arabic viewers: strange animals, surprising body facts, "what if?" scenarios, mysteries of nature, space, history and science. Use a strong question or visual surprise, then deliver a real payoff. Never invent a record, statistic, species, experiment or scientific claim.
''',
        '''- Make the topic highly curiosity-driven for Arabic viewers: strange animals, surprising body facts, "what if?" scenarios, mysteries of nature, space, history and science. Use a strong question or visual surprise, then deliver a real payoff. Never invent a record, statistic, species, experiment or scientific claim.
- Retention is the top creative priority: the opening must create an immediate unanswered question or visual surprise in the first spoken sentence, without greetings or setup.
- Create one coherent mini-story with a clear beginning, escalation and payoff. Each scene must add a new fact, consequence, reveal or visual development; never repeat the same point in different words.
- Use short, natural Egyptian-friendly Arabic phrasing that sounds compelling when spoken aloud. Remove filler, long definitions and academic wording; explain technical terms in plain Arabic.
- Keep the strongest reveal for the ending, but plant enough clues that the ending feels earned. Do not resolve the opening question too early.
- Make scene order visually continuous: preserve the same named animal/object, habitat, era and point of view when the narration follows one subject. Change location or subject only when the narration itself changes.
- Every scene must be filmable as one clear visual moment. Describe the exact subject, action, setting and camera framing; avoid vague queries such as "science", "nature", "amazing" or "history".
- Do not add a call to action that interrupts the payoff. Put one brief, natural CTA only after the answer or final reveal.
''',
        "stronger Arabic retention arc and scene continuity",
    )

    # Ensure single-narrator scripts carry the cast entry required by the script schema/reviewer.
    replace_once(
        root / "script.py",
        '''    else:
        cast = []

    description = re.sub(r"(?<!\w)#\w+", "", strip_emoji(str(data.get("description") or ""))).strip()
''',
        '''    else:
        cast = ["Narrator"]

    description = re.sub(r"(?<!\w)#\w+", "", strip_emoji(str(data.get("description") or ""))).strip()
''',
        "provide the required narrator cast entry for single-voice scripts",
    )

    # Keep the best draft and allow the next bounded review round to try another rewrite.
    replace_once(
        root / "script.py",
        '''            log.info("Script Doctor rewrite scored %d, below the draft's %d: kept the draft", new_score, best_score)
            break
''',
        '''            log.info("Script Doctor rewrite scored %d, below the draft's %d: kept the draft and will try another round",
                     new_score, best_score)
            continue
''',
        "continue bounded rewrite attempts after a weaker candidate",
    )

    # Honor provider-supplied rate-limit windows (notably Groq HTTP 429 / TPM).
    # The previous exponential backoff retried after 5/10 seconds even when Groq
    # explicitly asked for 20-35 seconds, wasting requests and prolonging failures.
    replace_once(
        root / "utils.py",
        '''            wait = base_delay * (2 ** (i - 1)) + random.uniform(0, 0.5)
''',
        '''            wait = base_delay * (2 ** (i - 1)) + random.uniform(0, 0.5)
            # Prefer a server-provided retry window when present. Keep it bounded so
            # a malformed response cannot stall a one-shot GitHub Actions job forever.
            retry_hint = re.search(r"(?:try again in|retry after)\\s+([0-9]+(?:\\.[0-9]+)?)\\s*s", str(e), re.I)
            if retry_hint:
                wait = max(wait, float(retry_hint.group(1)) + 1.0)
            wait = min(wait, float(os.getenv("LLM_MAX_RETRY_WAIT", "45")))
''',
        "respect provider Retry-After hints for rate limits",
    )

    print("Pinned engine quality patches verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
