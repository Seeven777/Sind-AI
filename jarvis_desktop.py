import json
import sys
from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from core.agent import JarvisAgent
from ui.habitat import HabitatWindow
from ui.hotkey import GlobalHotkey, HotkeyBridge
from ui.popup import make_icon
from mobile.companion import MobileCompanion


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

    mobile = MobileCompanion(agent, config, BASE)
    window.mobile_companion = mobile
    if config.get("mobile_companion_enabled", True) and config.get("mobile_companion_autostart", False):
        try:
            mobile.start()
        except Exception:
            pass

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

    mobile_toggle = QAction("Ativar acesso mobile", app)
    def toggle_mobile():
        try:
            state = mobile.toggle()
            mobile_toggle.setText("Desativar acesso mobile" if state.get("running") else "Ativar acesso mobile")
            if state.get("running"):
                window.show_mobile_pairing()
        except Exception as exc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(window, "Acesso mobile", str(exc))
    mobile_toggle.triggered.connect(toggle_mobile)
    menu.addAction(mobile_toggle)

    mobile_info = QAction("Mostrar acesso mobile", app)
    mobile_info.triggered.connect(window.show_mobile_pairing)
    menu.addAction(mobile_info)

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
            mobile.stop()
        except Exception:
            pass
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
