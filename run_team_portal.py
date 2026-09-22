from pathlib import Path
from team_assistant.portal.server import run_portal
BASE=Path(__file__).resolve().parent
run_portal(Path.home()/"JarvisData",BASE)
