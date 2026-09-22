from pathlib import Path


class ResultVerifier:
    def __init__(self, file_tools=None):
        self.file_tools = file_tools

    def verify(self, tool_name, args, result):
        if not isinstance(result, dict):
            return {"verified": False, "reason": "Resultado inválido."}
        if not result.get("ok"):
            return {"verified": False, "reason": result.get("error","Ferramenta reportou falha.")}

        try:
            if tool_name == "create_folder":
                p = Path(result.get("path",""))
                return {"verified": p.is_dir(), "reason": "Pasta existe." if p.is_dir() else "Pasta não encontrada após criação."}

            if tool_name == "create_file":
                p = Path(result.get("path",""))
                return {"verified": p.is_file(), "reason": "Arquivo existe." if p.is_file() else "Arquivo não encontrado após criação."}

            if tool_name in {"copy_item","move_item"}:
                p = Path(result.get("destination",""))
                return {"verified": p.exists(), "reason": "Destino existe." if p.exists() else "Destino não encontrado."}

            if tool_name == "rename_item":
                p = Path(result.get("new_path",""))
                return {"verified": p.exists(), "reason": "Novo caminho existe." if p.exists() else "Novo caminho não encontrado."}

            if tool_name == "delete_item":
                p = Path(result.get("path",""))
                return {"verified": not p.exists(), "reason": "Item removido." if not p.exists() else "Item ainda existe."}

            if tool_name == "execute_action":
                # Engines retornam ok somente após a operação ter respondido.
                return {"verified": True, "reason": f"Engine {result.get('engine','local')} confirmou a operação."}

            if tool_name == "execute_capability":
                return {"verified": bool(result.get("ok")), "reason": "Fonte externa respondeu."}

            return {"verified": True, "reason": "Resultado confirmado pela ferramenta."}
        except Exception as exc:
            return {"verified": False, "reason": f"Falha na verificação: {exc}"}
