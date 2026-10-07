from __future__ import annotations

from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import sys
import importlib.util
import urllib.error
import urllib.request


class VoiceUnavailable(RuntimeError):
    pass


class WhisperCppSTT:
    def __init__(self, executable=None, model=None):
        self.executable = executable or os.environ.get("JARVIS_WHISPER_CPP")
        self.model = model or os.environ.get("JARVIS_WHISPER_MODEL")

    def health(self):
        exe = Path(self.executable).expanduser() if self.executable else None
        model = Path(self.model).expanduser() if self.model else None
        ok = bool(exe and exe.is_file() and model and model.is_file())
        return {
            "status": "healthy" if ok else "unconfigured",
            "backend": "whisper.cpp",
            "executable": str(exe) if exe else None,
            "model": str(model) if model else None,
        }

    def transcribe(self, audio_path):
        health = self.health()
        if health["status"] != "healthy":
            raise VoiceUnavailable("whisper.cpp não configurado.")
        proc = subprocess.run(
            [
                str(Path(self.executable).expanduser()),
                "-m", str(Path(self.model).expanduser()),
                "-f", str(Path(audio_path).resolve()),
                "-nt", "-np",
            ],
            capture_output=True, text=True, timeout=180,
        )
        if proc.returncode != 0:
            raise VoiceUnavailable(proc.stderr.strip() or "whisper.cpp falhou.")
        return proc.stdout.strip()


class PiperTTS:
    def __init__(self, executable=None, model=None):
        self.executable = executable or os.environ.get("JARVIS_PIPER")
        self.model = model or os.environ.get("JARVIS_PIPER_MODEL")

    def health(self):
        exe = Path(self.executable).expanduser() if self.executable else None
        model = Path(self.model).expanduser() if self.model else None
        ok = bool(exe and exe.is_file() and model and model.is_file())
        return {
            "status": "healthy" if ok else "unconfigured",
            "backend": "piper",
            "executable": str(exe) if exe else None,
            "model": str(model) if model else None,
        }

    def synthesize(self, text, output_path=None):
        health = self.health()
        if health["status"] != "healthy":
            raise VoiceUnavailable("Piper não configurado.")
        output = Path(output_path or tempfile.mktemp(suffix=".wav")).resolve()
        proc = subprocess.run(
            [
                str(Path(self.executable).expanduser()),
                "--model", str(Path(self.model).expanduser()),
                "--output_file", str(output),
            ],
            input=str(text), capture_output=True, text=True, timeout=180,
        )
        if proc.returncode != 0 or not output.is_file():
            raise VoiceUnavailable(proc.stderr.strip() or "Piper falhou.")
        return str(output)


