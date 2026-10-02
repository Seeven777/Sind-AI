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
                matches = p.is_file() and "content" in args and p.read_text(encoding="utf-8") == args["content"]
                return {"verified": matches, "scope": "tool", "reason": "Conteúdo do arquivo relido e comparado." if matches else "Arquivo/conteúdo não corresponde ao solicitado."}

            if tool_name in {"copy_item","move_item"}:
                p = Path(result.get("destination",""))
                return {"verified": p.exists(), "reason": "Destino existe." if p.exists() else "Destino não encontrado."}

            if tool_name == "rename_item":
                p = Path(result.get("new_path",""))
                return {"verified": p.exists(), "reason": "Novo caminho existe." if p.exists() else "Novo caminho não encontrado."}

            if tool_name == "delete_item":
                p = Path(result.get("path",""))
                return {"verified": not p.exists(), "reason": "Item removido." if not p.exists() else "Item ainda existe."}

            if tool_name == "open_app":
                from runtime.phase4.runtime import verify_open_app
                return verify_open_app(args.get("app", ""))

            if tool_name == "whatsapp_send_message":
                return result.get("goal_verification", {"verified": False, "reason": "Sem evidência UIA."})

            if tool_name == "type_text":
                return {"verified": bool(result.get("text_verified")), "scope": "tool", "reason": "Releitura do campo; não verifica o objetivo completo."}

            if tool_name == "select_window":
                return {"verified": False, "reason": "Seleção de janela não confirma o objetivo."}

            if tool_name == "execute_action":
                # A resposta do engine é tool execution, não prova do objetivo.
                return {"verified": False, "reason": "Retorno do engine não comprova o objetivo físico."}

            if tool_name == "execute_capability":
                return {"verified": bool(result.get("ok")), "reason": "Fonte externa respondeu."}

            from runtime.phase4.runtime import READ_TOOLS
            if tool_name in READ_TOOLS:
                return {"verified": True, "scope": "tool", "reason": "Leitura retornou dados; não comprova execução do objetivo."}
            return {"verified": False, "scope": "tool", "reason": "Ferramenta executada sem pós-condição observável implementada."}
        except Exception as exc:
            return {"verified": False, "reason": f"Falha na verificação: {exc}"}
