import ctypes
import ctypes.wintypes
import threading

from PySide6.QtCore import QObject, Signal


class HotkeyBridge(QObject):
    activated = Signal()
    failed = Signal(str)


class GlobalHotkey:
    MOD_CONTROL = 0x0002
    VK_SPACE = 0x20
    WM_HOTKEY = 0x0312
    WM_QUIT = 0x0012

    def __init__(self, bridge):
        self.bridge = bridge
        self.thread = None
        self.thread_id = None
        self.hotkey_id = 1

    def start(self):
        if self.thread and self.thread.is_alive():
            return

        self.thread = threading.Thread(
            target=self._run,
            daemon=True
        )
        self.thread.start()

    def _run(self):
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        self.thread_id = kernel32.GetCurrentThreadId()

        ok = user32.RegisterHotKey(
            None,
            self.hotkey_id,
            self.MOD_CONTROL,
            self.VK_SPACE,
        )

        if not ok:
            self.bridge.failed.emit(
                "Não consegui registrar Ctrl+Space. "
                "Outro programa pode estar usando esse atalho."
            )
            return

        msg = ctypes.wintypes.MSG()

        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == self.WM_HOTKEY and msg.wParam == self.hotkey_id:
                    self.bridge.activated.emit()
        finally:
            user32.UnregisterHotKey(None, self.hotkey_id)

    def stop(self):
        if self.thread_id:
            ctypes.windll.user32.PostThreadMessageW(
                self.thread_id,
                self.WM_QUIT,
                0,
                0,
            )
