import json
import re
import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot, QUrl, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QMessageBox, QFileDialog, QTabWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel
)
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings



class InstitutionalWebView(QWebEngineView):
    """WebView persistente para ferramentas do SindPetshop-SP dentro do Jarvis."""

    def createWindow(self, _window_type):
        # target=_blank continua dentro da própria aba institucional.
        return self


class ServiceTabController(QObject):
    """
    Ponte thread-safe entre Agent Runtime e QWebEngine.

    O agente roda fora da thread da UI; toda leitura/clique/preenchimento da aba
    embutida é encaminhada para a thread Qt e devolvida de forma síncrona ao worker.
    """
    request = Signal(object)

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.request.connect(self._handle)

    def call(self, service_id, operation="open", payload=None, timeout=30):
        box = {"event": threading.Event(), "result": None}
        req = {
            "service_id": str(service_id),
            "operation": str(operation),
            "payload": dict(payload or {}),
            "box": box,
        }
        self.request.emit(req)
        if not box["event"].wait(max(1, float(timeout))):
            return {
                "ok": False,
                "error": f"A aba institucional não respondeu em {int(timeout)}s.",
                "service": str(service_id),
            }
        return box["result"] or {"ok": False, "error": "Resposta vazia da aba institucional."}

    def _finish(self, req, result):
        req["box"]["result"] = result
        req["box"]["event"].set()

    @Slot(object)
    def _handle(self, req):
        sid = req.get("service_id")
        operation = req.get("operation")
        payload = req.get("payload") or {}
        record = self.window.service_views.get(sid)
        if not record:
            self._finish(req, {"ok": False, "error": f"Aba institucional não encontrada: {sid}"})
            return

        view = record["view"]

        if operation == "open":
            self.window.open_service_tab(sid)
            self._finish(req, {
                "ok": True,
                "service": sid,
                "url": record["url"],
                "embedded": True,
            })
            return

        if operation == "back":
            view.back()
            self._finish(req, {"ok": True, "service": sid})
            return
        if operation == "forward":
            view.forward()
            self._finish(req, {"ok": True, "service": sid})
            return
        if operation == "reload":
            view.reload()
            self._finish(req, {"ok": True, "service": sid})
            return

        self.window.open_service_tab(sid)

        def run_js():
            if operation == "inspect":
                max_chars = max(1000, min(30000, int(payload.get("max_chars", 14000))))
                script = f"""
                (() => {{
                  const body = document.body;
                  const text = (body?.innerText || '').slice(0, {max_chars});
                  const headings = [...document.querySelectorAll('h1,h2,h3,h4')]
                    .slice(0,50).map(e => ({{level:e.tagName,text:(e.innerText||'').trim()}}))
                    .filter(x => x.text);
                  const tables = [...document.querySelectorAll('table')].slice(0,20)
                    .map(t => ({{rows:t.rows?.length||0,preview:(t.innerText||'').trim().slice(0,2200)}}));
                  const inputs = [...document.querySelectorAll('input,textarea,select,[contenteditable=true]')]
                    .slice(0,80).map(e => ({{
                      tag:e.tagName,
                      type:e.getAttribute('type')||'',
                      id:e.id||'',
                      name:e.getAttribute('name')||'',
                      placeholder:e.getAttribute('placeholder')||'',
                      aria:e.getAttribute('aria-label')||''
                    }}));
                  return {{ok:true,url:location.href,title:document.title,text,headings,tables,inputs}};
                }})()
                """
                view.page().runJavaScript(
                    script,
                    lambda data: self._finish(
                        req,
                        data if isinstance(data, dict) else {"ok": False, "error": "Não consegui ler a aba."}
                    )
                )
                return

            if operation == "click":
                target = json.dumps(str(payload.get("text") or ""), ensure_ascii=False)
                script = f"""
                (() => {{
                  const q={target}.trim().toLowerCase();
                  if(!q) return {{ok:false,error:'Texto do elemento é obrigatório.'}};
                  const els=[...document.querySelectorAll('button,a,[role=button],input[type=button],input[type=submit],[onclick]')];
                  const label=e => ((e.innerText||e.value||e.getAttribute('aria-label')||e.title||'').trim().toLowerCase());
                  let el=els.find(e=>label(e)===q) || els.find(e=>label(e).includes(q));
                  if(!el) return {{ok:false,error:'Elemento não encontrado.',query:q}};
                  el.scrollIntoView({{block:'center'}});
                  el.click();
                  return {{ok:true,clicked:label(el),url:location.href}};
                }})()
                """
                view.page().runJavaScript(script, lambda data: self._finish(req, data or {"ok": False}))
                return

            if operation == "fill":
                selector = json.dumps(str(payload.get("selector") or ""), ensure_ascii=False)
                hint = json.dumps(str(payload.get("field") or payload.get("text") or ""), ensure_ascii=False)
                value = json.dumps(str(payload.get("value") or ""), ensure_ascii=False)
                script = f"""
                (() => {{
                  const sel={selector};
                  const hint={hint}.toLowerCase();
                  let el=null;
                  if(sel) {{
                    try {{ el=document.querySelector(sel); }} catch(e) {{}}
                  }}
                  if(!el && hint) {{
                    const fields=[...document.querySelectorAll('input,textarea,select,[contenteditable=true]')];
                    el=fields.find(e => {{
                      const hay=[e.id,e.name,e.getAttribute('placeholder'),e.getAttribute('aria-label')]
                        .filter(Boolean).join(' ').toLowerCase();
                      return hay.includes(hint);
                    }});
                  }}
                  if(!el) return {{ok:false,error:'Campo não encontrado.'}};
                  el.focus();
                  const v={value};
                  if(el.isContentEditable) {{
                    el.textContent=v;
                  }} else {{
                    const proto = el.tagName==='TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
                    const desc = Object.getOwnPropertyDescriptor(proto,'value');
                    if(desc?.set) desc.set.call(el,v); else el.value=v;
                  }}
                  el.dispatchEvent(new Event('input',{{bubbles:true}}));
                  el.dispatchEvent(new Event('change',{{bubbles:true}}));
                  return {{ok:true,field:el.id||el.name||el.getAttribute('placeholder')||el.tagName}};
                }})()
                """
                view.page().runJavaScript(script, lambda data: self._finish(req, data or {"ok": False}))
                return

            self._finish(req, {"ok": False, "error": f"Operação não suportada: {operation}"})

        # Se a aba ainda não terminou o primeiro carregamento, espere por ela.
        if not record.get("loaded"):
            fired = {"done": False}

            def after_load(ok):
                if fired["done"]:
                    return
                fired["done"] = True
                try:
                    view.loadFinished.disconnect(after_load)
                except Exception:
                    pass
                if not ok:
                    self._finish(req, {"ok": False, "error": "A página institucional não terminou de carregar."})
                    return
                record["loaded"] = True
                QTimer.singleShot(350, run_js)

            view.loadFinished.connect(after_load)
            self.window._ensure_service_loaded(sid)
        else:
            run_js()


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
    commandFinished = Signal(str, str, bool, str)
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
    def deleteConversation(self, session_id):
        try:
            payload = self.window.agent.delete_conversation(session_id)
            if payload.get("ok"):
                self.snapshotChanged.emit(
                    json.dumps(self.window.build_snapshot(), ensure_ascii=False, default=str)
                )
            return json.dumps(payload, ensure_ascii=False, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

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
    def searchPlaybooks(self, query):
        try:
            return json.dumps(
                self.window.agent.workplace.search(query, limit=20),
                ensure_ascii=False, default=str
            )
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(str, str, result=str)
    def startPlaybook(self, playbook_id, request):
        try:
            result = self.window.agent.workplace.start_long_horizon(
                playbook_id,
                request=request,
                project_id=self.window.agent.projects.current_id(),
                session_id=self.window.agent.conversations.current_session_id,
                priority=65,
            )
            self.snapshotChanged.emit(
                json.dumps(self.window.build_snapshot(), ensure_ascii=False, default=str)
            )
            return json.dumps(result, ensure_ascii=False, default=str)
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
    def pickAttachments(self):
        try:
            files, _ = QFileDialog.getOpenFileNames(
                self.window,
                "Anexar arquivos ao Jarvis",
                str(Path.home()),
                "Documentos suportados (*.pdf *.docx *.txt *.md *.csv *.json *.log *.html *.htm);;Todos os arquivos (*.*)",
            )
            if not files:
                return json.dumps({"ok": True, "items": [], "count": 0}, ensure_ascii=False)
            result = self.window.agent.attachments.add_files(
                files,
                session_id=self.window.agent.conversations.current_session_id,
                project_id=self.window.agent.projects.current_id(),
            )
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(str, str, result=str)
    def createProject(self, name, description):
        try:
            result = self.window.agent.projects.create(name, description)
            if result.get("ok"):
                pid = result["data"]["id"]
                self.window.agent.projects.link_session(
                    pid, self.window.agent.conversations.current_session_id
                )
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(int, result=str)
    def setCurrentProject(self, project_id):
        try:
            result = self.window.agent.projects.set_current(project_id if project_id > 0 else None)
            if project_id > 0:
                self.window.agent.projects.link_session(
                    project_id, self.window.agent.conversations.current_session_id
                )
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(str, str, result=str)
    def addProjectNote(self, title, body):
        try:
            pid = self.window.agent.projects.current_id()
            if not pid:
                return json.dumps({"ok": False, "error": "Nenhum projeto ativo."}, ensure_ascii=False)
            return json.dumps(
                self.window.agent.projects.add_note(pid, title, body),
                ensure_ascii=False, default=str
            )
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

    @Slot(int, str, result=str)
    def longJobAction(self, job_id, action):
        try:
            engine = self.window.agent.long_horizon
            action = str(action or "").lower()
            if action == "pause":
                result = engine.pause(job_id)
            elif action == "resume":
                result = engine.resume(job_id, force=False)
            elif action == "force_resume":
                result = engine.resume(job_id, force=True)
            elif action == "cancel":
                result = engine.cancel(job_id)
            elif action == "run":
                result = engine.run_now(job_id)
            else:
                result = {"ok": False, "error": f"Ação desconhecida: {action}"}
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(int, result=str)
    def longJobDetails(self, job_id):
        try:
            return json.dumps(
                self.window.agent.long_horizon.get(job_id),
                ensure_ascii=False, default=str
            )
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
    def updateStatus(self):
        try:
            updater = getattr(self.window, "updater", None)
            if not updater:
                return json.dumps({"ok": False, "error": "Updater indisponível."}, ensure_ascii=False)
            return json.dumps(updater.status(), ensure_ascii=False, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(result=str)
    def checkUpdate(self):
        try:
            updater = getattr(self.window, "updater", None)
            if not updater:
                return json.dumps({"ok": False, "error": "Updater indisponível."}, ensure_ascii=False)
            result = updater.check_async(force=True)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(str, result=str)
    def setUpdateChannel(self, channel):
        try:
            updater = getattr(self.window, "updater", None)
            if not updater:
                return json.dumps({"ok": False, "error": "Updater indisponível."}, ensure_ascii=False)
            return json.dumps(updater.set_channel(channel), ensure_ascii=False, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(result=str)
    def installUpdate(self):
        try:
            updater = getattr(self.window, "updater", None)
            if not updater:
                return json.dumps({"ok": False, "error": "Updater indisponível."}, ensure_ascii=False)
            result = updater.launch_update()
            if result.get("ok"):
                from PySide6.QtCore import QTimer
                QTimer.singleShot(700, self.window.request_update_exit)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(result=str)
    def mobileStatus(self):
        try:
            mobile = getattr(self.window, "mobile_companion", None)
            if not mobile:
                return json.dumps({"ok": False, "error": "Mobile Companion indisponível."}, ensure_ascii=False)
            return json.dumps(mobile.status(), ensure_ascii=False, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(result=str)
    def mobileToggle(self):
        try:
            mobile = getattr(self.window, "mobile_companion", None)
            if not mobile:
                return json.dumps({"ok": False, "error": "Mobile Companion indisponível."}, ensure_ascii=False)
            result = mobile.toggle()
            self.snapshotChanged.emit(json.dumps(self.window.build_snapshot(), ensure_ascii=False))
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(result=str)
    def mobileDiagnostics(self):
        try:
            mobile = getattr(self.window, "mobile_companion", None)
            if not mobile:
                return json.dumps({"ok": False, "error": "Mobile Companion indisponível."}, ensure_ascii=False)
            return json.dumps(mobile.diagnostics(), ensure_ascii=False, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(result=str)
    def mobileMakeNetworkPrivate(self):
        try:
            script = self.window.base_dir / "Set-Jarvis-NetworkPrivate.ps1"
            if not script.exists():
                return json.dumps({"ok": False, "error": "Helper de rede não encontrado."}, ensure_ascii=False)
            import subprocess
            subprocess.Popen([
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                f"Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"{script}\"'"
            ], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return json.dumps({"ok": True, "message": "Solicitação administrativa aberta."}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(result=str)
    def mobileEnableFirewall(self):
        try:
            script = self.window.base_dir / "Enable-Jarvis-Mobile.ps1"
            if not script.exists():
                return json.dumps({"ok": False, "error": "Helper do firewall não encontrado."}, ensure_ascii=False)
            import subprocess
            subprocess.Popen([
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                f"Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"{script}\"'"
            ])
            return json.dumps({"ok": True, "message": "Solicitação administrativa aberta."}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @Slot(result=str)
    def mobileResetPin(self):
        try:
            mobile = getattr(self.window, "mobile_companion", None)
            if not mobile:
                return json.dumps({"ok": False, "error": "Mobile Companion indisponível."}, ensure_ascii=False)
            result = mobile.reset_pin()
            self.snapshotChanged.emit(json.dumps(self.window.build_snapshot(), ensure_ascii=False))
            return json.dumps(result, ensure_ascii=False, default=str)
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
        self._task_started_at = 0.0
        self._last_status_detail = ""
        self._heartbeat = QTimer(self)
        self._heartbeat.setInterval(
            max(1000, int(self.config.get("ui_task_heartbeat_seconds", 2)) * 1000)
        )
        self._heartbeat.timeout.connect(self._emit_task_heartbeat)

        self.setWindowTitle("Jarvis Habitat")
        self.setMinimumSize(620, 460)
        self.resize(1440, 900)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Window
        )

        self.tabs = QTabWidget(self)
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(False)
        self.tabs.setTabsClosable(False)
        self.tabs.tabBar().setUsesScrollButtons(True)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 0; background: #06080d; }
            QTabBar::tab {
                background: #090c13; color: #778197; border: 0;
                border-right: 1px solid #171d29; padding: 8px 13px;
                min-width: 76px; font-size: 10px;
            }
            QTabBar::tab:selected {
                background: #111522; color: #f3f4fb;
                border-bottom: 2px solid #7668ff;
            }
            QTabBar::tab:hover { background: #0f131d; color: #cbd0dc; }
        """)
        self.setCentralWidget(self.tabs)

        self.view = QWebEngineView(self.tabs)
        self.tabs.addTab(self.view, "✦ Jarvis")
        self.service_views = {}
        self._institutional_profile = QWebEngineProfile("JarvisInstitutional", self)
        profile_root = (
            Path.home()
            / self.config.get("persistent_root_name", "JarvisData")
            / "browser_profile"
            / "institutional_tabs"
        )
        profile_root.mkdir(parents=True, exist_ok=True)
        self._institutional_profile.setPersistentStoragePath(str(profile_root))
        self._institutional_profile.setCachePath(str(profile_root / "cache"))
        self._institutional_profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )

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

        self._build_service_tabs()
        self.service_controller = ServiceTabController(self)
        self.agent.services.set_tab_adapter(
            opener=lambda sid: self.service_controller.call(sid, "open", timeout=5),
            action=lambda sid, operation, payload: self.service_controller.call(
                sid, operation, payload=payload, timeout=35
            ),
        )

        html_path = self.base_dir / "ui" / "web" / "index.html"
        self.view.load(QUrl.fromLocalFile(str(html_path)))

    def _service_label(self, service):
        labels = {
            "insights_dashboard": "Insights",
            "agenda_sind": "Agenda",
            "facebook": "Facebook",
            "linkedin": "LinkedIn",
            "instagram": "Instagram",
            "tiktok": "TikTok",
            "internal_system": "Sistema",
            "slack": "Slack",
            "website": "Site",
        }
        return labels.get(service.get("id"), service.get("name", service.get("id","Serviço"))[:14])

    def _build_service_tabs(self):
        for service in self.agent.services.list(daily=True).get("items", []):
            sid = service["id"]
            page_widget = QWidget(self.tabs)
            layout = QVBoxLayout(page_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            nav = QWidget(page_widget)
            nav.setFixedHeight(38)
            nav.setStyleSheet("background:#080b11;border-bottom:1px solid #1d2331;")
            nav_layout = QHBoxLayout(nav)
            nav_layout.setContentsMargins(8, 5, 8, 5)
            nav_layout.setSpacing(5)

            view = InstitutionalWebView(page_widget)
            page = QWebEnginePage(self._institutional_profile, view)
            view.setPage(page)
            view.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
            view.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)

            def make_btn(label, tooltip):
                btn = QPushButton(label, nav)
                btn.setToolTip(tooltip)
                btn.setFixedSize(29, 27)
                btn.setStyleSheet(
                    "QPushButton{background:#0e121b;color:#8d96aa;border:1px solid #242b3b;"
                    "border-radius:7px;font-size:11px;}QPushButton:hover{color:white;border-color:#454e69;}"
                )
                return btn

            back = make_btn("←", "Voltar")
            forward = make_btn("→", "Avançar")
            reload_btn = make_btn("↻", "Recarregar")
            home = make_btn("⌂", "Página inicial")
            address = QLineEdit(nav)
            address.setPlaceholderText(service["url"])
            address.setStyleSheet(
                "QLineEdit{background:#0b0f17;color:#aab2c4;border:1px solid #242b3b;"
                "border-radius:7px;padding:5px 9px;font-size:9px;}"
                "QLineEdit:focus{border-color:#554c8d;}"
            )

            nav_layout.addWidget(back)
            nav_layout.addWidget(forward)
            nav_layout.addWidget(reload_btn)
            nav_layout.addWidget(home)
            nav_layout.addWidget(address, 1)

            layout.addWidget(nav)
            layout.addWidget(view, 1)

            record = {
                "service": service,
                "widget": page_widget,
                "view": view,
                "address": address,
                "url": service["url"],
                "loaded": False,
            }
            self.service_views[sid] = record
            self.tabs.addTab(page_widget, self._service_label(service))

            back.clicked.connect(view.back)
            forward.clicked.connect(view.forward)
            reload_btn.clicked.connect(view.reload)
            home.clicked.connect(lambda _=False, service_id=sid: self._navigate_service_home(service_id))
            address.returnPressed.connect(
                lambda service_id=sid: self._navigate_service_address(service_id)
            )
            view.urlChanged.connect(
                lambda url, service_id=sid: self._service_url_changed(service_id, url)
            )
            view.loadFinished.connect(
                lambda ok, service_id=sid: self._service_load_finished(service_id, ok)
            )

        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _service_url_changed(self, service_id, url):
        record = self.service_views.get(service_id)
        if record:
            record["address"].setText(url.toString())

    def _service_load_finished(self, service_id, ok):
        record = self.service_views.get(service_id)
        if record and ok:
            record["loaded"] = True

    def _navigate_service_home(self, service_id):
        record = self.service_views.get(service_id)
        if not record:
            return
        record["view"].setUrl(QUrl(record["url"]))

    def _navigate_service_address(self, service_id):
        record = self.service_views.get(service_id)
        if not record:
            return
        raw = record["address"].text().strip()
        if raw and not re.match(r"^https?://", raw, re.I):
            raw = "https://" + raw
        if raw:
            record["view"].setUrl(QUrl(raw))

    def _on_tab_changed(self, index):
        widget = self.tabs.widget(index)
        for sid, record in self.service_views.items():
            if record["widget"] is widget:
                self._ensure_service_loaded(sid)
                return

    def _ensure_service_loaded(self, service_id):
        record = self.service_views.get(service_id)
        if not record:
            return
        current = record["view"].url().toString()
        if not current or current == "about:blank":
            record["view"].setUrl(QUrl(record["url"]))

    @Slot(str)
    def open_service_tab(self, service_id):
        record = self.service_views.get(str(service_id))
        if not record:
            return
        self._ensure_service_loaded(str(service_id))
        idx = self.tabs.indexOf(record["widget"])
        if idx >= 0:
            self.tabs.setCurrentIndex(idx)
        self.show_and_focus()

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

        try:
            recent = self.agent.conversations.recent_messages(limit=12)
            recent_text = " ".join(
                str(x.get("content", "")) for x in recent if x.get("role") == "user"
            )[-5000:]
            project = self.agent.projects.current().get("data") or {}
            workplace_query = " ".join([
                str(project.get("name", "")),
                str(project.get("description", "")),
                recent_text,
            ]).strip()
            workplace_suggestions = self.agent.workplace.suggestions(
                workplace_query or "rotina de trabalho", limit=6
            ).get("items", [])
        except Exception:
            workplace_suggestions = []

        return {
            "model": f"{self.agent.models.fast_model_name()} ↔ {self.agent.models.reason_model_name()}",
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
            "long_horizon": {
                "stats": self.agent.long_horizon.stats(),
                "worker": self.agent.long_horizon.worker_status(),
                "items": self.agent.long_horizon.list(limit=20).get("items", []),
            },
            "workplace": {
                "stats": self.agent.workplace.stats(),
                "suggestions": workplace_suggestions,
                "categories": self.agent.workplace.categories,
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
                "reflections": self.agent.reflections.stats(),
                "reflection_items": self.agent.reflections.list(limit=10).get("items", []),
            },
            "projects": {
                "stats": self.agent.projects.stats(),
                "current": self.agent.projects.current().get("data"),
                "items": self.agent.projects.list(status="active", limit=30).get("items", []),
                "notes": self.agent.projects.notes(self.agent.projects.current_id(), limit=10).get("items", [])
                    if self.agent.projects.current_id() else [],
            },
            "attachments": {
                "stats": self.agent.attachments.stats(),
                "items": self.agent.attachments.list(
                    session_id=self.agent.conversations.current_session_id,
                    project_id=self.agent.projects.current_id(),
                    limit=20,
                ).get("items", []),
            },
            "improvements": {
                "stats": self.agent.improvements.stats(),
                "items": self.agent.improvements.list(status="proposed", limit=10).get("items", []),
            },
            "swarm": {
                "stats": self.agent.swarm.stats(),
                "agents": self.agent.swarm_registry.list(),
            },
            "apprenticeship": self.agent.apprenticeship.stats(),
            "acquisition": {
                "stats": self.agent.acquisition.stats(),
                "gaps": self.agent.acquisition.list_gaps(limit=10).get("items", []),
                "candidates": self.agent.acquisition.list_candidates(limit=10).get("items", []),
            },
            "hardware": self.agent.hardware.profile(),
            "public_data": {
                "stats": self.agent.public_data.stats(),
                "sources": self.agent.public_data.list_sources(limit=50).get("items", []),
                "proposals": self.agent.public_data.proposals(limit=10).get("items", []),
            },
            "institutional_services": {
                "stats": self.agent.services.stats(),
                "items": self.agent.services.list(daily=True).get("items", []),
            },
            "mobile": getattr(self, "mobile_companion", None).status() if getattr(self, "mobile_companion", None) else {"ok": False, "running": False},
            "updates": getattr(self, "updater", None).status() if getattr(self, "updater", None) else {"ok": False, "available": False},
            "health": self.agent.supervisor.quick_health(),
            "diagnostics": {
                "last_error": self.agent.diagnostics.last_error(),
                "recent": self.agent.diagnostics.recent(limit=12),
            },
        }

    def request_update_exit(self):
        """Close cleanly after the external updater process has been launched."""
        try:
            from PySide6.QtWidgets import QApplication
            QApplication.instance().quit()
        except Exception:
            self.close()

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

    def _format_elapsed(self):
        if not self._task_started_at:
            return "0s"
        total = max(0, int(time.monotonic() - self._task_started_at))
        hours, rem = divmod(total, 3600)
        minutes, seconds = divmod(rem, 60)
        if hours:
            return f"{hours}h {minutes:02d}m {seconds:02d}s"
        if minutes:
            return f"{minutes}m {seconds:02d}s"
        return f"{seconds}s"

    def _emit_task_heartbeat(self):
        if self.thread is None:
            return
        base = self._last_status_detail or "Jarvis continua trabalhando"
        # Evita empilhar tempos antigos no texto recebido do worker.
        detail = f"{base} • {self._format_elapsed()} • em andamento"
        self.bridge.statusChanged.emit(
            self._map_status(base),
            detail,
        )

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
                "{}",
            )
            return

        self.current_prompt = prompt
        self._task_started_at = time.monotonic()
        self._last_status_detail = "Interpretando solicitação"
        self.bridge.statusChanged.emit(
            "thinking",
            "Interpretando solicitação • 0s • em andamento",
        )
        self._heartbeat.start()

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
        self._last_status_detail = str(detail or "Jarvis continua trabalhando")
        self.bridge.statusChanged.emit(
            self._map_status(detail),
            f"{self._last_status_detail} • {self._format_elapsed()} • em andamento",
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
        self._heartbeat.stop()
        try:
            metadata = json.dumps(self.agent._last_response_metadata or {}, ensure_ascii=False, default=str)
        except Exception:
            metadata = "{}"
        self.bridge.commandFinished.emit(
            self.current_prompt,
            result,
            ok,
            metadata,
        )

        self.bridge.snapshotChanged.emit(
            json.dumps(
                self.build_snapshot(),
                ensure_ascii=False,
            )
        )

    def _cleanup_worker(self):
        self._heartbeat.stop()
        self.worker = None
        self.thread = None
        self._task_started_at = 0.0
        self._last_status_detail = ""

    def show_mobile_pairing(self):
        mobile = getattr(self, "mobile_companion", None)
        if not mobile:
            QMessageBox.information(self, "Jarvis Mobile", "Mobile Companion indisponível nesta instalação.")
            return
        state = mobile.status()
        if not state.get("running"):
            answer = QMessageBox.question(
                self,
                "Jarvis Mobile",
                "O acesso mobile está desligado. Deseja ativá-lo agora?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if answer != QMessageBox.Yes:
                return
            state = mobile.start()
        QMessageBox.information(
            self,
            "Jarvis Mobile",
            f"Conecte o celular à mesma rede Wi-Fi.\n\n"
            f"Endereço: {state.get('url')}\n"
            f"PIN: {state.get('pin')}\n\n"
            "Abra o endereço no navegador do celular e digite o PIN. "
            "O processamento continua neste computador.",
        )

    def closeEvent(self, event):
        event.ignore()
        self.hide()
