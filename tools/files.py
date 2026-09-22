from pathlib import Path
import shutil

class FileTools:
    def __init__(self, allowed_roots, workspace):
        self.allowed_roots = [Path(p).resolve() for p in allowed_roots]
        self.workspace = Path(workspace).resolve()

    def _allowed(self, path):
        p = Path(path).resolve()
        for root in self.allowed_roots:
            try:
                p.relative_to(root)
                return True
            except ValueError:
                pass
        return False

    def normalize(self, raw):
        p = Path(str(raw)).expanduser()
        if not p.is_absolute():
            p = self.workspace / p
        return p.resolve()

    def create_folder(self, path):
        p = self.normalize(path)
        if not self._allowed(p): return {"ok": False, "error": "Caminho não permitido."}
        p.mkdir(parents=True, exist_ok=True)
        return {"ok": True, "path": str(p)}

    def list_files(self, path):
        p = self.normalize(path)
        if not self._allowed(p): return {"ok": False, "error": "Caminho não permitido."}
        if not p.is_dir(): return {"ok": False, "error": "Pasta não encontrada."}
        items = [{"name": x.name, "type": "folder" if x.is_dir() else "file", "path": str(x)}
                 for x in sorted(p.iterdir(), key=lambda x: x.name.lower())[:250]]
        return {"ok": True, "items": items}

    def create_file(self, path, content):
        p = self.normalize(path)
        if not self._allowed(p): return {"ok": False, "error": "Caminho não permitido."}
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"ok": True, "path": str(p)}

    def read_file(self, path):
        p = self.normalize(path)
        if not self._allowed(p): return {"ok": False, "error": "Caminho não permitido."}
        if not p.is_file(): return {"ok": False, "error": "Arquivo não encontrado."}
        return {"ok": True, "path": str(p), "content": p.read_text(encoding="utf-8", errors="replace")[:12000]}

    def rename_item(self, path, new_name, overwrite=False):
        p = self.normalize(path)
        if not p.exists(): return {"ok": False, "error": "Item não encontrado."}
        d = p.with_name(new_name)
        if d.exists() and not overwrite:
            return {"ok": False, "needs_confirmation": True, "destination": str(d), "error": "Destino já existe."}
        if d.exists():
            shutil.rmtree(d) if d.is_dir() else d.unlink()
        p.rename(d)
        return {"ok": True, "new_path": str(d)}

    def copy_item(self, source, destination, overwrite=False):
        s, d = self.normalize(source), self.normalize(destination)
        if not s.exists(): return {"ok": False, "error": "Origem não encontrada."}
        if d.exists() and not overwrite:
            return {"ok": False, "needs_confirmation": True, "destination": str(d), "error": "Destino já existe."}
        if s.is_dir():
            if d.exists(): shutil.rmtree(d)
            shutil.copytree(s, d)
        else:
            d.parent.mkdir(parents=True, exist_ok=True)
            if d.exists(): d.unlink()
            shutil.copy2(s, d)
        return {"ok": True, "destination": str(d)}

    def move_item(self, source, destination, overwrite=False):
        s, d = self.normalize(source), self.normalize(destination)
        if not s.exists(): return {"ok": False, "error": "Origem não encontrada."}
        if d.exists() and not overwrite:
            return {"ok": False, "needs_confirmation": True, "destination": str(d), "error": "Destino já existe."}
        d.parent.mkdir(parents=True, exist_ok=True)
        if d.exists():
            shutil.rmtree(d) if d.is_dir() else d.unlink()
        shutil.move(str(s), str(d))
        return {"ok": True, "destination": str(d)}

    def delete_item(self, path):
        p = self.normalize(path)
        if not p.exists(): return {"ok": False, "error": "Item não encontrado."}
        shutil.rmtree(p) if p.is_dir() else p.unlink()
        return {"ok": True, "path": str(p)}

    def search_files(self, root, query, max_results=100):
        base = self.normalize(root)
        if not base.is_dir(): return {"ok": False, "error": "Pasta não encontrada."}
        q = str(query).lower()
        out = []
        for item in base.rglob("*"):
            if q in item.name.lower():
                out.append({"name": item.name, "path": str(item), "type": "folder" if item.is_dir() else "file"})
                if len(out) >= max_results: break
        return {"ok": True, "results": out}
