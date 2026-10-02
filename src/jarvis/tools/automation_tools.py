from __future__ import annotations

import asyncio
from pathlib import Path

from .base import RiskLevel,ToolResult


def _run(coro):
    return asyncio.run(coro)


class BrowserOpenTool:
    tool_id='browser.open'
    risk=RiskLevel.READ
    def __init__(self,controller): self.controller=controller
    def execute(self,payload):
        try:
            result=_run(self.controller.open(str(payload['url'])))
            return ToolResult(True,result,{'browser_opened':True,'url':result.get('url')})
        except Exception as exc:
            return ToolResult(False,error=str(exc))
    def verify(self,payload,result):
        ok=bool(result.success and result.output.get('url'))
        return ToolResult(ok,result.output,result.evidence,result.error if not ok else None)


class BrowserSnapshotTool:
    tool_id='browser.snapshot'
    risk=RiskLevel.READ
    def __init__(self,controller): self.controller=controller
    def execute(self,payload):
        try:
            result=_run(self.controller.snapshot(int(payload.get('max_chars',12000))))
            return ToolResult(True,result,{'observed_url':result.get('url'),'chars':len(result.get('text',''))})
        except Exception as exc:
            return ToolResult(False,error=str(exc))
    def verify(self,payload,result):
        ok=bool(result.success and result.output.get('url') is not None)
        return ToolResult(ok,result.output,result.evidence,result.error if not ok else None)


class BrowserFillTool:
    tool_id='browser.fill'
    risk=RiskLevel.INTERNAL_WRITE
    def __init__(self,controller): self.controller=controller
    def execute(self,payload):
        try:
            result=_run(self.controller.fill(str(payload['selector']),str(payload.get('text',''))))
            return ToolResult(True,result,{
                'field_changed':True,
                'selector':payload['selector'],
                'filled_chars':result.get('filled_chars'),
            })
        except Exception as exc:
            return ToolResult(False,error=str(exc))
    def verify(self,payload,result):
        ok=bool(result.success and result.evidence.get('field_changed'))
        return ToolResult(ok,result.output,result.evidence,result.error if not ok else None)


class BrowserClickTool:
    tool_id='browser.click'
    risk=RiskLevel.EXTERNAL_WRITE
    def __init__(self,controller): self.controller=controller
    def execute(self,payload):
        try:
            result=_run(self.controller.click(str(payload['selector'])))
            return ToolResult(True,result,{
                'click_invoked':True,
                'selector':payload['selector'],
                'observed_after':{'url':result.get('url'),'title':result.get('title')},
            })
        except Exception as exc:
            return ToolResult(False,error=str(exc))
    def verify(self,payload,result):
        # Confirms the UI action and post-click observation. It does not claim a
        # business outcome such as "message sent"; higher-level verifier must.
        ok=bool(result.success and result.evidence.get('click_invoked') and result.output.get('url') is not None)
        return ToolResult(ok,result.output,result.evidence,result.error if not ok else None)


class WindowsListTool:
    tool_id='windows.list'
    risk=RiskLevel.READ
    def __init__(self,controller): self.controller=controller
    def execute(self,payload):
        try:
            result=_run(self.controller.list_windows())
            return ToolResult(True,{'windows':result,'count':len(result)},{'uia_observed':True,'count':len(result)})
        except Exception as exc:
            return ToolResult(False,error=str(exc))
    def verify(self,payload,result):
        return ToolResult(bool(result.success and result.evidence.get('uia_observed')),result.output,result.evidence,result.error)


class WindowsInspectTool:
    tool_id='windows.inspect'
    risk=RiskLevel.READ
    def __init__(self,controller): self.controller=controller
    def execute(self,payload):
        try:
            result=_run(self.controller.inspect(str(payload['window_title_re']),int(payload.get('depth',2))))
            return ToolResult(True,result,{'uia_observed':True,'controls':len(result.get('controls',[]))})
        except Exception as exc:
            return ToolResult(False,error=str(exc))
    def verify(self,payload,result):
        return ToolResult(bool(result.success and result.evidence.get('uia_observed')),result.output,result.evidence,result.error)


class WindowsActivateTool:
    tool_id='windows.activate'
    risk=RiskLevel.INTERNAL_WRITE
    def __init__(self,controller): self.controller=controller
    def execute(self,payload):
        try:
            result=_run(self.controller.interact({
                'kind':'activate','window_title_re':payload['window_title_re']
            }))
            return ToolResult(True,result,{'uia_action':'activate','window':result.get('window')})
        except Exception as exc:
            return ToolResult(False,error=str(exc))
    def verify(self,payload,result):
        return ToolResult(bool(result.success and result.output.get('success')),result.output,result.evidence,result.error)


class WindowsSetTextTool:
    tool_id='windows.set_text'
    risk=RiskLevel.INTERNAL_WRITE
    def __init__(self,controller): self.controller=controller
    def execute(self,payload):
        try:
            action={'kind':'set_text','window_title_re':payload['window_title_re'],'text':payload.get('text','')}
            for key in ('title','auto_id','control_type','timeout'):
                if key in payload: action[key]=payload[key]
            result=_run(self.controller.interact(action))
            return ToolResult(True,result,{
                'uia_action':'set_text','window':result.get('window'),
                'chars':result.get('chars'),
            })
        except Exception as exc:
            return ToolResult(False,error=str(exc))
    def verify(self,payload,result):
        ok=bool(result.success and result.output.get('success') and result.evidence.get('uia_action')=='set_text')
        return ToolResult(ok,result.output,result.evidence,result.error if not ok else None)


class WindowsClickTool:
    tool_id='windows.click'
    risk=RiskLevel.EXTERNAL_WRITE
    def __init__(self,controller): self.controller=controller
    def execute(self,payload):
        try:
            action={'kind':'click','window_title_re':payload['window_title_re']}
            for key in ('title','auto_id','control_type','timeout'):
                if key in payload: action[key]=payload[key]
            result=_run(self.controller.interact(action))
            return ToolResult(True,result,{
                'uia_action':'click','window':result.get('window'),
                'criteria':result.get('criteria',{}),
            })
        except Exception as exc:
            return ToolResult(False,error=str(exc))
    def verify(self,payload,result):
        ok=bool(result.success and result.output.get('success') and result.evidence.get('uia_action')=='click')
        return ToolResult(ok,result.output,result.evidence,result.error if not ok else None)
