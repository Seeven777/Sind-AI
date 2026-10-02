import asyncio
from jarvis.tools import BrowserOpenTool,WindowsListTool


class Browser:
    async def open(self,url): return {"url":url,"title":"Test","status":200}


class Windows:
    async def list_windows(self): return [{"title":"A"}]


def test_browser_and_windows_tool_adapters():
    b=BrowserOpenTool(Browser())
    result=b.execute({"url":"https://example.com"})
    assert b.verify({},result).success

    w=WindowsListTool(Windows())
    result2=w.execute({})
    assert w.verify({},result2).success
    assert result2.output["count"]==1
