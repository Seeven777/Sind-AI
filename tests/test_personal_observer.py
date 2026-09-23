import json
import tempfile
import time
import unittest
from pathlib import Path

from actions.hub import ActionHub
from observe.activity_store import ActivityStore
from observe.engine import ObservationEngine
from observe.patterns import detect_activity_patterns


class PersonalObserverTests(unittest.TestCase):
    def test_activity_store_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ActivityStore(Path(tmp) / "activity.db")
            event_id = store.record({
                "source": "test",
                "event_type": "window_focus",
                "app_id": "photoshop",
                "process_name": "Photoshop.exe",
                "window_title": "post.psd - Adobe Photoshop",
                "payload": {"document_hint": "post.psd"},
            })
            self.assertGreater(event_id, 0)
            items = store.recent(minutes=5, limit=10)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["app_id"], "photoshop")
            self.assertEqual(items[0]["payload"]["document_hint"], "post.psd")

    def test_pattern_detection(self):
        events = []
        for app in ["vscode", "chrome", "vscode", "chrome", "vscode", "chrome"]:
            events.append({"event_type": "window_focus", "app_id": app})
        result = detect_activity_patterns(events, min_count=2)
        self.assertTrue(result["ok"])
        self.assertTrue(any(x["sequence"] == ["vscode", "chrome"] for x in result["patterns"]))

    def test_observer_context_and_passive_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = ObservationEngine(tmp)
            context = engine.current_context()
            self.assertIn("ok", context)
            started = engine.start_passive(interval_seconds=0.5)
            self.assertTrue(started["ok"])
            time.sleep(0.7)
            status = engine.passive_status()
            self.assertTrue(status["active"])
            stopped = engine.stop_passive()
            self.assertTrue(stopped["ok"])
            self.assertFalse(engine.passive_status()["active"])

    def test_supplemental_action_catalog_is_additive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            actions_dir = root / "actions"
            supplement_dir = actions_dir / "catalog.d"
            supplement_dir.mkdir(parents=True)
            primary = {
                "actions": [{
                    "id": "base.echo",
                    "engine": "dummy",
                    "group": "base",
                    "operation": "echo",
                    "description": "base",
                    "params": {},
                    "risk": "read",
                    "keywords": ["base"],
                }]
            }
            extra = {
                "actions": [{
                    "id": "extra.echo",
                    "engine": "dummy",
                    "group": "extra",
                    "operation": "echo",
                    "description": "extra",
                    "params": {},
                    "risk": "read",
                    "keywords": ["extra"],
                }]
            }
            (actions_dir / "catalog.json").write_text(json.dumps(primary), encoding="utf-8")
            (supplement_dir / "personal.json").write_text(json.dumps(extra), encoding="utf-8")

            class Dummy:
                def echo(self):
                    return {"ok": True}

            hub = ActionHub(actions_dir / "catalog.json", {"dummy": Dummy()})
            self.assertIsNotNone(hub.get("base.echo"))
            self.assertIsNotNone(hub.get("extra.echo"))
            self.assertEqual(hub.stats()["actions"], 2)


if __name__ == "__main__":
    unittest.main()
