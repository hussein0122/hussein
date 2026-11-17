"""Offline tests for documentary topic selection and visual-fidelity fallback."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import documentary_engine as engine


class DocumentaryQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_state = engine.STATE
        engine.STATE = Path(self.temp_dir.name) / "documentary_queue.json"
        self.topics = [{"id": name, "title": name, "scenes": []} for name in ("rare", "common", "other")]

    def tearDown(self):
        engine.STATE = self.old_state
        self.temp_dir.cleanup()

    def write_state(self, **values):
        state = {"completed": [], "deferred": []}
        state.update(values)
        engine.STATE.write_text(json.dumps(state), encoding="utf-8")

    def test_deferred_topic_does_not_block_other_topics(self):
        self.write_state(deferred=["rare"])
        self.assertEqual(engine.choose_topic(self.topics)["id"], "common")

    def test_deferred_topics_are_retried_after_other_topics_get_a_turn(self):
        self.write_state(deferred=["rare", "common", "other"])
        selected = engine.choose_topic(self.topics)
        self.assertEqual(selected["id"], "rare")
        self.assertEqual(json.loads(engine.STATE.read_text(encoding="utf-8"))["deferred"], [])

    def test_successful_topic_is_completed_and_removed_from_deferred(self):
        self.write_state(deferred=["rare"])
        engine.mark_topic_completed(self.topics[0], "video123")
        state = json.loads(engine.STATE.read_text(encoding="utf-8"))
        self.assertIn("rare", state["completed"])
        self.assertNotIn("rare", state["deferred"])
        self.assertEqual(state["last_video_id"], "video123")


class DocumentaryTtsTests(unittest.IsolatedAsyncioTestCase):
    async def test_primary_voice_retries_transient_no_audio(self):
        calls = []

        class FakeCommunicate:
            def __init__(self, text, voice, **kwargs):
                self.voice = voice

            async def save(self, path):
                calls.append(self.voice)
                if len(calls) == 1:
                    raise RuntimeError("NoAudioReceived")
                Path(path).write_bytes(b"ID3" + b"x" * 512)

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "voice.mp3"
            with patch.object(
                engine.edge_tts, "Communicate",
                side_effect=lambda *args, **kwargs: FakeCommunicate(*args, **kwargs)
            ), patch.object(engine.asyncio, "sleep", new_callable=AsyncMock):
                selected_voice = await engine.tts("اختبار صوت عربي", target)

            self.assertEqual(selected_voice, engine.VOICE)
            self.assertEqual(calls, [engine.VOICE, engine.VOICE])
            self.assertGreater(target.stat().st_size, 256)

    async def test_fallback_voice_is_used_after_primary_voice_retries(self):
        fallback = "ar-EG-SalmaNeural"
        calls = []

        class FakeCommunicate:
            def __init__(self, text, voice, **kwargs):
                self.voice = voice

            async def save(self, path):
                calls.append(self.voice)
                if self.voice == engine.VOICE:
                    raise RuntimeError("NoAudioReceived")
                Path(path).write_bytes(b"ID3" + b"x" * 512)

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "voice.mp3"
            with patch.dict(os.environ, {"DOCUMENTARY_FALLBACK_VOICE": fallback}), patch.object(
                engine.edge_tts, "Communicate",
                side_effect=lambda *args, **kwargs: FakeCommunicate(*args, **kwargs)
            ), patch.object(engine.asyncio, "sleep", new_callable=AsyncMock):
                selected_voice = await engine.tts("اختبار صوت عربي", target)

            self.assertEqual(selected_voice, fallback)
            self.assertEqual(calls, [engine.VOICE, engine.VOICE, fallback])
            self.assertGreater(target.stat().st_size, 256)


if __name__ == "__main__":
    unittest.main()
