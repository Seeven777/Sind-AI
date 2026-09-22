import json
import threading
import time
from datetime import datetime
from pathlib import Path


class ObservationEngine:
    """
    Recorder explícito de demonstrações.

    Privacidade:
    - não grava o texto digitado;
    - caracteres imprimíveis viram apenas eventos "text_input";
    - tenta associar cliques a elementos UI Automation;
    - só funciona entre start() e stop().
    """

    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)
        self.sessions_dir = self.root_dir / "sessions"
        self.candidates_dir = self.root_dir / "candidates"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.candidates_dir.mkdir(parents=True, exist_ok=True)

        self.active = False
        self.session_id = None
        self.events = []
        self._mouse_listener = None
        self._key_listener = None
        self._lock = threading.Lock()
        self._typed_open = False
        self._typed_count = 0

    def _now(self):
        return datetime.now().isoformat(timespec="milliseconds")

    def _foreground_window(self):
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            n = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            return {"handle": int(hwnd), "title": buf.value.strip()}
        except Exception:
            return {"handle": None, "title": ""}

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

    def _flush_text(self):
        with self._lock:
            if self._typed_count:
                self.events.append({
                    "time": self._now(),
                    "type": "text_input",
                    "chars": self._typed_count,
                    "window": self._foreground_window(),
                })
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

        # Caracteres normais: conta, mas não armazena conteúdo.
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
            "enter","tab","esc","backspace","delete","up","down","left","right",
            "home","end","page_up","page_down"
        }
        if name in allowed:
            with self._lock:
                self.events.append({
                    "time": self._now(),
                    "type": "key",
                    "key": name,
                    "window": self._foreground_window(),
                })

    def start(self, label="demonstracao"):
        if self.active:
            return {"ok": False, "error": "Já existe uma observação ativa."}

        try:
            from pynput import mouse, keyboard
        except Exception as exc:
            return {"ok": False, "error": f"pynput não instalado: {exc}"}

        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.events = [{
            "time": self._now(),
            "type": "session_start",
            "label": str(label),
            "privacy": "typed_text_masked",
        }]
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
            self.events.append({
                "time": self._now(),
                "type": "session_stop",
            })
            payload = {
                "session_id": self.session_id,
                "created_at": self.events[0]["time"],
                "events": list(self.events),
            }

        path = self.sessions_dir / f"{self.session_id}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

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
        }

    def list_sessions(self, limit=30):
        items = []
        for p in sorted(self.sessions_dir.glob("*.json"), reverse=True)[:int(limit)]:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                items.append({
                    "session_id": data.get("session_id", p.stem),
                    "events": len(data.get("events", [])),
                    "created_at": data.get("created_at"),
                    "path": str(p),
                })
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
        clicks = [e for e in events if e.get("type") == "mouse_click"]
        texts = [e for e in events if e.get("type") == "text_input"]
        keys = [e for e in events if e.get("type") == "key"]
        windows = []
        for e in events:
            title = (e.get("window") or {}).get("title")
            if title and title not in windows:
                windows.append(title)

        return {
            "ok": True,
            "summary": {
                "events": len(events),
                "clicks": len(clicks),
                "text_inputs": len(texts),
                "special_keys": len(keys),
                "windows": windows,
            }
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

        for e in events:
            etype = e.get("type")
            window_title = (e.get("window") or {}).get("title")

            if window_title and window_title != current_window:
                current_window = window_title
                steps.append({
                    "tool": "select_window",
                    "args": {"query": current_window},
                })

            if etype == "mouse_click":
                ctrl = e.get("control") or {}
                cname = (ctrl.get("name") or "").strip()
                ctype = (ctrl.get("control_type") or "").strip()
                if cname:
                    steps.append({
                        "tool": "click_control",
                        "args": {
                            "name": cname,
                            "control_type": ctype or None,
                        }
                    })
                else:
                    steps.append({
                        "tool": "observation_note",
                        "args": {
                            "note": "Clique sem elemento UIA identificável",
                            "x": e.get("x"),
                            "y": e.get("y"),
                        }
                    })

            elif etype == "text_input":
                input_index += 1
                key = f"input_{input_index}"
                inputs[key] = {
                    "required": True,
                    "description": f"Texto digitado no passo {input_index}; conteúdo original foi mascarado por privacidade.",
                }
                steps.append({
                    "tool": "type_text",
                    "args": {"text": "{{" + key + "}}"},
                })

            elif etype == "key":
                mapping = {"esc":"escape"}
                key = mapping.get(e.get("key"), e.get("key"))
                if key in {"enter","tab","escape","backspace","delete","up","down","left","right"}:
                    steps.append({
                        "tool": "press_key",
                        "args": {"key": key},
                    })

        # Remove selects repetidos consecutivos e notas que não são executáveis.
        compact = []
        for step in steps:
            if step["tool"] == "observation_note":
                continue
            if compact and step["tool"] == "select_window" and compact[-1] == step:
                continue
            compact.append(step)

        candidate = {
            "version": 1,
            "name": name or f"observed_{session_id}",
            "source_session": session_id,
            "inputs": inputs,
            "steps": compact,
            "status": "candidate",
            "privacy": "typed_text_masked",
        }
        path = self.candidates_dir / f"{session_id}.json"
        path.write_text(json.dumps(candidate, indent=2, ensure_ascii=False), encoding="utf-8")

        return {
            "ok": True,
            "candidate": candidate,
            "path": str(path),
            "steps": len(compact),
            "inputs": len(inputs),
        }

    def list_candidates(self, limit=30):
        items = []
        for p in sorted(self.candidates_dir.glob("*.json"), reverse=True)[:int(limit)]:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                items.append({
                    "name": data.get("name"),
                    "source_session": data.get("source_session"),
                    "steps": len(data.get("steps", [])),
                    "inputs": list((data.get("inputs") or {}).keys()),
                    "path": str(p),
                })
            except Exception:
                continue
        return {"ok": True, "items": items, "count": len(items)}
