from __future__ import annotations

from dataclasses import dataclass,field
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tomllib
from datetime import datetime,timezone


def now():
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class SkillManifest:
    skill_id:str
    version:str
    description:str
    entrypoint:str='executor.py'
    permissions:tuple[str,...]=()
    capabilities:tuple[str,...]=()
    metadata:dict=field(default_factory=dict)

    @classmethod
    def from_file(cls,path:Path):
        raw=tomllib.loads(Path(path).read_text(encoding='utf-8'))
        section=raw.get('skill') or raw
        return cls(
            skill_id=str(section['id']),
            version=str(section.get('version','0.1.0')),
            description=str(section.get('description','')),
            entrypoint=str(section.get('entrypoint','executor.py')),
            permissions=tuple(section.get('permissions',[])),
            capabilities=tuple(section.get('capabilities',[])),
            metadata=dict(raw.get('metadata') or {}),
        )


class SkillRegistry:
    def __init__(self):
        self._skills={}

    def register(self,manifest,installed_path=None,state='active'):
        self._skills[(manifest.skill_id,manifest.version)]={
            'manifest':manifest,'path':str(installed_path) if installed_path else None,'state':state
        }

    def latest(self,skill_id):
        candidates=[
            value for (sid,_),value in self._skills.items()
            if sid==skill_id and value['state']=='active'
        ]
        return candidates[-1] if candidates else None

    def all(self):
        return tuple(self._skills.values())

    def capabilities(self):
        result={}
        for value in self._skills.values():
            if value['state']!='active': continue
            for cap in value['manifest'].capabilities:
                result.setdefault(cap,[]).append(value['manifest'].skill_id)
        return result


class SkillRepository:
    def __init__(self,conn):
        self.conn=conn

    def upsert(self,manifest,state,source_path,installed_path,test_result):
        self.conn.execute(
            """INSERT INTO skill_installs(
               skill_id,version,state,source_path,installed_path,manifest_json,test_json,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?)
               ON CONFLICT(skill_id,version) DO UPDATE SET
                 state=excluded.state,source_path=excluded.source_path,
                 installed_path=excluded.installed_path,manifest_json=excluded.manifest_json,
                 test_json=excluded.test_json,updated_at=excluded.updated_at""",
            (
                manifest.skill_id,manifest.version,state,str(source_path) if source_path else None,
                str(installed_path) if installed_path else None,
                json.dumps({
                    'id':manifest.skill_id,'version':manifest.version,
                    'description':manifest.description,'entrypoint':manifest.entrypoint,
                    'permissions':list(manifest.permissions),
                    'capabilities':list(manifest.capabilities),
                    'metadata':manifest.metadata,
                },ensure_ascii=False),
                json.dumps(test_result or {},ensure_ascii=False),now(),now()
            )
        ); self.conn.commit()

    def list(self):
        return [dict(r) for r in self.conn.execute(
            'SELECT * FROM skill_installs ORDER BY updated_at DESC'
        ).fetchall()]


class SkillManager:
    """Versioned skill installer.

    Skills are copied under the Jarvis data directory; the production core is
    never modified. Tests run before activation.
    """

    def __init__(self,*,root:Path,staging:Path,repository:SkillRepository,registry:SkillRegistry):
        self.root=Path(root)
        self.staging=Path(staging)
        self.repository=repository
        self.registry=registry
        self.root.mkdir(parents=True,exist_ok=True)
        self.staging.mkdir(parents=True,exist_ok=True)
        self.load_installed()

    def load_installed(self):
        for manifest_path in self.root.glob('*/*/manifest.toml'):
            try:
                manifest=SkillManifest.from_file(manifest_path)
                self.registry.register(manifest,manifest_path.parent,'active')
            except Exception:
                continue

    def validate(self,source:Path):
        source=Path(source).resolve()
        manifest_path=source/'manifest.toml'
        if not manifest_path.exists():
            raise ValueError('Skill sem manifest.toml.')
        manifest=SkillManifest.from_file(manifest_path)
        entry=source/manifest.entrypoint
        if not entry.is_file():
            raise ValueError(f'Entrypoint ausente: {manifest.entrypoint}')
        return manifest

    def test(self,source:Path,timeout=90):
        source=Path(source).resolve()
        tests=source/'tests'
        if not tests.exists():
            return {'status':'no_tests','passed':False,'returncode':None}
        try:
            proc=subprocess.run(
                [sys.executable,'-m','pytest','-q',str(tests)],
                cwd=source,
                capture_output=True,text=True,timeout=timeout,
                env={'PATH':str(Path(sys.executable).parent),'PYTHONNOUSERSITE':'1'},
            )
            return {
                'status':'passed' if proc.returncode==0 else 'failed',
                'passed':proc.returncode==0,
                'returncode':proc.returncode,
                'stdout':proc.stdout[-12000:],
                'stderr':proc.stderr[-12000:],
            }
        except subprocess.TimeoutExpired:
            return {'status':'timeout','passed':False,'returncode':None}

    def install(self,source:Path,*,require_tests=True):
        source=Path(source).resolve()
        manifest=self.validate(source)
        result=self.test(source)
        if require_tests and not result.get('passed'):
            self.repository.upsert(manifest,'rejected',source,None,result)
            raise RuntimeError(f"Skill reprovada nos testes: {result.get('status')}")
        destination=self.root/manifest.skill_id/manifest.version
        if destination.exists():
            shutil.rmtree(destination)
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(source,destination)
        self.repository.upsert(manifest,'active',source,destination,result)
        self.registry.register(manifest,destination,'active')
        return {
            'skill_id':manifest.skill_id,'version':manifest.version,
            'path':str(destination),'tests':result,
        }

    def disable(self,skill_id,version):
        item=self.registry._skills.get((skill_id,version))
        if not item:
            raise KeyError((skill_id,version))
        item['state']='disabled'
        manifest=item['manifest']
        self.repository.upsert(manifest,'disabled',item.get('path'),item.get('path'),{})
        return {'skill_id':skill_id,'version':version,'state':'disabled'}

    def create_scaffold(self,skill_id,description,capabilities=()):
        safe=''.join(c for c in skill_id if c.isalnum() or c in '._-').strip('.-_')
        if not safe:
            raise ValueError('skill_id inválido')
        folder=self.staging/safe
        if folder.exists():
            shutil.rmtree(folder)
        (folder/'tests').mkdir(parents=True)
        manifest=(
            '[skill]\n'
            f'id = "{safe}"\n'
            'version = "0.1.0"\n'
            f'description = {json.dumps(description,ensure_ascii=False)}\n'
            'entrypoint = "executor.py"\n'
            'permissions = []\n'
            f'capabilities = {json.dumps(list(capabilities),ensure_ascii=False)}\n'
        )
        (folder/'manifest.toml').write_text(manifest,encoding='utf-8')
        (folder/'executor.py').write_text(
            'def execute(payload):\n'
            '    return {"success": True, "output": payload}\n',
            encoding='utf-8'
        )
        (folder/'tests'/'test_executor.py').write_text(
            'from executor import execute\n\n'
            'def test_execute():\n'
            '    result=execute({"x":1})\n'
            '    assert result["success"] is True\n',
            encoding='utf-8'
        )
        return {'path':str(folder),'skill_id':safe}
