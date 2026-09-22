from datetime import datetime
from pathlib import Path
from PIL import ImageGrab

def take_screenshot(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / datetime.now().strftime("screenshot_%Y%m%d_%H%M%S.png")
    img = ImageGrab.grab(all_screens=True)
    img.save(path)
    return {"ok": True, "path": str(path), "width": img.width, "height": img.height}
