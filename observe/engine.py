import json
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from observe.activity_store import ActivityStore
from observe.context import foreground_snapshot
from observe.patterns import detect_activity_patterns


class ObservationEngine:
    """Observe & Learn engine.

    Backward compatibility:
    - start()/stop()/summary()/build_candidate() preserve the 1.9 explicit
      demonstration flow;
    - typed printable text remains masked;
    - existing mouse/UIA skill compilation remains unchanged in principle.

    Phase 1 additions:
    - opt-in passive context observation (active application/window changes);
    - persistent SQLite activity ledger;
    - current desktop context and recent-activity queries;
    - basic repeated-context pattern discovery;
    - generic ingest_event() bridge for future Photoshop/VSCode/browser plugins.

    The passive observer DOES NOT record key contents or continuous screenshots.
    It is intentionally cheap enough for the CPU-first reference machine.
    """

    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)
        self.sessions_dir = self.root_dir / "sessions"
        self.candidates_dir = self.root_dir / "candidates"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.candidates_dir.mkdir(parents=True, exist_ok=True)

        # Existing explicit demonstration state.
        self.active = False
        self.session_id = None
        self.events = []
        self._mouse_listener = None
        self._key_listener = None
        self._lock = threading.RLock()
        self._typed_open = False
        self._typed_count = 0

        # New persistent activity/context layer.
        self.activity_store = ActivityStore(self.root_dir / "activity.db")
        self._passive_stop = threading.Event()
        self._passive_thread = None
        self._passive_interval = 2.0
        self._last_passive_fingerprint = None
        self._last_heartbeat = 0.0
        self._heartbeat_seconds = 60.0

        try:
            self.activity_store.prune(
                days=int(self.activity_store.get_setting("retention_days", 45) or 45)
            )
        except Exception:
            pass

        # Passive observation is opt-in. Once enabled by the user it survives
        # restarts, which is required for continuous learning/context awareness.
        if bool(self.activity_store.get_setting("passive_enabled", False)):
            self.start_passive(
                interval_seconds=float(
                    self.activity_store.get_setting("passive_interval_seconds", 2.0) or 2.0
                ),
                persist=False,
            )

    def _now(self):
        return datetime.now().isoformat(timespec="milliseconds")

    def _foreground_window(self):
        snapshot = foreground_snapshot()
        return {
            "handle": snapshot.get("handle"),
            "title": snapshot.get("window_title", ""),
            "pid": snapshot.get("pid", 0),
            "process_name": snapshot.get("process_name", ""),
            "app_id": snapshot.get("app_id", "unknown"),
            "app_label": snapshot.get("app_label", "Aplicativo desconhecido"),
            "document_hint": snapshot.get("document_hint", ""),
        }

    def _control_at(self, x, y):
        try:
            from pywinauto import Desktop

            ctrl = Desktop(backend="uia").from_point(int(x), int(y))
            info = ctrl.element_info
            return {
                "name": (info.name or "").strip(),
                "control_type": (info.control_type or "").strip(),
                "automation_id": (info.automation_id or "").strip(),
            }
        except Exception:
            return {"name": "", "control_type": "", "automation_id": ""}

    # ---------------------------------------------------------------------
    # Existing explicit demonstration recorder
    # ---------------------------------------------------------------------
    def _flush_text(self):
        with self._lock:
            if self._typed_count:
                self.events.append(
                    {
                        "time": self._now(),
                        "type": "text_input",
                        "chars": self._typed_count,
                        "window": self._foreground_window(),
                    }
                )
            self._typed_count = 0
            self._typed_open = False

    def _on_click(self, x, y, button, pressed):
        if not self.active or not pressed:
            return
        self._flush_text()
        event = {
            "time": self._now(),
            "type": "mouse_click",
            "button": str(button).replace("Button.", ""),
            "x": int(x),
            "y": int(y),
            "window": self._foreground_window(),
            "control": self._control_at(x, y),
        }
        with self._lock:
            self.events.append(event)

    def _on_press(self, key):
        if not self.active:
            return

        # Printable characters are counted, never persisted as typed content.
        try:
            char = key.char
        except Exception:
            char = None

        if char and len(char) == 1 and char.isprintable():
            with self._lock:
                self._typed_count += 1
                self._typed_open = True
            return

        self._flush_text()
        name = str(key).replace("Key.", "")
        allowed = {
            "enter",
            "tab",
            "esc",
            "backspace",
            "delete",
            "up",
            "down",
            "left",
            "right",
            "home",
            "end",
            "page_up",
            "page_down",
        }
        if name in allowed:
            with self._lock:
                self.events.append(
                    {
                        "time": self._now(),
                        "type": "key",
                        "key": name,
                        "window": self._foreground_window(),
                    }
                )

    def start(self, label="demonstracao"):
        if self.active:
            return {"ok": False, "error": "Já existe uma observação ativa."}

        try:
            from pynput import keyboard, mouse
        except Exception as exc:
            return {"ok": False, "error": f"pynput não instalado: {exc}"}

        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.events = [
            {
                "time": self._now(),
                "type": "session_start",
                "label": str(label),
                "privacy": "typed_text_masked",
                "window": self._foreground_window(),
            }
        ]
        self.active = True

        self._mouse_listener = mouse.Listener(on_click=self._on_click)
        self._key_listener = keyboard.Listener(on_press=self._on_press)
        self._mouse_listener.start()
        self._key_listener.start()
        return {
            "ok": True,
            "session_id": self.session_id,
            "privacy": "O conteúdo digitado não será gravado.",
        }

    def stop(self):
        if not self.active:
            return {"ok": False, "error": "Não há observação ativa."}

        self._flush_text()
        self.active = False
        for listener in (self._mouse_listener, self._key_listener):
            try:
                if listener:
                    listener.stop()
            except Exception:
                pass

        self._mouse_listener = None
        self._key_listener = None
        with self._lock:
            self.events.append(
                {
                    "time": self._now(),
                    "type": "session_stop",
                    "window": self._foreground_window(),
                }
            )
            payload = {
                "session_id": self.session_id,
                "created_at": self.events[0]["time"],
                "events": list(self.events),
            }

        path = self.sessions_dir / f"{self.session_id}.json"
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        summary = self.summary(self.session_id)
        return {
            "ok": True,
            "session_id": self.session_id,
            "path": str(path),
            "events": len(payload["events"]),
            "summary": summary.get("summary"),
        }

    def status(self):
        return {
            "ok": True,
            "active": self.active,
            "session_id": self.session_id if self.active else None,
            "events": len(self.events) if self.active else 0,
            "privacy": "typed_text_masked",
            "passive": self.passive_status(),
        }

    def list_sessions(self, limit=30):
        items = []
        for path in sorted(self.sessions_dir.glob("*.json"), reverse=True)[: int(limit)]:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                items.append(
                    {
                        "session_id": data.get("session_id", path.stem),
                        "events": len(data.get("events", [])),
                        "created_at": data.get("created_at"),
                        "path": str(path),
                    }
                )
            except Exception:
                continue
        return {"ok": True, "items": items, "count": len(items)}

    def _load_session(self, session_id):
        path = self.sessions_dir / f"{session_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Sessão não encontrada: {session_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def summary(self, session_id):
        try:
            data = self._load_session(session_id)
        except Exception:
            if self.active and session_id == self.session_id:
                data = {"events": list(self.events)}
            else:
                return {"ok": False, "error": "Sessão não encontrada."}

        events = data.get("events", [])
        clicks = [event for event in events if event.get("type") == "mouse_click"]
        texts = [event for event in events if event.get("type") == "text_input"]
        keys = [event for event in events if event.get("type") == "key"]
        app_actions = [event for event in events if event.get("type") == "app_action"]
        windows = []
        apps = []
        for event in events:
            window = event.get("window") or {}
            title = window.get("title")
            app_id = window.get("app_id")
            if title and title not in windows:
                windows.append(title)
            if app_id and app_id not in apps:
                apps.append(app_id)

        return {
            "ok": True,
            "summary": {
                "events": len(events),
                "clicks": len(clicks),
                "text_inputs": len(texts),
                "special_keys": len(keys),
                "structured_app_actions": len(app_actions),
                "windows": windows,
                "apps": apps,
            },
        }

    def build_candidate(self, session_id, name=None):
        try:
            data = self._load_session(session_id)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        events = data.get("events", [])
        steps = []
        inputs = {}
        current_window = None
        input_index = 0

        for event in events:
            event_type = event.get("type")
            window_title = (event.get("window") or {}).get("title")
            if window_title and window_title != current_window:
                current_window = window_title
                steps.append(
                    {"tool": "select_window", "args": {"query": current_window}}
                )

            # Future application bridges can provide a replayable structured step.
            # Example payload: {"replay": {"tool": "photoshop.action", "args": {...}}}
            if event_type == "app_action":
                replay = event.get("replay") or (event.get("payload") or {}).get("replay")
                if isinstance(replay, dict) and replay.get("tool"):
                    steps.append(
                        {
                            "tool": str(replay.get("tool")),
                            "args": dict(replay.get("args") or {}),
                        }
                    )
                continue

            if event_type == "mouse_click":
                ctrl = event.get("control") or {}
                control_name = (ctrl.get("name") or "").strip()
                control_type = (ctrl.get("control_type") or "").strip()
                if control_name:
                    steps.append(
                        {
                            "tool": "click_control",
                            "args": {
                                "name": control_name,
                                "control_type": control_type or None,
                            },
                        }
                    )
                else:
                    steps.append(
                        {
                            "tool": "observation_note",
                            "args": {
                                "note": "Clique sem elemento UIA identificável",
                                "x": event.get("x"),
                                "y": event.get("y"),
                            },
                        }
                    )
            elif event_type == "text_input":
                input_index += 1
                key = f"input_{input_index}"
                inputs[key] = {
                    "required": True,
                    "description": (
                        f"Texto digitado no passo {input_index}; conteúdo original "
                        "foi mascarado por privacidade."
                    ),
                }
                steps.append(
                    {"tool": "type_text", "args": {"text": "{{" + key + "}}"}}
                )
            elif event_type == "key":
                mapping = {"esc": "escape"}
                key = mapping.get(event.get("key"), event.get("key"))
                if key in {
                    "enter",
                    "tab",
                    "escape",
                    "backspace",
                    "delete",
                    "up",
                    "down",
                    "left",
                    "right",
                }:
                    steps.append({"tool": "press_key", "args": {"key": key}})

        # Preserve 1.9 behavior: non-replayable notes are not compiled into a Skill.
        compact = []
        for step in steps:
            if step["tool"] == "observation_note":
                continue
            if compact and step["tool"] == "select_window" and compact[-1] == step:
                continue
            compact.append(step)

        candidate = {
            "version": 2,
            "name": name or f"observed_{session_id}",
            "source_session": session_id,
            "inputs": inputs,
            "steps": compact,
            "status": "candidate",
            "privacy": "typed_text_masked",
            "supports_structured_app_actions": True,
        }
        path = self.candidates_dir / f"{session_id}.json"
        path.write_text(
            json.dumps(candidate, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return {
            "ok": True,
            "candidate": candidate,
            "path": str(path),
            "steps": len(compact),
            "inputs": len(inputs),
        }

    def list_candidates(self, limit=30):
        items = []
        for path in sorted(self.candidates_dir.glob("*.json"), reverse=True)[: int(limit)]:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                items.append(
                    {
                        "name": data.get("name"),
                        "source_session": data.get("source_session"),
                        "steps": len(data.get("steps", [])),
                        "inputs": list((data.get("inputs") or {}).keys()),
                        "path": str(path),
                    }
                )
            except Exception:
                continue
        return {"ok": True, "items": items, "count": len(items)}

    # ---------------------------------------------------------------------
    # Phase 1: passive personal context observer
    # ---------------------------------------------------------------------
    def _record_snapshot(self, snapshot, event_type="window_focus", source="windows"):
        if not snapshot.get("ok"):
            return None
        app_id = snapshot.get("app_id") or "unknown"
        process_name = snapshot.get("process_name") or ""
        window_title = snapshot.get("window_title") or ""
        dedupe_key = "|".join([app_id, process_name.lower(), window_title])
        return self.activity_store.record(
            {
                "ts": self._now(),
                "source": source,
                "event_type": event_type,
                "app_id": app_id,
                "process_name": process_name,
                "window_title": window_title,
                "dedupe_key": dedupe_key,
                "payload": {
                    "app_label": snapshot.get("app_label", ""),
                    "document_hint": snapshot.get("document_hint", ""),
                    "pid": snapshot.get("pid", 0),
                    # Full executable path is deliberately not persisted by default.
                    "platform": snapshot.get("platform", sys.platform),
                },
            }
        )

    def _passive_loop(self):
        while not self._passive_stop.is_set():
            try:
                snapshot = foreground_snapshot()
                fingerprint = "|".join(
                    [
                        str(snapshot.get("app_id") or "unknown"),
                        str(snapshot.get("process_name") or "").lower(),
                        str(snapshot.get("window_title") or ""),
                    ]
                )
                now = time.monotonic()
                if fingerprint != self._last_passive_fingerprint:
                    self._record_snapshot(snapshot, event_type="window_focus")
                    self._last_passive_fingerprint = fingerprint
                    self._last_heartbeat = now
                elif now - self._last_heartbeat >= self._heartbeat_seconds:
                    self._record_snapshot(snapshot, event_type="window_heartbeat")
                    self._last_heartbeat = now
            except Exception:
                # Observation must never take the primary Jarvis runtime down.
                pass
            self._passive_stop.wait(max(0.5, float(self._passive_interval)))

    def start_passive(self, interval_seconds=2.0, persist=True):
        interval = max(0.5, min(float(interval_seconds or 2.0), 30.0))
        if self._passive_thread and self._passive_thread.is_alive():
            return {
                "ok": True,
                "active": True,
                "already_active": True,
                "interval_seconds": self._passive_interval,
                "events": self.activity_store.count(),
            }

        self._passive_interval = interval
        self._passive_stop.clear()
        self._last_passive_fingerprint = None
        self._last_heartbeat = 0.0
        self._passive_thread = threading.Thread(
            target=self._passive_loop,
            name="JarvisPersonalObserver",
            daemon=True,
        )
        self._passive_thread.start()

        if persist:
            self.activity_store.set_setting("passive_enabled", True)
            self.activity_store.set_setting("passive_interval_seconds", interval)

        return {
            "ok": True,
            "active": True,
            "interval_seconds": interval,
            "events": self.activity_store.count(),
            "privacy": (
                "Registra trocas de aplicativo/janela e contexto estrutural; "
                "não grava conteúdo digitado nem screenshots contínuos."
            ),
        }

    def stop_passive(self, persist=True):
        was_active = bool(self._passive_thread and self._passive_thread.is_alive())
        self._passive_stop.set()
        thread = self._passive_thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=max(1.0, self._passive_interval + 0.5))
        self._passive_thread = None
        if persist:
            self.activity_store.set_setting("passive_enabled", False)
        return {
            "ok": True,
            "active": False,
            "was_active": was_active,
            "events": self.activity_store.count(),
        }

    def passive_status(self):
        active = bool(self._passive_thread and self._passive_thread.is_alive())
        return {
            "ok": True,
            "active": active,
            "interval_seconds": self._passive_interval,
            "events": self.activity_store.count(),
            "persistent": bool(self.activity_store.get_setting("passive_enabled", False)),
            "privacy": "window_context_only",
        }

    def current_context(self, record=False):
        snapshot = foreground_snapshot()
        if record and snapshot.get("ok"):
            self._record_snapshot(snapshot, event_type="context_query", source="jarvis")
        return snapshot

    def recent_activity(self, minutes=30, limit=100):
        items = self.activity_store.recent(minutes=minutes, limit=limit)
        # Oldest first is easier for the agent/user to reason about as a timeline.
        items.reverse()
        return {
            "ok": True,
            "minutes": max(1, int(minutes)),
            "items": items,
            "count": len(items),
        }

    def activity_summary(self, minutes=60):
        result = self.activity_store.summary(minutes=minutes)
        latest = self.activity_store.latest()
        result["latest"] = latest
        return result

    def activity_patterns(self, minutes=480, min_count=2, limit=12):
        events = self.activity_store.recent(minutes=minutes, limit=2000)
        events.reverse()
        result = detect_activity_patterns(
            events,
            min_count=min_count,
            max_pattern=4,
            limit=limit,
        )
        result["minutes"] = max(1, int(minutes))
        return result

    def ingest_event(
        self,
        source,
        event_type,
        payload=None,
        app_id=None,
        process_name=None,
        window_title=None,
        replay=None,
    ):
        """Accept a structured event from an application bridge.

        This is the stable seam for future Photoshop UXP, VSCode extension and
        browser-extension bridges. `replay` is optional; when an explicit teaching
        session is active, replayable events are also attached to that demonstration
        so build_candidate() can compile them directly into a Skill.
        """
        payload = dict(payload or {})
        context = foreground_snapshot()
        resolved_app = app_id or context.get("app_id") or "unknown"
        resolved_process = process_name or context.get("process_name") or ""
        resolved_title = window_title or context.get("window_title") or ""
        if replay:
            payload["replay"] = dict(replay)

        event_id = self.activity_store.record(
            {
                "ts": self._now(),
                "source": str(source or "app_bridge"),
                "event_type": str(event_type or "app_event"),
                "app_id": str(resolved_app),
                "process_name": str(resolved_process),
                "window_title": str(resolved_title),
                "session_id": str(self.session_id or "") if self.active else "",
                "payload": payload,
            }
        )

        if self.active and replay:
            with self._lock:
                self.events.append(
                    {
                        "time": self._now(),
                        "type": "app_action",
                        "source": str(source or "app_bridge"),
                        "payload": payload,
                        "replay": dict(replay),
                        "window": self._foreground_window(),
                    }
                )

        return {
            "ok": True,
            "event_id": event_id,
            "app_id": resolved_app,
            "attached_to_demonstration": bool(self.active and replay),
        }
