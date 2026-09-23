import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from observe.episodes import build_work_episodes
from observe.procedural_memory import ProceduralMemory
from observe.engine import ObservationEngine


class PersonalAutonomyPhase2Tests(unittest.TestCase):
    def test_procedural_memory_round_trip_and_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = ProceduralMemory(Path(tmp) / "procedural.db")
            result = memory.remember_demonstration(
                "Criar publicação SindPetshop",
                source_session="demo1",
                skill_name="Criar publicação SindPetshop",
                app_ids=["photoshop", "chrome"],
                inputs={"title": {"required": True}},
                step_count=12,
            )
            self.assertTrue(result["ok"])
            found = memory.search("publicação photoshop", limit=5)
            self.assertEqual(found["count"], 1)
            self.assertEqual(found["items"][0]["name"], "Criar publicação SindPetshop")
            self.assertIn("photoshop", found["items"][0]["app_ids"])

    def test_procedure_maturity_increases_with_successes(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = ProceduralMemory(Path(tmp) / "procedural.db")
            memory.remember_demonstration("Exportar post", app_ids=["photoshop"], step_count=8)
            for _ in range(5):
                memory.record_outcome("Exportar post", status="success")
            item = memory.get_by_name("Exportar post")
            self.assertIn(item["maturity"], {"trusted", "autonomous"})
            self.assertGreater(item["confidence"], 0.68)

    def test_episode_segmentation(self):
        start = datetime.now() - timedelta(minutes=20)
        def event(offset, app):
            return {
                "ts": (start + timedelta(seconds=offset)).isoformat(timespec="milliseconds"),
                "event_type": "window_focus",
                "app_id": app,
                "source": "test",
                "payload": {"document_hint": f"{app}.file"},
            }
        events = [event(0, "vscode"), event(30, "chrome"), event(60, "vscode"), event(700, "photoshop")]
        result = build_work_episodes(events, gap_seconds=300)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["episodes"][0]["apps"], ["vscode", "chrome", "vscode"])
        self.assertEqual(result["episodes"][1]["apps"], ["photoshop"])

    def test_observer_operational_context_and_expert(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = ObservationEngine(tmp)
            for app in ["photoshop", "photoshop", "chrome", "photoshop"]:
                engine.activity_store.record({
                    "source": "test",
                    "event_type": "window_focus",
                    "app_id": app,
                    "process_name": f"{app}.exe",
                    "window_title": f"{app} work",
                    "payload": {"document_hint": "post.psd" if app == "photoshop" else "docs"},
                })
            engine.remember_procedure(
                "Criar post",
                source_session="s1",
                app_ids=["photoshop"],
                inputs={},
                step_count=9,
            )
            expert = engine.app_expertise("photoshop")
            self.assertEqual(expert["app_id"], "photoshop")
            self.assertGreaterEqual(expert["procedures"], 1)
            self.assertIn(expert["maturity"], {"learned", "practiced"})
            bundle = engine.context_packet(minutes=60)
            self.assertTrue(bundle["ok"])
            self.assertIn("PERSONAL OPERATIONAL CONTEXT", bundle["text"])


    def test_working_context_recovers_last_external_app(self):
        # This tests the ledger primitive used when the foreground is Jarvis.
        with tempfile.TemporaryDirectory() as tmp:
            engine = ObservationEngine(tmp)
            engine.activity_store.record({
                "ts": datetime.now().isoformat(timespec="milliseconds"),
                "source": "windows",
                "event_type": "window_focus",
                "app_id": "photoshop",
                "process_name": "Photoshop.exe",
                "window_title": "post.psd - Adobe Photoshop",
                "payload": {"app_label": "Adobe Photoshop", "document_hint": "post.psd"},
            })
            item = engine.activity_store.latest_excluding_apps({"jarvis", "pythonw", "python"}, minutes=180)
            self.assertEqual(item.get("app_id"), "photoshop")



if __name__ == "__main__":
    unittest.main()
