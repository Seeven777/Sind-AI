import ctypes
from pathlib import Path


def get_desktop_path():
    """Obtém a Área de Trabalho real do Windows, inclusive se houver redirecionamento."""
    try:
        buf = ctypes.create_unicode_buffer(260)
        CSIDL_DESKTOPDIRECTORY = 0x10
        result = ctypes.windll.shell32.SHGetFolderPathW(
            None, CSIDL_DESKTOPDIRECTORY, None, 0, buf
        )
        if result == 0 and buf.value:
            return Path(buf.value).resolve()
    except Exception:
        pass

    return (Path.home() / "Desktop").resolve()
