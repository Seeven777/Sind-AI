from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import tempfile


class VoiceUnavailable(RuntimeError):
    pass


class WhisperCppSTT:
    def __init__(self,executable=None,model=None):
        self.executable=executable or os.environ.get('JARVIS_WHISPER_CPP')
        self.model=model or os.environ.get('JARVIS_WHISPER_MODEL')

    def health(self):
        exe=Path(self.executable).expanduser() if self.executable else None
        model=Path(self.model).expanduser() if self.model else None
        ok=bool(exe and exe.is_file() and model and model.is_file())
        return {
            'status':'healthy' if ok else 'unconfigured',
            'backend':'whisper.cpp',
            'executable':str(exe) if exe else None,
            'model':str(model) if model else None,
        }

    def transcribe(self,audio_path):
        health=self.health()
        if health['status']!='healthy':
            raise VoiceUnavailable('whisper.cpp não configurado.')
        proc=subprocess.run(
            [
                str(Path(self.executable).expanduser()),
                '-m',str(Path(self.model).expanduser()),
                '-f',str(Path(audio_path).resolve()),
                '-nt','-np',
            ],
            capture_output=True,text=True,timeout=180
        )
        if proc.returncode!=0:
            raise VoiceUnavailable(proc.stderr.strip() or 'whisper.cpp falhou.')
        return proc.stdout.strip()


class PiperTTS:
    def __init__(self,executable=None,model=None):
        self.executable=executable or os.environ.get('JARVIS_PIPER')
        self.model=model or os.environ.get('JARVIS_PIPER_MODEL')

    def health(self):
        exe=Path(self.executable).expanduser() if self.executable else None
        model=Path(self.model).expanduser() if self.model else None
        ok=bool(exe and exe.is_file() and model and model.is_file())
        return {
            'status':'healthy' if ok else 'unconfigured',
            'backend':'piper',
            'executable':str(exe) if exe else None,
            'model':str(model) if model else None,
        }

    def synthesize(self,text,output_path=None):
        health=self.health()
        if health['status']!='healthy':
            raise VoiceUnavailable('Piper não configurado.')
        output=Path(output_path or tempfile.mktemp(suffix='.wav')).resolve()
        proc=subprocess.run(
            [
                str(Path(self.executable).expanduser()),
                '--model',str(Path(self.model).expanduser()),
                '--output_file',str(output),
            ],
            input=str(text),capture_output=True,text=True,timeout=180
        )
        if proc.returncode!=0 or not output.is_file():
            raise VoiceUnavailable(proc.stderr.strip() or 'Piper falhou.')
        return str(output)


class VoiceService:
    def __init__(self,stt=None,tts=None):
        self.stt=stt or WhisperCppSTT()
        self.tts=tts or PiperTTS()

    def health(self):
        return {'stt':self.stt.health(),'tts':self.tts.health()}

    def transcribe(self,audio_path):
        return self.stt.transcribe(audio_path)

    def synthesize(self,text,output_path=None):
        return self.tts.synthesize(text,output_path)
