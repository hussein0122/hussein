"""Offline tests for documentary topic selection and visual-fidelity fallback."""
import json
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
