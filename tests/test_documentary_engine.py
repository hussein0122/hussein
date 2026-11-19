"""Offline tests for documentary topic selection and visual-fidelity fallback."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import documentary_engine as engine
from cairo_slot_gate import evaluate_slot


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


    def test_find_video_rejects_non_documentary_subject_matches(self):
        hits = [
            {
                "id": 1,
                "tags": "octopus, santa, cartoon, 3d, sea, ocean, water",
                "videos": {"large": {"url": "https://assets.invalid/santa.mp4", "width": 1920, "height": 1080}},
            },
            {
                "id": 2,
                "tags": "octopus, fair, folk festival, carousel, ride, fairground",
                "videos": {"large": {"url": "https://assets.invalid/fairground.mp4", "width": 1920, "height": 1080}},
            },
            {
                "id": 3,
                "tags": "octopus, underwater, reef, coral, marine life, swimming",
                "videos": {"large": {"url": "https://assets.invalid/relevant.mp4", "width": 1920, "height": 1080}},
            },
        ]

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"hits": hits}

        with patch.object(engine.requests, "get", return_value=FakeResponse()):
            url, asset_id = engine.find_video(
                "octopus underwater reef moving",
                "test-key",
                ["octopus"],
            )

        self.assertEqual(asset_id, 3)
        self.assertIn("relevant.mp4", url)


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
            with patch.object(engine, "ACTIVE_VOICE", engine.VOICE), patch.object(
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
            second_target = Path(directory) / "voice_second_scene.mp3"
            with patch.object(engine, "ACTIVE_VOICE", engine.VOICE), patch.dict(
                os.environ, {"DOCUMENTARY_FALLBACK_VOICE": fallback}
            ), patch.object(
                engine.edge_tts, "Communicate",
                side_effect=lambda *args, **kwargs: FakeCommunicate(*args, **kwargs)
            ), patch.object(engine.asyncio, "sleep", new_callable=AsyncMock):
                selected_voice = await engine.tts("اختبار صوت عربي", target)
                second_scene_voice = await engine.tts("مشهد تاني", second_target)
                self.assertEqual(engine.ACTIVE_VOICE, fallback)

            self.assertEqual(selected_voice, fallback)
            self.assertEqual(second_scene_voice, fallback)
            self.assertEqual(calls, [engine.VOICE, engine.VOICE, fallback, fallback])
            self.assertGreater(target.stat().st_size, 256)
            self.assertGreater(second_target.stat().st_size, 256)


class CairoSlotGateTests(unittest.TestCase):
    def test_winter_crons_map_to_each_cairo_slot(self):
        expected = {
            "5 8 * * *": "10:05",
            "5 14 * * *": "16:05",
            "5 20 * * *": "22:05",
        }
        for cron, slot in expected.items():
            with self.subTest(cron=cron):
                self.assertEqual(evaluate_slot("schedule", cron, 120), (True, slot))

    def test_summer_crons_map_to_each_cairo_slot(self):
        expected = {
            "5 7 * * *": "10:05",
            "5 13 * * *": "16:05",
            "5 19 * * *": "22:05",
        }
        for cron, slot in expected.items():
            with self.subTest(cron=cron):
                self.assertEqual(evaluate_slot("schedule", cron, 180), (True, slot))

    def test_inactive_season_crons_are_skipped(self):
        self.assertEqual(
            evaluate_slot("schedule", "5 7 * * *", 120),
            (False, "inactive-season-or-unknown-cron"),
        )
        self.assertEqual(
            evaluate_slot("schedule", "5 8 * * *", 180),
            (False, "inactive-season-or-unknown-cron"),
        )

    def test_unknown_cron_is_skipped(self):
        self.assertEqual(
            evaluate_slot("schedule", "0 0 * * *", 120),
            (False, "inactive-season-or-unknown-cron"),
        )

    def test_manual_dispatch_is_not_blocked_by_schedule_gate(self):
        self.assertEqual(evaluate_slot("workflow_dispatch", "", 120), (True, "manual"))


if __name__ == "__main__":
    unittest.main()
