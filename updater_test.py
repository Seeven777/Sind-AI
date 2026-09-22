import json
import tempfile
from pathlib import Path

from updates.manager import UpdateManager


def check(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    print("[OK]", name)


def main():
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        (base / "updates").mkdir()
        (base / "updates" / "Update-Jarvis.ps1").write_text("Write-Host test", encoding="utf-8")
        (base / ".jarvis_install.json").write_text(
            json.dumps({
                "repository": "Seeven777/Sind-AI",
                "channel": "main",
                "branch": "main",
                "sha": "abc123",
                "version": "1.3",
            }),
            encoding="utf-8",
        )

        cfg = {
            "release_version": "1.3",
            "persistent_root_name": "JarvisUpdaterTestData",
            "update_state_root": str(base / "persistent"),
            "update_repository": "Seeven777/Sind-AI",
            "update_channel": "main",
            "update_branch": "main",
            "update_auto_check": False,
            "update_check_interval_seconds": 3600,
        }

        manager = UpdateManager(base, cfg)

        manager._fetch_main = lambda: {
            "sha": "abc123",
            "version": "",
            "date": "2026-09-22T00:00:00Z",
            "message": "same",
            "download_url": "https://example.invalid/same.zip",
        }
        state = manager.check()
        check("Main unchanged", state["available"] is False, state)

        manager._fetch_main = lambda: {
            "sha": "def456",
            "version": "",
            "date": "2026-09-22T01:00:00Z",
            "message": "new commit",
            "download_url": "https://example.invalid/new.zip",
        }
        state = manager.check()
        check("Main detects new commit", state["available"] is True, state)
        check("Remote SHA stored", state["remote_sha"] == "def456", state)

        manager.check_async = lambda force=False: manager.status()
        result = manager.set_channel("stable")
        check("Switch to stable", result["ok"] and manager.channel == "stable", result)
        manager._checking = False
        manager._fetch_stable = lambda: {
            "sha": "",
            "version": "1.4.0",
            "date": "2026-09-22T02:00:00Z",
            "message": "Jarvis 1.4.0",
            "download_url": "https://example.invalid/stable.zip",
        }
        state = manager.check()
        check("Stable detects higher version", state["available"] is True, state)
        check("Stable version parsed", state["remote_version"] == "1.4.0", state)

        manager._fetch_stable = lambda: {
            "sha": "",
            "version": "1.3.0",
            "date": "2026-09-22T02:00:00Z",
            "message": "Jarvis 1.3.0",
            "download_url": "https://example.invalid/stable.zip",
        }
        state = manager.check()
        check("Stable ignores same version", state["available"] is False, state)

        check("Helper exists", (base / "updates" / "Update-Jarvis.ps1").exists())

        print("\nAuto Updater test concluído.")


if __name__ == "__main__":
    main()
