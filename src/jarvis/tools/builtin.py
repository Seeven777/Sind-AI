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

class WriteWorkspacePdfTool:
    """Create a PDF inside Jarvis' dedicated workspace using ReportLab."""
    tool_id='files.write_workspace_pdf'
    risk=RiskLevel.INTERNAL_WRITE

    def __init__(self,root:Path):
        self.root=Path(root).resolve()

    def _target(self,relative_path:str)->Path:
        relative=Path(relative_path)
        if relative.is_absolute():
            raise ValueError('Use um caminho relativo ao workspace do Jarvis.')
        target=(self.root/relative).resolve()
        try: target.relative_to(self.root)
        except ValueError as exc: raise ValueError('O caminho solicitado sai do workspace permitido.') from exc
        if target.suffix.lower()!='.pdf':
            target=target.with_suffix('.pdf')
        return target

    def execute(self,payload):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER
            from reportlab.lib.colors import HexColor
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Preformatted
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            target=self._target(str(payload.get('relative_path') or payload.get('path') or 'documento.pdf'))
            target.parent.mkdir(parents=True,exist_ok=True)
            title=str(payload.get('title') or 'Documento Jarvis')
            content=str(payload.get('content') or '')
            if not content.strip(): return ToolResult(False,error='Conteúdo do PDF vazio.')

            font='Helvetica'; bold='Helvetica-Bold'
            font_candidates=[
                (Path(r'C:\Windows\Fonts\segoeui.ttf'),'JarvisSegoe'),
                (Path(r'C:\Windows\Fonts\segoeuib.ttf'),'JarvisSegoeBold'),
                (Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),'JarvisDeja'),
                (Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),'JarvisDejaBold'),
            ]
            for path,name in font_candidates:
                if path.exists() and name not in pdfmetrics.getRegisteredFontNames():
                    try: pdfmetrics.registerFont(TTFont(name,str(path)))
                    except Exception: pass
            if 'JarvisSegoe' in pdfmetrics.getRegisteredFontNames(): font='JarvisSegoe'
            elif 'JarvisDeja' in pdfmetrics.getRegisteredFontNames(): font='JarvisDeja'
            if 'JarvisSegoeBold' in pdfmetrics.getRegisteredFontNames(): bold='JarvisSegoeBold'
            elif 'JarvisDejaBold' in pdfmetrics.getRegisteredFontNames(): bold='JarvisDejaBold'

            styles=getSampleStyleSheet()
            styles.add(ParagraphStyle(name='JarvisTitle',fontName=bold,fontSize=19,leading=23,textColor=HexColor('#0b1720'),alignment=TA_CENTER,spaceAfter=18))
            styles.add(ParagraphStyle(name='JarvisH2',fontName=bold,fontSize=13,leading=16,textColor=HexColor('#12344a'),spaceBefore=10,spaceAfter=7))
            styles.add(ParagraphStyle(name='JarvisBody',fontName=font,fontSize=9.5,leading=14,textColor=HexColor('#20262b'),spaceAfter=7))
            styles.add(ParagraphStyle(name='JarvisBullet',fontName=font,fontSize=9.2,leading=13,textColor=HexColor('#20262b'),leftIndent=14,firstLineIndent=-8,spaceAfter=4))
            doc=SimpleDocTemplate(str(target),pagesize=A4,rightMargin=45,leftMargin=45,topMargin=45,bottomMargin=45,title=title,author='Jarvis')
            story=[Paragraph(title.replace('&','&amp;'),styles['JarvisTitle'])]
            for raw in content.splitlines():
                line=raw.strip()
                if not line:
                    story.append(Spacer(1,5)); continue
                if line.startswith('### '): story.append(Paragraph(line[4:].replace('&','&amp;'),styles['JarvisH2'])); continue
                if line.startswith('## '): story.append(Paragraph(line[3:].replace('&','&amp;'),styles['JarvisH2'])); continue
                if line.startswith('# '): story.append(Paragraph(line[2:].replace('&','&amp;'),styles['JarvisH2'])); continue
                if line.startswith('- ') or line.startswith('* '):
                    safe=line[2:].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                    story.append(Paragraph('• '+safe,styles['JarvisBullet'])); continue
                if line.startswith('```'): continue
                if line.startswith('|'):
                    safe=line.strip('|').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                    story.append(Paragraph(safe.replace('|','  ·  '),styles['JarvisBody'])); continue
                safe=line.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                story.append(Paragraph(safe,styles['JarvisBody']))
            doc.build(story)
            data=target.read_bytes();digest=hashlib.sha256(data).hexdigest()
            return ToolResult(True,{'path':str(target),'relative_path':str(target.relative_to(self.root)),'bytes':len(data),'title':title},{'exists':target.is_file(),'sha256':digest,'pdf':True})
        except Exception as exc:
            return ToolResult(False,error=f'Falha ao criar PDF: {exc}')

    def verify(self,payload,result):
        if not result.success: return result
        p=Path(result.output['path'])
        try:
            from pypdf import PdfReader
            pages=len(PdfReader(str(p)).pages) if p.is_file() else 0
        except Exception as exc:
            return ToolResult(False,result.output,{'exists':p.is_file()},f'PDF não pôde ser lido após criação: {exc}')
        digest=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
        expected=result.evidence.get('sha256')
        ok=p.is_file() and pages>0 and digest==expected
        return ToolResult(ok,result.output,{'exists':p.is_file(),'pages':pages,'sha256':digest,'matches_execution':digest==expected},None if ok else 'PDF não pôde ser confirmado após a criação.')
