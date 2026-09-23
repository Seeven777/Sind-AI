import re
from pathlib import Path

source = (Path(__file__).resolve().parent / "mobile" / "companion.py").read_text(encoding="utf-8")
assert 're.fullmatch(r"/\\d{6}/?", path)' in source
assert 're.fullmatch(r"/\\\\d{6}/?", path)' not in source
assert re.fullmatch(r"/\d{6}/?", "/791327")
print("[OK] PIN route regex real")
