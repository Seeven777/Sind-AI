from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def make_icon():
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor("#14171d"))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(2, 2, 60, 60)

    painter.setPen(QColor("#f2f2f2"))
    font = painter.font()
    font.setBold(True)
    font.setPointSize(25)
    painter.setFont(font)
    painter.drawText(pix.rect(), Qt.AlignCenter, "J")
    painter.end()

    return QIcon(pix)


class AgentWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)
    status_changed = Signal(str)
    confirmation_requested = Signal(str, str)

    def __init__(self, agent, prompt):
        super().__init__()
        self.agent = agent
        self.prompt = prompt
        import threading
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
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class JarvisPopup(QMainWindow):
    request_quit = Signal()

    def __init__(self, agent, config):
        super().__init__()
        self.agent = agent
        self.config = config
        self.thread = None
        self.worker = None

        self.setWindowTitle("Jarvis")
        self.setWindowIcon(make_icon())
        self.resize(650, 440)

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._build()

    def _build(self):
        shell = QWidget()
        shell.setObjectName("shell")
        self.setCentralWidget(shell)

        root = QVBoxLayout(shell)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        top = QHBoxLayout()

        title = QLabel("Jarvis")
        title.setObjectName("title")

        self.status = QLabel("Pronto")
        self.status.setObjectName("status")

        minimize = QPushButton("—")
        minimize.setObjectName("topButton")
        minimize.setFixedSize(30, 30)
        minimize.clicked.connect(self.hide)

        close = QPushButton("×")
        close.setObjectName("topButton")
        close.setFixedSize(30, 30)
        close.clicked.connect(self.hide)

        top.addWidget(title)
        top.addStretch()
        top.addWidget(self.status)
        top.addSpacing(10)
        top.addWidget(minimize)
        top.addWidget(close)

        root.addLayout(top)

        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setPlaceholderText(
            "Jarvis pronto.\n\n"
            "Ctrl + Space mostra ou esconde esta janela."
        )
        root.addWidget(self.chat, 1)

        bottom = QHBoxLayout()

        self.input = QLineEdit()
        self.input.setPlaceholderText("Digite uma tarefa...")
        self.input.returnPressed.connect(self.send)

        self.send_button = QPushButton("Executar")
        self.send_button.clicked.connect(self.send)

        bottom.addWidget(self.input, 1)
        bottom.addWidget(self.send_button)

        root.addLayout(bottom)

        meta = QLabel(
            f"Local • {self.config['model']} • Fast Path + ferramentas"
        )
        meta.setObjectName("meta")
        root.addWidget(meta)

        self.setStyleSheet("""
            QWidget#shell {
                background: #111318;
                border: 1px solid #292e37;
                border-radius: 18px;
            }

            QLabel#title {
                color: #f4f4f4;
                font-size: 20px;
                font-weight: 700;
            }

            QLabel#status {
                color: #9ca3af;
                font-size: 12px;
            }

            QLabel#meta {
                color: #737985;
                font-size: 11px;
            }

            QTextEdit {
                background: #171a20;
                color: #eeeeee;
                border: 1px solid #292e37;
                border-radius: 12px;
                padding: 12px;
                font-size: 13px;
            }

            QLineEdit {
                background: #171a20;
                color: #ffffff;
                border: 1px solid #343a46;
                border-radius: 12px;
                padding: 11px 13px;
                font-size: 13px;
            }

            QPushButton {
                background: #262b34;
                color: #ffffff;
                border: 1px solid #383e49;
                border-radius: 10px;
                padding: 10px 15px;
            }

            QPushButton:hover {
                background: #303641;
            }

            QPushButton:disabled {
                color: #727986;
                background: #1b1e24;
            }

            QPushButton#topButton {
                background: transparent;
                border: none;
                font-size: 18px;
                padding: 0;
            }

            QPushButton#topButton:hover {
                background: #272b33;
            }
        """)

    def show_and_focus(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.input.setFocus()

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self.show_and_focus()

    def send(self):
        prompt = self.input.text().strip()

        if not prompt or self.thread is not None:
            return

        self.chat.append(f"<b>Você:</b> {prompt}")
        self.input.clear()

        self.status.setText("Processando")
        self.send_button.setEnabled(False)
        self.input.setEnabled(False)

        self.thread = QThread(self)
        self.worker = AgentWorker(self.agent, prompt)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.status_changed.connect(self.status.setText)
        self.worker.confirmation_requested.connect(self._confirm_action)
        self.worker.finished.connect(self._done)
        self.worker.failed.connect(self._failed)

        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)

        self.thread.finished.connect(self._cleanup)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()


    def _confirm_action(self, title, message):
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(message)
        box.setIcon(QMessageBox.Warning)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        approved = box.exec() == QMessageBox.Yes
        if self.worker:
            self.worker.resolve_confirmation(approved)

    def _done(self, text):
        self.chat.append(f"<b>Jarvis:</b> {text}")
        self.status.setText("Pronto")

    def _failed(self, text):
        self.chat.append(f"<b>Erro:</b> {text}")
        self.status.setText("Erro")

    def _cleanup(self):
        self.send_button.setEnabled(True)
        self.input.setEnabled(True)
        self.input.setFocus()
        self.worker = None
        self.thread = None

    def closeEvent(self, event):
        event.ignore()
        self.hide()
