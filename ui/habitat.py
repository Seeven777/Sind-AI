import json
import threading
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot, QUrl
from PySide6.QtWidgets import QMainWindow, QMessageBox
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView


class AgentWorker(QObject):
    finished = Signal(str, bool)
    status_changed = Signal(str)
    confirmation_requested = Signal(str, str)

    def __init__(self, agent, prompt):
        super().__init__()
        self.agent = agent
        self.prompt = prompt
        self._event = threading.Event()
        self._approved = False

    def _confirm(self, title, message):
        self._approved = False
        self._event.clear()
        self.confirmation_requested.emit(title, message)
        self._event.wait()
        return self._approved

    def resolve_confirmation(self, approved):
        self._approved = bool(approved)
        self._event.set()

    def run(self):
        try:
            result = self.agent.run(
                self.prompt,
                status=self.status_changed.emit,
                confirm_callback=self._confirm,
            )
            self.finished.emit(str(result), True)
        except Exception as exc:
            self.finished.emit(str(exc), False)


class JarvisBridge(QObject):
    commandSubmitted = Signal(str)
    modeRequested = Signal(str)
    windowRequested = Signal(str)
    moveRequested = Signal()
    cancelRequested = Signal()
    newChatRequested = Signal()

    statusChanged = Signal(str, str)
    commandFinished = Signal(str, str, bool)
    snapshotChanged = Signal(str)

    def __init__(self, window):
        super().__init__()
        self.window = window

    @Slot(str)
    def sendCommand(self, prompt):
        self.commandSubmitted.emit(prompt)

    @Slot(str)
    def setMode(self, mode):
        self.modeRequested.emit(mode)

    @Slot(str)
    def windowAction(self, action):
        self.windowRequested.emit(action)

    @Slot()
    def beginMove(self):
        self.moveRequested.emit()

    @Slot()
    def cancelTask(self):
        self.cancelRequested.emit()

    @Slot()
    def newChat(self):
        self.newChatRequested.emit()

    @Slot(int, result=str)
    def openConversation(self, session_id):
        try:
            result = self.window.agent.conversations.set_current(session_id)
            if not result.get("ok"):
                return json.dumps(result, ensure_ascii=False)
            messages = self.window.agent.conversations.recent_messages(limit=200, session_id=session_id)
            return json.dumps({"ok": True, "session_id": session_id, "messages": messages}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(str, result=str)
    def searchPublicSources(self, query):
        try:
            return json.dumps(self.window.agent.public_data.recommend(query, limit=12), ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(str, result=str)
    def searchActions(self, query):
        try:
            return json.dumps(self.window.agent.actions.search(query, limit=30), ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(str, result=str)
    def searchWorkflows(self, query):
        try:
            return json.dumps(self.window.agent.workflows.search(query, limit=30), ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(str, str, result=str)
    def searchKnowledge(self, collection, query):
        try:
            return json.dumps(self.window.agent.knowledge.search(collection, query, limit=12), ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(str, result=str)
    def researchPreview(self, query):
        try:
            result = self.window.agent.research.search(query, limit=8, official_first=True)
            return json.dumps(result, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(result=str)
    def systemHealth(self):
        try:
            return json.dumps(self.window.agent.supervisor.full_health(), ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(int, result=str)
    def taskEvents(self, task_id):
        try:
            return json.dumps(self.window.agent.tasks.events(task_id, limit=200), ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(int, result=str)
    def runAutomation(self, job_id):
        try:
            return json.dumps(self.window.agent.automations.run_now(job_id), ensure_ascii=False, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(int, str, result=str)
    def approvalDecision(self, approval_id, decision):
        try:
            if str(decision).lower() == "approve":
                result = self.window.agent.approvals.approve(approval_id, resolved_by="ui", execute=True)
            else:
                result = self.window.agent.approvals.reject(approval_id, resolved_by="ui")
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(int, result=str)
    def checkMonitor(self, monitor_id):
        try:
            return json.dumps(self.window.agent.monitors.check(monitor_id, force=True), ensure_ascii=False, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(int, result=str)
    def markNotificationRead(self, notification_id):
        try:
            return json.dumps(self.window.agent.notifications.mark_read(notification_id), ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(int, result=str)
    def testConnector(self, connector_id):
        try:
            return json.dumps(self.window.agent.connectors.test(connector_id), ensure_ascii=False, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(result=str)
    def getSnapshot(self):
        return json.dumps(
            self.window.build_snapshot(),
            ensure_ascii=False,
        )


class HabitatWindow(QMainWindow):
    def __init__(self, agent, config, base_dir):
        super().__init__()

        self.agent = agent
        self.config = config
        self.base_dir = Path(base_dir)
        self.mode = "habitat"
        self.thread = None
        self.worker = None
        self.current_prompt = ""

        self.setWindowTitle("Jarvis Habitat")
        self.setMinimumSize(620, 460)
        self.resize(1440, 900)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Window
        )

        self.view = QWebEngineView(self)
        self.setCentralWidget(self.view)

        self.channel = QWebChannel(self.view.page())
        self.bridge = JarvisBridge(self)
        self.channel.registerObject("jarvisBridge", self.bridge)
        self.view.page().setWebChannel(self.channel)

        self.bridge.commandSubmitted.connect(self.execute_command)
        self.bridge.modeRequested.connect(self.set_mode)
        self.bridge.windowRequested.connect(self.window_action)
        self.bridge.moveRequested.connect(self.begin_move)
        self.bridge.cancelRequested.connect(self.cancel_task)
        self.bridge.newChatRequested.connect(self.new_chat)

        html_path = self.base_dir / "ui" / "web" / "index.html"
        self.view.load(QUrl.fromLocalFile(str(html_path)))

    def build_snapshot(self):
        try:
            memories = self.agent.memory.list_memories(limit=80)
        except Exception:
            memories = []

        try:
            aliases = self.agent.memory.list_aliases()
        except Exception:
            aliases = []

        try:
            skills = self.agent.skills.list_skills()
        except Exception:
            skills = []

        return {
            "model": f"{self.config.get('fast_model','qwen3:1.7b')} ↔ {self.config.get('reasoning_model', self.config.get('model','qwen3:4b'))}",
            "context": self.config.get("num_ctx", 4096),
            "workspace": str(self.agent.workspace),
            "persistent_root": str(self.agent.persistent_root),
            "memories": memories,
            "aliases": aliases,
            "skills": skills,
            "system": {
                "mode": "local",
                "execution": "cpu",
            },
            "deep_access": self.agent.deep_access.snapshot(),
            "capabilities": self.agent.capabilities.stats(),
            "active_task": self.agent.tasks.active(),
            "recent_tasks": self.agent.tasks.recent(limit=8),
            "actions": self.agent.actions.stats(),
            "workflows": self.agent.workflows.stats(),
            "browser": self.agent.browser_agent.status(),
            "knowledge": self.agent.knowledge.stats(),
            "knowledge_collections": self.agent.knowledge.list_collections(),
            "institutional": self.agent.institutional.execute("stats"),
            "institutional_knowledge": self.agent.institutional_knowledge.execute("stats"),
            "training": self.agent.training.execute("stats"),
            "content_ops": self.agent.content_ops.execute("stats"),
            "governance": self.agent.governance.execute("stats"),
            "automations": {
                "stats": self.agent.automations.stats(),
                "worker": self.agent.automations.worker_status(),
                "items": self.agent.automations.list(limit=30).get("items", []),
                "upcoming": self.agent.automations.upcoming(hours=24, limit=20).get("items", []),
            },
            "monitors": {
                "stats": self.agent.monitors.stats(),
                "items": self.agent.monitors.list(limit=30).get("items", []),
                "events": self.agent.monitors.events(acknowledged=False, limit=20).get("items", []),
            },
            "approvals": {
                "stats": self.agent.approvals.stats(),
                "pending": self.agent.approvals.pending(limit=30).get("items", []),
            },
            "connectors": {
                "stats": self.agent.connectors.stats(),
                "items": self.agent.connectors.list(limit=30).get("items", []),
            },
            "team": {
                "stats": self.agent.team.stats(),
                "roles": self.agent.team.role_list(status="active", limit=50).get("items", []),
                "users": self.agent.team.user_list(status="active", limit=50).get("items", []),
                "gaps": self.agent.team.gap_list(status="open", limit=20).get("items", []),
            },
            "notifications": {
                "stats": self.agent.notifications.stats(),
                "unread": self.agent.notifications.unread(limit=30).get("items", []),
            },
            "observe": self.agent.observe.status(),
            "wordpress": self.agent.wordpress.list_profiles(),
            "research": {
                "recent": self.agent.research.recent(limit=8),
            },
            "cognitive": {
                "conversations": self.agent.conversations.stats(),
                "sessions": self.agent.conversations.list_sessions(limit=30),
                "learning": self.agent.learning.stats(),
                "semantic": self.agent.semantic.stats(),
                "lessons": self.agent.learning.list_lessons(limit=12).get("items", []),
            },
            "public_data": {
                "stats": self.agent.public_data.stats(),
                "sources": self.agent.public_data.list_sources(limit=50).get("items", []),
                "proposals": self.agent.public_data.proposals(limit=10).get("items", []),
            },
            "health": self.agent.supervisor.quick_health(),
            "diagnostics": {
                "last_error": self.agent.diagnostics.last_error(),
                "recent": self.agent.diagnostics.recent(limit=12),
            },
        }

    def show_and_focus(self):
        if self.mode == "habitat":
            self.showMaximized()
        else:
            self.show()
            self.resize(720, 520)
            screen = self.screen().availableGeometry()
            self.move(
                screen.right() - self.width() - 26,
                screen.bottom() - self.height() - 26,
            )

        self.raise_()
        self.activateWindow()

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show_and_focus()

    @Slot(str)
    def set_mode(self, mode):
        if mode not in {"habitat", "compact"}:
            return

        self.mode = mode

        if mode == "habitat":
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
            self.showMaximized()
        else:
            self.setWindowFlags(
                Qt.FramelessWindowHint |
                Qt.Tool |
                Qt.WindowStaysOnTopHint
            )
            self.show()
            self.resize(720, 520)

            screen = self.screen().availableGeometry()
            self.move(
                screen.right() - self.width() - 26,
                screen.bottom() - self.height() - 26,
            )

        self.raise_()
        self.activateWindow()

    @Slot(str)
    def window_action(self, action):
        if action == "hide":
            self.hide()
        elif action == "minimize":
            self.showMinimized()
        elif action == "habitat":
            self.set_mode("habitat")
        elif action == "compact":
            self.set_mode("compact")

    @Slot()
    def begin_move(self):
        try:
            handle = self.windowHandle()
            if handle:
                handle.startSystemMove()
        except Exception:
            pass

    def _map_status(self, detail):
        d = (detail or "").lower()

        if any(x in d for x in ["consultando", "processando", "interpretando"]):
            return "thinking"

        if any(x in d for x in ["executando", "skill", "atualizando memória", "gerenciando"]):
            return "executing"

        return "thinking"

    def execute_command(self, prompt):
        if self.thread is not None:
            self.bridge.commandFinished.emit(
                prompt,
                "Já existe uma tarefa em execução.",
                False,
            )
            return

        self.current_prompt = prompt
        self.bridge.statusChanged.emit(
            "thinking",
            "Interpretando solicitação",
        )

        self.thread = QThread(self)
        self.worker = AgentWorker(self.agent, prompt)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.status_changed.connect(self._on_status)
        self.worker.confirmation_requested.connect(
            self._confirm_action
        )
        self.worker.finished.connect(self._on_finished)

        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self._cleanup_worker)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def _on_status(self, detail):
        self.bridge.statusChanged.emit(
            self._map_status(detail),
            detail,
        )
        # Mantém o painel direito vivo durante tarefas longas (plano/progresso).
        try:
            self.bridge.snapshotChanged.emit(
                json.dumps(self.build_snapshot(), ensure_ascii=False)
            )
        except Exception:
            pass

    @Slot()
    def new_chat(self):
        try:
            self.agent.new_conversation()
        except Exception:
            try:
                self.agent.history = []
            except Exception:
                pass
        self.current_prompt = ""
        self.bridge.snapshotChanged.emit(
            json.dumps(self.build_snapshot(), ensure_ascii=False)
        )

    @Slot()
    def cancel_task(self):
        if self.thread is None:
            return
        try:
            self.agent.cancel_current()
            self.bridge.statusChanged.emit("error", "Cancelamento solicitado")
        except Exception:
            pass

    def _confirm_action(self, title, message):
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(message)
        box.setIcon(QMessageBox.Warning)
        box.setStandardButtons(
            QMessageBox.Yes | QMessageBox.No
        )
        box.setDefaultButton(QMessageBox.No)

        approved = box.exec() == QMessageBox.Yes

        if self.worker:
            self.worker.resolve_confirmation(approved)

    def _on_finished(self, result, ok):
        self.bridge.commandFinished.emit(
            self.current_prompt,
            result,
            ok,
        )

        self.bridge.snapshotChanged.emit(
            json.dumps(
                self.build_snapshot(),
                ensure_ascii=False,
            )
        )

    def _cleanup_worker(self):
        self.worker = None
        self.thread = None

    def closeEvent(self, event):
        event.ignore()
        self.hide()
