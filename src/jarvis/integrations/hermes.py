from __future__ import annotations

import asyncio
import os
import shutil
import sys
from pathlib import Path
from dataclasses import dataclass


class HermesError(RuntimeError):
    pass


@dataclass(slots=True, frozen=True)
class HermesResult:
    success: bool
    content: str
    metadata: dict


class HermesAgentBridge:
    """Advisory bridge to an installed Hermes Agent CLI.

    The bridge deliberately defaults to the Hermes ``safe`` toolset, which
    provides read-oriented web/vision capabilities without granting terminal,
    file-write or browser-control powers to a Hermes session launched by Jarvis.
    Jarvis Operator remains the authority for physical/external actions.
    """

    provider_id = "hermes"

    def __init__(
        self,
        *,
        command: str = "hermes",
        profile: str = "",
        toolsets: str = "safe",
        timeout_seconds: int = 300,
        enabled: bool = True,
    ):
        self.command = command.strip() or "hermes"
        self.profile = profile.strip()
        self.toolsets = toolsets.strip() or "safe"
        self.timeout_seconds = max(10, int(timeout_seconds))
        self.enabled = bool(enabled)

    def executable(self) -> str | None:
        if not self.enabled:
            return None

        # Windows may ignore extensionless executable scripts in shutil.which()
        # because PATHEXT is consulted. Prefer an exact PATH entry first so a
        # local/dev shim is resolved deterministically, then fall back to the
        # normal platform lookup for hermes.exe/hermes.cmd/etc.
        path_value = os.environ.get("PATH", "")
        for entry in path_value.split(os.pathsep):
            if not entry:
                continue
            candidate = Path(entry) / self.command
            if candidate.is_file():
                return str(candidate)
            if os.name == "nt":
                pathext = os.environ.get(
                    "PATHEXT", ".COM;.EXE;.BAT;.CMD"
                ).split(";")
                for ext in pathext:
                    if not ext:
                        continue
                    for suffix in (ext.lower(), ext.upper()):
                        candidate_ext = Path(entry) / f"{self.command}{suffix}"
                        if candidate_ext.is_file():
                            return str(candidate_ext)

        return shutil.which(self.command)

    def health(self) -> dict:
        executable = self.executable()
        if not self.enabled:
            return {
                "status": "disabled",
                "provider": self.provider_id,
                "command": self.command,
                "toolsets": self.toolsets,
            }
        if not executable:
            return {
                "status": "unavailable",
                "provider": self.provider_id,
                "command": self.command,
                "toolsets": self.toolsets,
                "error": "Comando Hermes não encontrado no PATH.",
            }
        return {
            "status": "healthy",
            "provider": self.provider_id,
            "command": executable,
            "profile": self.profile or None,
            "toolsets": self.toolsets,
        }

    def _argv(self, prompt: str) -> list[str]:
        args = [self.command]
        if self.profile:
            args.extend(["--profile", self.profile])
        args.extend(["-z", prompt])
        if self.toolsets:
            args.extend(["--toolsets", self.toolsets])
        return args

    async def run(self, prompt: str) -> HermesResult:
        health = self.health()
        if health["status"] != "healthy":
            raise HermesError(health.get("error", "Hermes indisponível."))
        prompt = str(prompt).strip()
        if not prompt:
            raise HermesError("Prompt Hermes vazio.")

        env = os.environ.copy()
        resolved = self.executable()
        if resolved is None:
            raise HermesError("Executável Hermes não está disponível.")

        argv = self._argv(prompt)
        # Test/dev shims on Windows are sometimes extensionless executable
        # scripts with a shebang. Windows CreateProcess cannot launch these
        # directly, so invoke the current Python interpreter explicitly.
        resolved_path = Path(resolved)
        if resolved_path.is_file() and not resolved_path.suffix:
            try:
                first_line = resolved_path.open("r", encoding="utf-8").readline()
            except (OSError, UnicodeDecodeError):
                first_line = ""
            if first_line.startswith("#!"):
                argv = [sys.executable, resolved, *argv[1:]]

        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            raise HermesError(
                f"Hermes excedeu o timeout de {self.timeout_seconds}s."
            )

        content = stdout.decode("utf-8", errors="replace").strip()
        error = stderr.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            raise HermesError(
                f"Hermes terminou com código {proc.returncode}: "
                f"{error or content or 'sem detalhes'}"
            )
        if not content:
            raise HermesError("Hermes terminou sem resposta final.")

        return HermesResult(
            True,
            content,
            {
                "provider": self.provider_id,
                "profile": self.profile or None,
                "toolsets": self.toolsets,
                "returncode": proc.returncode,
            },
        )
