from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from .base import RiskLevel, ToolResult


class SystemTimeTool:
    tool_id='system.time'
    risk=RiskLevel.READ
    def execute(self,payload):
        return ToolResult(
            True,
            {'utc':datetime.now(timezone.utc).isoformat()},
            {'source':'system_clock'}
        )
    def verify(self,payload,result):
        return ToolResult(
            bool(result.output.get('utc')),
            result.output,
            result.evidence,
            result.error
        )


class ReadTextFileTool:
    tool_id='files.read_text'
    risk=RiskLevel.READ
    def execute(self,payload):
        path=Path(payload['path']).expanduser().resolve()
        if not path.exists() or not path.is_file():
            return ToolResult(False,error=f'Arquivo não encontrado: {path}')
        try:
            content=path.read_text(encoding=payload.get('encoding','utf-8'))
        except Exception as exc:
            return ToolResult(False,error=f'Falha ao ler {path}: {exc}')
        return ToolResult(
            True,
            {'path':str(path),'content':content},
            {'exists':True,'size':path.stat().st_size}
        )
    def verify(self,payload,result):
        if not result.success: return result
        p=Path(result.output['path'])
        return ToolResult(
            p.is_file(),
            result.output,
            {'exists':p.is_file(),'size':p.stat().st_size if p.is_file() else None},
            None if p.is_file() else 'Arquivo deixou de existir após a leitura.'
        )


class ListDirectoryTool:
    tool_id='files.list_directory'
    risk=RiskLevel.READ
    def execute(self,payload):
        path=Path(payload['path']).expanduser().resolve()
        if not path.exists() or not path.is_dir():
            return ToolResult(False,error=f'Pasta não encontrada: {path}')
        limit=max(1,min(int(payload.get('limit',100)),500))
        entries=[]
        try:
            for item in sorted(path.iterdir(),key=lambda p:(not p.is_dir(),p.name.lower()))[:limit]:
                entries.append({
                    'name':item.name,
                    'path':str(item),
                    'kind':'folder' if item.is_dir() else 'file',
                    'size':item.stat().st_size if item.is_file() else None,
                })
        except Exception as exc:
            return ToolResult(False,error=f'Falha ao listar {path}: {exc}')
        return ToolResult(
            True,
            {'path':str(path),'entries':entries,'count':len(entries)},
            {'exists':True,'is_dir':True}
        )
    def verify(self,payload,result):
        if not result.success: return result
        p=Path(result.output['path'])
        return ToolResult(
            p.is_dir(),
            result.output,
            {'exists':p.exists(),'is_dir':p.is_dir()},
            None if p.is_dir() else 'Pasta não pôde ser confirmada.'
        )


class WriteWorkspaceTextTool:
    """Writes only inside Jarvis' dedicated workspace_files directory."""
    tool_id='files.write_workspace_text'
    risk=RiskLevel.INTERNAL_WRITE

    def __init__(self,root:Path):
        self.root=Path(root).resolve()

    def _target(self,relative_path:str)->Path:
        relative=Path(relative_path)
        if relative.is_absolute():
            raise ValueError('Use um caminho relativo ao workspace do Jarvis.')
        target=(self.root/relative).resolve()
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise ValueError('O caminho solicitado sai do workspace permitido.') from exc
        return target

    def execute(self,payload):
        try:
            target=self._target(str(payload['relative_path']))
            target.parent.mkdir(parents=True,exist_ok=True)
            content=str(payload.get('content',''))
            target.write_text(content,encoding='utf-8')
            digest=hashlib.sha256(target.read_bytes()).hexdigest()
            return ToolResult(
                True,
                {'path':str(target),'relative_path':str(target.relative_to(self.root)),'chars':len(content)},
                {'exists':target.is_file(),'sha256':digest}
            )
        except Exception as exc:
            return ToolResult(False,error=str(exc))

    def verify(self,payload,result):
        if not result.success: return result
        p=Path(result.output['path'])
        if not p.is_file():
            return ToolResult(False,result.output,{'exists':False},'Arquivo não encontrado após escrita.')
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        ok=digest==result.evidence.get('sha256')
        return ToolResult(
            ok,result.output,
            {'exists':True,'sha256':digest,'matches_execution':ok},
            None if ok else 'Checksum divergente após escrita.'
        )
