from pathlib import Path


def test_all_primary_ui_surfaces_exist():
    root=Path(__file__).resolve().parents[2]/"src"/"jarvis"/"ui"/"hq_web"
    for name in (
        "companion.html","index.html","mission-control.html","projects.html",
        "agents.html","memory.html","system.html",
    ):
        assert (root/name).is_file(), name
