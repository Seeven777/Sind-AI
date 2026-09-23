import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class Phase2CorePatcherTests(unittest.TestCase):
    def test_patcher_inserts_context_hook_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "core").mkdir()
            fixture = '''class JarvisAgent:\n    def system_prompt(self, user_text=""):\n        experience_context = self.experience.context(\n            user_text,\n            project_id=self.projects.current_id(),\n            max_chars=2400,\n        ).get("text", "") if hasattr(self, "experience") else ""\n        return f"""- Use computador e integrações apenas quando ajudarem o objetivo.\n- High/critical continuam sujeitos à governança.\nPROJETO ATUAL\n{project_context or "- nenhum projeto ativo"}\n\nPROCEDIMENTOS ENSINADOS RELEVANTES\n"""\n'''
            (root / "core" / "agent.py").write_text(fixture, encoding="utf-8")
            script = Path(__file__).resolve().parents[1] / "apply_phase2_core_patch.py"
            first = subprocess.run([sys.executable, str(script)], cwd=root, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
            text = (root / "core" / "agent.py").read_text(encoding="utf-8")
            self.assertIn("Phase 2 personal operational context", text)
            self.assertIn("CONTEXTO OPERACIONAL PESSOAL", text)
            self.assertIn("DADO NÃO CONFIÁVEL", text)
            second = subprocess.run([sys.executable, str(script)], cwd=root, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0)
            text2 = (root / "core" / "agent.py").read_text(encoding="utf-8")
            self.assertEqual(text, text2)


if __name__ == "__main__":
    unittest.main()
