import json
import os
import platform
import shutil
import subprocess
from pathlib import Path


class HardwareProfiler:
    """Detecta capacidade local e recomenda um perfil de modelos sem exigir GPU."""

    def __init__(self):
        self._cached = None

    def _memory_gb(self):
        try:
            if os.name == "nt":
                import ctypes
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]
                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(stat)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                return round(stat.ullTotalPhys / (1024**3), 1)
            p = Path("/proc/meminfo")
            if p.exists():
                for line in p.read_text().splitlines():
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return round(kb / 1024 / 1024, 1)
        except Exception:
            pass
        return None

    def _run_hidden(self, cmd, timeout=5):
        kwargs = {"capture_output": True, "text": True, "timeout": timeout}
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            try:
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                kwargs["startupinfo"] = si
            except Exception:
                pass
        return subprocess.run(cmd, **kwargs)

    def _gpu(self):
        gpus = []
        if shutil.which("nvidia-smi"):
            try:
                p = self._run_hidden(
                    ["nvidia-smi","--query-gpu=name,memory.total","--format=csv,noheader,nounits"],
                    timeout=4
                )
                for line in p.stdout.splitlines():
                    parts = [x.strip() for x in line.split(",")]
                    if parts:
                        gpus.append({"name": parts[0], "vram_mb": int(parts[1]) if len(parts)>1 and parts[1].isdigit() else None, "vendor":"NVIDIA"})
            except Exception:
                pass
        if not gpus and os.name == "nt":
            try:
                cmd = [
                    "powershell","-NoProfile","-Command",
                    "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"
                ]
                p = self._run_hidden(cmd, timeout=5)
                for line in p.stdout.splitlines():
                    if line.strip():
                        gpus.append({"name": line.strip(), "vram_mb": None, "vendor":"unknown"})
            except Exception:
                pass
        return gpus

    def profile(self, refresh=False):
        if self._cached and not refresh:
            return self._cached
        ram = self._memory_gb()
        cpu_threads = os.cpu_count() or 1
        gpu = self._gpu()
        nvidia_vram = max([x.get("vram_mb") or 0 for x in gpu if x.get("vendor")=="NVIDIA"] or [0])

        if (ram or 0) >= 32 and nvidia_vram >= 8000:
            tier = "power"
            fast = "qwen3:4b"
            reason = "qwen3:8b"
            parallel = 2
        elif (ram or 0) >= 12 and cpu_threads >= 8:
            tier = "standard"
            fast = "qwen3:1.7b"
            reason = "qwen3:4b"
            parallel = 1
        else:
            tier = "lite"
            fast = "qwen3:0.6b"
            reason = "qwen3:1.7b"
            parallel = 1

        self._cached = {
            "ok": True,
            "tier": tier,
            "os": platform.platform(),
            "cpu": platform.processor() or platform.machine(),
            "cpu_threads": cpu_threads,
            "ram_gb": ram,
            "gpus": gpu,
            "recommended": {
                "fast_model": fast,
                "reasoning_model": reason,
                "parallel_agents": parallel,
                "semantic_memory": tier != "lite",
            },
        }
        return self._cached
