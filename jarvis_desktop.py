import json
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from core.agent import JarvisAgent
from ui.habitat import HabitatWindow
from ui.hotkey import GlobalHotkey, HotkeyBridge
from ui.popup import make_icon
from mobile.companion import MobileCompanion
from updates.manager import UpdateManager


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

    updater = UpdateManager(BASE, config)
    window.updater = updater
    if config.get("update_auto_check", True):
        updater.check_async(force=False)
    update_timer = QTimer()
    update_timer.setInterval(60 * 60 * 1000)
    update_timer.timeout.connect(lambda: updater.check_async(force=False))
    update_timer.start()

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

    update_action = QAction("Verificar atualizações", app)
    def check_updates():
        state = updater.check(force=True)
        from PySide6.QtWidgets import QMessageBox
        if state.get("available"):
            remote = state.get("remote_version") or (state.get("remote_sha") or "")[:8]
            msg = f"Atualização disponível: {remote}\n\n{state.get('remote_message','')}"
            box = QMessageBox(window)
            box.setWindowTitle("Atualização do Jarvis")
            box.setText(msg)
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            box.button(QMessageBox.Yes).setText("Atualizar agora")
            box.button(QMessageBox.No).setText("Depois")
            if box.exec() == QMessageBox.Yes:
                result = updater.launch_update()
                if result.get("ok"):
                    window.request_update_exit()
                else:
                    QMessageBox.warning(window, "Atualização", result.get("error","Falha ao iniciar atualização."))
        elif state.get("error"):
            QMessageBox.warning(window, "Atualização", state.get("error"))
        else:
            QMessageBox.information(window, "Atualização", "Você já está na versão mais recente.")
    update_action.triggered.connect(check_updates)
    menu.addAction(update_action)

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

    _shutdown_done = {"value": False}

    def cleanup_app():
        if _shutdown_done["value"]:
            return
        _shutdown_done["value"] = True
        try:
            hotkey.stop()
        except Exception:
            pass
        try:
            mobile.stop()
        except Exception:
            pass
        try:
            agent.shutdown()
        except Exception:
            pass
        try:
            tray.hide()
        except Exception:
            pass

    def quit_app():
        cleanup_app()
        app.quit()

    app.aboutToQuit.connect(cleanup_app)
    quit_action.triggered.connect(quit_app)

    window.show_and_focus()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
