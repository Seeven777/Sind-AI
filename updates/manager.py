import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import re


class UpdateManager:
    """Verifica GitHub sem bloquear a UI e delega a instalação a um helper externo."""

    def __init__(self, base_dir, config):
        self.base_dir = Path(base_dir).resolve()
        self.config = config
        self.repository = config.get("update_repository", "Seeven777/Sind-AI")
        self.branch = config.get("update_branch", "main")
        self.channel = config.get("update_channel", "main")
        self.auto_check = bool(config.get("update_auto_check", True))
        self.interval = int(config.get("update_check_interval_seconds", 14400))
        self.install_mode = config.get("update_install_mode", "prompt")

        custom_state_root = config.get("update_state_root")
        self.persistent_root = Path(custom_state_root).expanduser() if custom_state_root else (Path.home() / config.get("persistent_root_name", "JarvisData"))
        self.state_dir = self.persistent_root / "updates"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.install_meta_path = self.base_dir / ".jarvis_install.json"
        self.state_path = self.state_dir / "state.json"
        self._lock = threading.RLock()
        self._checking = False

        self._state = {
            "ok": True,
            "checking": False,
            "available": False,
            "channel": self.channel,
            "branch": self.branch,
            "repository": self.repository,
            "current_version": str(config.get("release_version", "")),
            "current_sha": "",
            "remote_version": "",
            "remote_sha": "",
            "remote_date": "",
            "remote_message": "",
            "last_checked_at": "",
            "error": "",
        }
        self._load_local_metadata()
        self._load_cached_state()
        self.channel = str(self._state.get("channel") or self.channel)
        self.branch = str(self._state.get("branch") or self.branch)

    def _now(self):
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _load_json(self, path):
        try:
            return json.loads(Path(path).read_text(encoding="utf-8-sig"))
        except Exception:
            return {}

    def _load_local_metadata(self):
        meta = self._load_json(self.install_meta_path)
        self._state["current_sha"] = str(meta.get("sha") or "")
        self._state["current_version"] = str(
            meta.get("version")
            or self.config.get("release_version")
            or ""
        )
        self._state["channel"] = str(meta.get("channel") or self.channel)
        self._state["branch"] = str(meta.get("branch") or self.branch)

    def _load_cached_state(self):
        cached = self._load_json(self.state_path)
        if not cached:
            return
        with self._lock:
            for key in (
                "channel","branch","remote_version","remote_sha","remote_date","remote_message",
                "last_checked_at","available","error"
            ):
                if key in cached:
                    self._state[key] = cached[key]

    def _save_state(self):
        data = self.status()
        data.pop("checking", None)
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.state_path)

    def status(self):
        with self._lock:
            data = dict(self._state)
            data["checking"] = self._checking
            return data

    def _github_headers(self):
        return {
            "Accept": "application/vnd.github+json",
            "User-Agent": "SindAI-Jarvis-Updater/1.6",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _fetch_main(self):
        url = f"https://api.github.com/repos/{self.repository}/commits/{self.branch}"
        r = requests.get(url, headers=self._github_headers(), timeout=10)
        r.raise_for_status()
        data = r.json()
        commit = data.get("commit") or {}
        author = commit.get("author") or {}
        return {
            "sha": str(data.get("sha") or ""),
            "version": "",
            "date": str(author.get("date") or ""),
            "message": str(commit.get("message") or "").splitlines()[0][:220],
            "download_url": f"https://github.com/{self.repository}/archive/refs/heads/{self.branch}.zip",
        }

    def _fetch_stable(self):
        url = f"https://api.github.com/repos/{self.repository}/releases/latest"
        r = requests.get(url, headers=self._github_headers(), timeout=10)
        r.raise_for_status()
        data = r.json()
        tag = str(data.get("tag_name") or "")
        version = tag.lstrip("vV")
        return {
            "sha": "",
            "version": version,
            "date": str(data.get("published_at") or ""),
            "message": str(data.get("name") or tag or "Release estável"),
            "download_url": str(data.get("zipball_url") or ""),
        }

    def _version_tuple(self, value):
        nums = [int(piece) for piece in re.findall(r"\d+", str(value))[:4]]
        if not nums:
            nums = [0]
        while len(nums) < 4:
            nums.append(0)
        return tuple(nums[:4])

    def check(self, force=True):
        with self._lock:
            if self._checking:
                return self.status()
            self._checking = True
            self._state["error"] = ""

        try:
            remote = self._fetch_stable() if self.channel == "stable" else self._fetch_main()
            current_sha = self._state.get("current_sha") or ""
            current_version = self._state.get("current_version") or ""

            if self.channel == "stable":
                available = bool(remote["version"]) and self._version_tuple(remote["version"]) > self._version_tuple(current_version)
            else:
                # Existing installs upgraded to 1.3 receive metadata from the installer.
                # If metadata is missing, show an update once so the install can be normalized.
                available = bool(remote["sha"]) and (not current_sha or remote["sha"] != current_sha)

            with self._lock:
                self._state.update({
                    "ok": True,
                    "available": bool(available),
                    "remote_version": remote["version"],
                    "remote_sha": remote["sha"],
                    "remote_date": remote["date"],
                    "remote_message": remote["message"],
                    "download_url": remote["download_url"],
                    "last_checked_at": self._now(),
                    "error": "",
                })
            self._save_state()
        except Exception as exc:
            with self._lock:
                self._state["ok"] = False
                self._state["error"] = str(exc)
                self._state["last_checked_at"] = self._now()
            self._save_state()
        finally:
            with self._lock:
                self._checking = False
        return self.status()

    def check_async(self, force=False):
        if not self.auto_check and not force:
            return self.status()
        with self._lock:
            if self._checking:
                return self.status()
            last = self._state.get("last_checked_at") or ""
            if not force and last:
                try:
                    ts = datetime.fromisoformat(last.replace("Z", "+00:00")).timestamp()
                    if time.time() - ts < self.interval:
                        return self.status()
                except Exception:
                    pass

        thread = threading.Thread(target=self.check, kwargs={"force": True}, daemon=True)
        thread.start()
        return self.status()

    def set_channel(self, channel):
        channel = str(channel or "").lower().strip()
        if channel not in {"main", "stable"}:
            return {"ok": False, "error": "Canal inválido."}
        self.channel = channel
        self._state["channel"] = channel
        self._state["available"] = False
        self._state["error"] = ""
        self._save_state()
        self.check_async(force=True)
        return {"ok": True, "channel": channel}

    def launch_update(self):
        status = self.status()
        if not status.get("available"):
            return {"ok": False, "error": "Nenhuma atualização disponível."}

        helper = self.base_dir / "updates" / "Update-Jarvis.ps1"
        if not helper.exists():
            return {"ok": False, "error": "Helper de atualização não encontrado."}

        temp_dir = Path(tempfile.mkdtemp(prefix="JarvisUpdater_"))
        helper_copy = temp_dir / "Update-Jarvis.ps1"
        shutil.copy2(helper, helper_copy)

        log_path = self.state_dir / "last_update.log"
        args = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", str(helper_copy),
            "-InstallDir", str(self.base_dir),
            "-Repository", self.repository,
            "-Channel", self.channel,
            "-Branch", self.branch,
            "-CurrentPid", str(os.getpid()),
            "-LogPath", str(log_path),
        ]
        try:
            flags = 0
            if os.name == "nt":
                flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            subprocess.Popen(
                args,
                cwd=str(temp_dir),
                creationflags=flags,
                close_fds=True,
            )
            return {"ok": True, "started": True, "message": "Atualizador iniciado. O Jarvis será fechado e reiniciado."}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
