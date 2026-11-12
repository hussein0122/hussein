"""Apply deterministic quality/safety patches to the pinned PurffleShorts engine.

The upstream engine is pinned to one immutable commit in shorts.yml. These small,
verified source transformations improve Arabic topic visuals and CI quota behavior
without replacing its generation, TTS, rendering, analytics, or upload pipeline.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    source = path.read_text(encoding="utf-8")
    if new in source:
        print(f"PATCH OK (already applied): {label}")
        return
    if old not in source:
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

    # Give the model a clear creative brief for curiosity hooks and literal, scene-level visuals.
    replace_once(
        root / "script.py",
        '''- search_query: 1-4 English words describing concrete, filmable stock footage for that scene (e.g. "octopus underwater", "old library books"). No abstract words.
- image_prompt: one vivid English sentence for an AI image of that scene, no text or letters in the image.
''',
        '''- Make the topic highly curiosity-driven for Arabic viewers: strange animals, surprising body facts, "what if?" scenarios, mysteries of nature, space, history and science. Use a strong question or surprising fact, then deliver a real payoff. Never invent a record, statistic, species, experiment or scientific claim.
- Prefer a specific subject over a broad lecture: name the exact animal, body part, place, experiment or phenomenon. Avoid generic topics and recycled hooks.
- search_query: 2-4 English words that directly describe the exact visible subject/action in THIS scene. For a named muscle/body part, use its exact anatomy (e.g. "biceps muscle anatomy", "quadriceps anatomy"); for an animal, name the exact species and habitat (e.g. "axolotl underwater", "shoebill bird"); for food, show the exact food. No abstract concepts or unrelated metaphors.
- image_prompt: one vivid English sentence describing the same exact subject. Anatomy scenes should look like accurate educational 3D anatomical illustrations with the named muscle highlighted and surrounding anatomy subdued; animal scenes should show the named species in its natural habitat. No text, labels or letters.
- Never use generic construction, brick-wall, business-meeting or random gym footage as a substitute for a named subject. If the exact visual is unavailable, prefer a neutral designed background over a misleading clip.
''',
        "Arabic curiosity and visual-match script brief",
    )

    # Tighten scientific accuracy, especially for health and regeneration claims.
    replace_once(
        root / "script.py",
        '''- Every line earns its place: concrete details, numbers, names. Only well-established facts; no made-up statistics.
''',
        '''- Every line earns its place: concrete details, numbers, names. Only well-established facts; no made-up statistics.
- Scientific accuracy is mandatory: never claim an animal or organ regenerates, heals, survives, or behaves "completely", "fully", "always", "never", "first" or "oldest" unless the supplied context explicitly proves that exact claim. State partial limits and uncertainty plainly; distinguish a hypothetical "what if" from real science.
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
        '           "llama-3.3-70b-versatile"),',
        '           "openai/gpt-oss-120b"),',
        "use current Groq GPT-OSS 120B fallback model",
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

    print("Pinned engine quality patches verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
