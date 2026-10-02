import sys
from pathlib import Path

from jarvis.mcp import MCPServer,MCPStdioClient


def test_mcp_stdio_basic(tmp_path:Path):
    server_py=tmp_path/"fake_mcp.py"
    server_py.write_text(
        "import sys,json\n"
        "for line in sys.stdin:\n"
        " m=json.loads(line); method=m.get('method'); rid=m.get('id')\n"
        " if method=='initialize': result={'protocolVersion':'2025-06-18'}\n"
        " elif method=='tools/list': result={'tools':[{'name':'echo'}]}\n"
        " elif method=='tools/call': result={'content':[{'type':'text','text':'ok'}]}\n"
        " else: result={}\n"
        " print(json.dumps({'jsonrpc':'2.0','id':rid,'result':result}),flush=True)\n",
        encoding="utf-8",
    )
    client=MCPStdioClient(MCPServer("fake",[sys.executable,str(server_py)]))
    try:
        assert client.initialize()["protocolVersion"]=="2025-06-18"
        assert client.list_tools()["tools"][0]["name"]=="echo"
        assert client.call_tool("echo")["content"][0]["text"]=="ok"
    finally:
        client.close()
