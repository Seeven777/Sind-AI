import json
import sys
from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from runtime.local_secrets import load_local_secrets

# Load user-owned secrets before HabitatWindow checks the environment.
load_local_secrets()

from core.agent import JarvisAgent
from ui.habitat import HabitatWindow
from ui.hotkey import GlobalHotkey, HotkeyBridge
from ui.popup import make_icon


BASE = Path(__file__).resolve().parent
CONFIG_PATH = BASE / "data" / "config.json"


def load_config():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    # The requested ElevenLabs voice is authoritative. Do not fall back to the
    # low-quality native Windows voice when cloud TTS is unavailable.
    config["voice_provider"] = "elevenlabs"
    config["voice_fallback_local"] = False
    config["elevenlabs_voice_id"] = "2CECaLAGTS5NRGxgbcxr"
    config.setdefault("elevenlabs_model_id", "eleven_multilingual_v2")
    return config


def main():
    config = load_config()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    agent = JarvisAgent(
        config,
        base_dir=BASE,
    )

    window = HabitatWindow(
        agent=agent,
        config=config,
        base_dir=BASE,
    )

    tray = QSystemTrayIcon(make_icon(), app)
    menu = QMenu()

    open_habitat = QAction("Abrir Habitat", app)
    open_habitat.triggered.connect(
        lambda: window.set_mode("habitat")
    )
    menu.addAction(open_habitat)

    open_compact = QAction("Abrir Compact Mode", app)
    open_compact.triggered.connect(
        lambda: window.set_mode("compact")
    )
    menu.addAction(open_compact)

    menu.addSeparator()

    quit_action = QAction("Sair", app)
    menu.addAction(quit_action)

    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda reason: window.toggle_visibility()
        if reason == QSystemTrayIcon.Trigger
        else None
    )
    tray.show()

    bridge = HotkeyBridge()
    bridge.activated.connect(
        window.toggle_visibility
    )

    hotkey = GlobalHotkey(bridge)
    hotkey.start()

    def quit_app():
        hotkey.stop()
        try:
            agent.shutdown()
        except Exception:
            pass
        tray.hide()
        app.quit()

    quit_action.triggered.connect(quit_app)

    window.show_and_focus()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
