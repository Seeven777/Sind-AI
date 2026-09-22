from datetime import datetime
from pathlib import Path
import zipfile


def backup_data(source_root, destination_dir):
    src = Path(source_root).resolve()
    dst_dir = Path(destination_dir).resolve()
    dst_dir.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        return {"ok": False, "error": "Data Vault não encontrado."}
    out = dst_dir / datetime.now().strftime("JarvisData_backup_%Y%m%d_%H%M%S.zip")
    try:
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for item in src.rglob("*"):
                if item.is_file():
                    z.write(item, arcname=item.relative_to(src))
        return {"ok": True, "path": str(out)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
