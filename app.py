import json
import sys
from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from core.agent import JarvisAgent
from ui.habitat import HabitatWindow
from ui.hotkey import GlobalHotkey, HotkeyBridge
from ui.popup import make_icon


BASE = Path(__file__).resolve().parent
CONFIG_PATH = BASE / "data" / "config.json"


def load_config():
    return json.loads(
        CONFIG_PATH.read_text(encoding="utf-8")
    )


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
