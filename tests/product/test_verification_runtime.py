from pathlib import Path
from jarvis.runtime import GoalVerifier


def test_goal_verifier_file_and_evidence(tmp_path:Path):
    p=tmp_path/"x.txt"
    p.write_text("abc",encoding="utf-8")
    v=GoalVerifier()
    exists=v.verify({"kind":"file_exists","path":str(p)}, {})
    assert exists.passed
    ev=v.verify({"kind":"evidence_key","key":"ok"},{"ok":True})
    assert ev.passed
    bad=v.verify({"kind":"equals","field":"x","value":2},{"x":1})
    assert bad.passed is False
