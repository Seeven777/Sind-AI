from __future__ import annotations

from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
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
    """Zero-config Windows speech fallback.

    This intentionally uses the system speech engine only when Jarvis is running
    on Windows. It gives the Companion a dependable spoken fallback even when
    ElevenLabs/Piper are not configured and browser speech is unavailable.
    """

    def __init__(self, executable=None, voice=None):
        self.executable = executable or shutil.which("powershell.exe") or shutil.which("powershell")
        self.voice = voice or os.environ.get("JARVIS_WINDOWS_VOICE")

    def health(self):
        ok = os.name == "nt" and bool(self.executable)
        return {
            "status": "healthy" if ok else "unavailable",
            "backend": "windows-sapi",
            "voice": self.voice,
            "executable": self.executable,
        }

    @staticmethod
    def _ps_quote(value):
        return str(value).replace("'", "''")

    def _run(self, text, output_path=None, *, speak=False):
        if self.health()["status"] != "healthy":
            raise VoiceUnavailable("Voz nativa do Windows indisponível.")
        temp_text = Path(tempfile.mktemp(suffix=".txt")).resolve()
        temp_text.write_text(str(text), encoding="utf-8")
        output = Path(output_path or tempfile.mktemp(suffix=".wav")).resolve() if not speak else None
        text_path = self._ps_quote(temp_text)
        voice = self._ps_quote(self.voice) if self.voice else ""
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
        self.elevenlabs = ElevenLabsTTS()
        self.piper = PiperTTS()
        self.windows = WindowsSapiTTS()
        self.tts = tts or self._select_tts()

    def _select_tts(self):
        preferred = os.environ.get("JARVIS_TTS_PROVIDER", "auto").strip().lower()
        candidates = {
            "elevenlabs": self.elevenlabs,
            "piper": self.piper,
            "windows": self.windows,
            "windows-sapi": self.windows,
        }
        if preferred in candidates and candidates[preferred].health()["status"] == "healthy":
            return candidates[preferred]
        for candidate in (self.elevenlabs, self.piper, self.windows):
            if candidate.health()["status"] == "healthy":
                return candidate
        return self.piper

    def health(self):
        active = self.tts.health()
        return {
            "stt": self.stt.health(),
            "tts": active,
            "tts_backends": {
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
        preferred = os.environ.get("JARVIS_TTS_PROVIDER", "auto").strip().lower()
        ordered = [self.elevenlabs, self.piper, self.windows]
        if preferred == "piper":
            ordered = [self.piper, self.elevenlabs, self.windows]
        elif preferred in {"windows", "windows-sapi"}:
            ordered = [self.windows, self.elevenlabs, self.piper]
        errors = []
        for backend in ordered:
            if backend.health()["status"] != "healthy":
                continue
            try:
                self.tts = backend
                return backend.synthesize(clean, output_path)
            except VoiceUnavailable as exc:
                errors.append(str(exc))
        raise VoiceUnavailable("; ".join(errors) if errors else "Nenhum TTS local/cloud foi configurado.")

    def speak_native(self, text):
        """Speak directly through Windows when browser audio cannot play."""
        clean = self._clean(text)
        if self.windows.health()["status"] != "healthy":
            raise VoiceUnavailable("Fallback de voz nativa indisponível.")
        return self.windows.speak(clean)