class WindowsSapiTTS:
    """Zero-config Windows speech fallback with two native engines.

    System.Speech is preferred because it can synthesize WAV files for the web
    Companion. SAPI.SpVoice is kept as a second direct-speaker fallback because
    it is present on Windows installations where System.Speech voice discovery
    can be incomplete.
    """

    def __init__(self, executable=None, voice=None):
        self.executable = executable or shutil.which("powershell.exe") or shutil.which("powershell")
        self.voice = voice or os.environ.get("JARVIS_WINDOWS_VOICE")
        self._health_cache = None

    def health(self):
        if self._health_cache is not None:
            return dict(self._health_cache)
        ok = os.name == "nt" and bool(self.executable)
        error = None
        engine = None
        installed = []
        if ok:
            script = (
                "$ErrorActionPreference='Stop';"
                "$result=@{systemSpeech=$false;com=$false;voices=@()};"
                "try{Add-Type -AssemblyName System.Speech;"
                "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
                "$result.systemSpeech=$true;"
                "$result.voices=@($s.GetInstalledVoices()|ForEach-Object{$_.VoiceInfo.Name});"
                "$s.Dispose()}catch{};"
                "try{$v=New-Object -ComObject SAPI.SpVoice;"
                "$result.com=$true;"
                "if(-not $result.voices.Count){$result.voices=@($v.GetVoices()|ForEach-Object{$_.GetDescription()})}}catch{};"
                "$result|ConvertTo-Json -Compress"
            )
            try:
                probe = subprocess.run(
                    [self.executable, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
                    capture_output=True, text=True, timeout=15,
                )
                data = json.loads((probe.stdout or "{}").strip() or "{}") if probe.returncode == 0 else {}
                if data.get("systemSpeech"):
                    engine = "system-speech"
                elif data.get("com"):
                    engine = "sapi-com"
                installed = list(data.get("voices") or [])[:20]
                ok = bool(engine)
                if not ok:
                    error = (probe.stderr or probe.stdout or "Nenhum motor SAPI disponível").strip()[:500]
            except Exception as exc:
                ok = False
                error = str(exc)[:500]
        self._health_cache = {
            "status": "healthy" if ok else "unavailable",
            "backend": "windows-sapi",
            "engine": engine,
            "voice": self.voice,
            "installed_voices": installed,
            "executable": self.executable,
            "error": error,
        }
        return dict(self._health_cache)

    @staticmethod
    def _ps_quote(value):
        return str(value).replace("'", "''")

    def _run(self, text, output_path=None, *, speak=False):
        health = self.health()
        if health["status"] != "healthy":
            raise VoiceUnavailable("Voz nativa do Windows indisponível.")
        temp_text = Path(tempfile.mktemp(suffix=".txt")).resolve()
        temp_text.write_text(str(text), encoding="utf-8")
        output = Path(output_path or tempfile.mktemp(suffix=".wav")).resolve() if not speak else None
        text_path = self._ps_quote(temp_text)
        voice = self._ps_quote(self.voice) if self.voice else ""

        if speak and health.get("engine") == "sapi-com":
            select = (
                f"$wanted='{voice}';$v.GetVoices()|Where-Object{{$_.GetDescription() -like ('*'+$wanted+'*')}}|Select-Object -First 1|ForEach-Object{{$v.Voice=$_}};"
                if voice else ""
            )
            script = (
                f"$t=[System.IO.File]::ReadAllText('{text_path}',[System.Text.Encoding]::UTF8);"
                "$v=New-Object -ComObject SAPI.SpVoice;"
                + select + "$null=$v.Speak($t);"
            )
        else:
            if health.get("engine") != "system-speech":
                temp_text.unlink(missing_ok=True)
                raise VoiceUnavailable("System.Speech indisponível para gerar arquivo de áudio.")
            select = (
                f"try{{$s.SelectVoice('{voice}')}}catch{{}};" if voice else
                "try{$s.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Male,[System.Speech.Synthesis.VoiceAge]::Adult,0,[System.Globalization.CultureInfo]::GetCultureInfo('pt-BR'))}catch{};"
            )
            if speak:
                action = "$s.Speak($t);"
            else:
                out_path = self._ps_quote(output)
                action = f"$s.SetOutputToWaveFile('{out_path}');$s.Speak($t);$s.SetOutputToDefaultAudioDevice();"
            script = (
                "Add-Type -AssemblyName System.Speech;"
                f"$t=[System.IO.File]::ReadAllText('{text_path}',[System.Text.Encoding]::UTF8);"
                "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
                + select + action + "$s.Dispose();"
            )
        try:
            proc = subprocess.run(
                [self.executable, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
                capture_output=True, text=True, timeout=240,
            )
        finally:
            temp_text.unlink(missing_ok=True)
        if proc.returncode != 0:
            raise VoiceUnavailable(proc.stderr.strip() or "Voz nativa do Windows falhou.")
        if speak:
            return True
        if not output.is_file() or output.stat().st_size < 44:
            raise VoiceUnavailable("Voz nativa do Windows não gerou áudio.")
        return str(output)

    def synthesize(self, text, output_path=None):
        return self._run(text, output_path, speak=False)

    def speak(self, text):
        return self._run(text, speak=True)


class EdgeNeuralTTS:
    """Free online neural TTS through the public Edge speech endpoint.

    It requires no API key. Jarvis uses a male Brazilian Portuguese voice by
    default and keeps rate/pitch deliberately restrained to create a calm,
    slightly synthetic assistant presence instead of the Windows default voice.
    """

    def __init__(self, voice=None, rate=None, pitch=None, volume=None):
        self.voice = voice or os.environ.get("JARVIS_EDGE_VOICE", "pt-BR-AntonioNeural")
        self.rate = rate or os.environ.get("JARVIS_EDGE_RATE", "-6%")
        self.pitch = pitch or os.environ.get("JARVIS_EDGE_PITCH", "-14Hz")
        self.volume = volume or os.environ.get("JARVIS_EDGE_VOLUME", "+0%")
        self._last_error = None

    def health(self):
        installed = importlib.util.find_spec("edge_tts") is not None
        return {
            "status": "healthy" if installed else "unconfigured",
            "backend": "edge-tts",
            "voice": self.voice if installed else None,
            "rate": self.rate if installed else None,
            "pitch": self.pitch if installed else None,
            "online": True,
            "last_error": self._last_error,
        }

    def synthesize(self, text, output_path=None):
        if self.health()["status"] != "healthy":
            raise VoiceUnavailable("Edge Neural TTS não instalado.")
        output = Path(output_path or tempfile.mktemp(suffix=".mp3")).resolve()
        source = Path(tempfile.mktemp(suffix=".txt")).resolve()
        source.write_text(str(text), encoding="utf-8")
        cmd = [
            sys.executable, "-m", "edge_tts",
            "--file", str(source),
            "--voice", self.voice,
            f"--rate={self.rate}",
            f"--pitch={self.pitch}",
            f"--volume={self.volume}",
            "--write-media", str(output),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        finally:
            source.unlink(missing_ok=True)
        if proc.returncode != 0 or not output.is_file() or output.stat().st_size < 256:
            detail = (proc.stderr or proc.stdout or "Edge Neural TTS falhou.").strip()[:700]
            self._last_error = detail
            output.unlink(missing_ok=True)
            raise VoiceUnavailable(detail)
        self._last_error = None
        return str(output)


class ChatterboxTTS:
    """Optional local Chatterbox/OpenAI-compatible TTS endpoint.

    This adapter keeps the heavy model outside the Jarvis runtime. If a local
    Chatterbox server is configured, Jarvis can use it without changing the
    core environment. No endpoint is enabled by default.
    """

    def __init__(self, base_url=None, voice=None, language=None):
        self.base_url = (base_url or os.environ.get("JARVIS_CHATTERBOX_URL") or "").rstrip("/")
        self.voice = voice or os.environ.get("JARVIS_CHATTERBOX_VOICE", "default")
        self.language = language or os.environ.get("JARVIS_CHATTERBOX_LANGUAGE", "pt")
        self._last_error = None

    def health(self):
        return {
            "status": "healthy" if self.base_url else "unconfigured",
            "backend": "chatterbox",
            "url": self.base_url or None,
            "voice": self.voice if self.base_url else None,
            "language": self.language if self.base_url else None,
            "last_error": self._last_error,
        }

    def synthesize(self, text, output_path=None):
        if not self.base_url:
            raise VoiceUnavailable("Chatterbox local não configurado.")
        output = Path(output_path or tempfile.mktemp(suffix=".mp3")).resolve()
        body = json.dumps({
            "input": str(text),
            "voice": self.voice,
            "language_id": self.language,
            "response_format": "mp3",
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/v1/audio/speech",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "audio/mpeg"},
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                audio = response.read()
        except Exception as exc:
            self._last_error = str(exc)[:700]
            raise VoiceUnavailable(f"Chatterbox indisponível: {exc}") from exc
        if not audio:
            self._last_error = "áudio vazio"
            raise VoiceUnavailable("Chatterbox retornou áudio vazio.")
        output.write_bytes(audio)
        self._last_error = None
        return str(output)


class ElevenLabsTTS:
    """Optional high-quality cloud voice.

    Configuration is intentionally environment-only so credentials never cross
    the local Companion UI:
      JARVIS_ELEVENLABS_API_KEY
      JARVIS_ELEVENLABS_VOICE_ID
      JARVIS_ELEVENLABS_MODEL (optional)
    """

    def __init__(self, api_key=None, voice_id=None, model=None):
        self.api_key = api_key or os.environ.get("JARVIS_ELEVENLABS_API_KEY")
        self.voice_id = voice_id or os.environ.get("JARVIS_ELEVENLABS_VOICE_ID")
        self.model = model or os.environ.get("JARVIS_ELEVENLABS_MODEL", "eleven_multilingual_v2")

    def health(self):
        ok = bool(self.api_key and self.voice_id)
        return {
            "status": "healthy" if ok else "unconfigured",
            "backend": "elevenlabs",
            "voice_id": self.voice_id if ok else None,
            "model": self.model if ok else None,
        }

    def synthesize(self, text, output_path=None):
        if self.health()["status"] != "healthy":
            raise VoiceUnavailable("ElevenLabs não configurado.")
        output = Path(output_path or tempfile.mktemp(suffix=".mp3")).resolve()
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        body = json.dumps({
            "text": str(text),
            "model_id": self.model,
            "voice_settings": {
                "stability": 0.48,
                "similarity_boost": 0.78,
                "style": 0.18,
                "use_speaker_boost": True,
            },
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                audio = response.read()
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="ignore")[:500]
            except Exception:
                pass
            raise VoiceUnavailable(f"ElevenLabs falhou ({exc.code}). {detail}".strip()) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise VoiceUnavailable(f"ElevenLabs indisponível: {exc}") from exc
        if not audio:
            raise VoiceUnavailable("ElevenLabs retornou áudio vazio.")
        output.write_bytes(audio)
        return str(output)


class VoiceService:
    def __init__(self, stt=None, tts=None):
        self.stt = stt or WhisperCppSTT()
        self._explicit_tts = tts
        self.chatterbox = ChatterboxTTS()
        self.edge = EdgeNeuralTTS()
        self.elevenlabs = ElevenLabsTTS()
        self.piper = PiperTTS()
        self.windows = WindowsSapiTTS()
        self.tts = tts or self._select_tts()

    def _candidate_order(self):
        preferred = os.environ.get("JARVIS_TTS_PROVIDER", "auto").strip().lower()
        mapping = {
            "chatterbox": self.chatterbox,
            "edge": self.edge,
            "edge-tts": self.edge,
            "elevenlabs": self.elevenlabs,
            "piper": self.piper,
            "windows": self.windows,
            "windows-sapi": self.windows,
        }
        # Auto favors a configured local premium voice, then the free neural
        # online voice, then offline local fallbacks. ElevenLabs remains
        # supported but is no longer required for a pleasant default voice.
        default = [self.chatterbox, self.edge, self.elevenlabs, self.piper, self.windows]
        first = mapping.get(preferred)
        return ([first] + [x for x in default if x is not first]) if first else default

    def _select_tts(self):
        for candidate in self._candidate_order():
            if candidate.health()["status"] == "healthy":
                return candidate
        return self.piper

    def health(self):
        active = self.tts.health()
        return {
            "stt": self.stt.health(),
            "tts": active,
            "tts_backends": {
                "chatterbox": self.chatterbox.health(),
                "edge_tts": self.edge.health(),
                "elevenlabs": self.elevenlabs.health(),
                "piper": self.piper.health(),
                "windows_sapi": self.windows.health(),
                "browser_fallback": {"status": "available", "backend": "web-speech"},
            },
        }

    def transcribe(self, audio_path):
        return self.stt.transcribe(audio_path)

    def _clean(self, text):
        clean = " ".join(str(text or "").split()).strip()
        if not clean:
            raise VoiceUnavailable("Texto vazio para síntese de voz.")
        return clean[:6000]

    def synthesize(self, text, output_path=None):
        clean = self._clean(text)
        if self._explicit_tts is not None:
            return self._explicit_tts.synthesize(clean, output_path)
        errors = []
        for backend in self._candidate_order():
            if backend.health()["status"] != "healthy":
                continue
            try:
                self.tts = backend
                return backend.synthesize(clean, output_path)
            except VoiceUnavailable as exc:
                errors.append(f"{backend.health().get('backend')}: {exc}")
        raise VoiceUnavailable("; ".join(errors) if errors else "Nenhum TTS local/cloud foi configurado.")

    def diagnostics(self):
        health = self.health()
        return {
            **health,
            "preferred": os.environ.get("JARVIS_TTS_PROVIDER", "auto").strip().lower(),
            "active_backend": health.get("tts", {}).get("backend"),
            "can_speak_native": health.get("tts_backends", {}).get("windows_sapi", {}).get("status") == "healthy",
            "recommended_profile": {
                "provider": "edge-tts",
                "voice": os.environ.get("JARVIS_EDGE_VOICE", "pt-BR-AntonioNeural"),
                "rate": os.environ.get("JARVIS_EDGE_RATE", "-6%"),
                "pitch": os.environ.get("JARVIS_EDGE_PITCH", "-14Hz"),
            },
        }

    def speak_native(self, text):
        """Speak directly through Windows when browser audio cannot play."""
        clean = self._clean(text)
        if self.windows.health()["status"] != "healthy":
            raise VoiceUnavailable("Fallback de voz nativa indisponível.")
        return self.windows.speak(clean)

