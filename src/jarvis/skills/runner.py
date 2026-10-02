from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


_RUNNER=r"""
import importlib.util,json,sys,pathlib
entry=pathlib.Path(sys.argv[1]).resolve()
payload=json.loads(sys.stdin.read() or "{}")
spec=importlib.util.spec_from_file_location("jarvis_skill",entry)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
if not hasattr(module,"execute"):
    raise RuntimeError("Skill entrypoint must define execute(payload)")
result=module.execute(payload)
print(json.dumps(result,ensure_ascii=False))
"""


class SkillRunner:
    def __init__(self,registry):
        self.registry=registry

    def execute(self,skill_id,payload,timeout=30):
        item=self.registry.latest(skill_id)
        if not item:
            raise KeyError(f'Skill ativa não encontrada: {skill_id}')
        manifest=item['manifest']
        root=Path(item['path'])
        entry=root/manifest.entrypoint
        proc=subprocess.run(
            [sys.executable,'-I','-c',_RUNNER,str(entry)],
            input=json.dumps(payload,ensure_ascii=False),
            capture_output=True,text=True,timeout=timeout,
            cwd=root,
            env={},
        )
        if proc.returncode!=0:
            raise RuntimeError(proc.stderr.strip() or 'Skill falhou.')
        return json.loads(proc.stdout)
