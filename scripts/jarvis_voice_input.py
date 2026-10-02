"""One-shot local microphone capture for the PySide habitat.

The process emits newline-delimited JSON so QProcess can forward listening
levels and the final Faster-Whisper transcript without blocking the UI thread.
"""

from __future__ import annotations

import io
import json
import struct
import sys
import wave


SAMPLE_RATE = 16_000
CHUNK = 1_024
SILENCE_THRESHOLD = 500
SILENCE_SECONDS = 1.25
STARTUP_SILENCE_SECONDS = 7.0
MAX_SECONDS = 30.0


def emit(event: str, **payload: object) -> None:
    print(json.dumps({"event": event, **payload}, ensure_ascii=False), flush=True)


def rms(data: bytes) -> float:
    count = len(data) // 2
    if not count:
        return 0.0
    samples = struct.unpack(f"{count}h", data[: count * 2])
    return (sum(value * value for value in samples) / count) ** 0.5


def wav_bytes(frames: list[bytes]) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(SAMPLE_RATE)
        target.writeframes(b"".join(frames))
    return output.getvalue()


def record() -> tuple[bytes, bool]:
    import sounddevice as sd

    per_second = SAMPLE_RATE / CHUNK
    silence_limit = int(SILENCE_SECONDS * per_second)
    startup_limit = int(STARTUP_SILENCE_SECONDS * per_second)
    max_chunks = int(MAX_SECONDS * per_second)
    frames: list[bytes] = []
    silence = 0
    heard_speech = False

    emit("listening")
    with sd.RawInputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=CHUNK
    ) as stream:
        for index in range(max_chunks):
            raw, overflowed = stream.read(CHUNK)
            data = bytes(raw)
            frames.append(data)
            level = rms(data)
            if index % 2 == 0:
                emit("level", value=min(1.0, level / 6000.0), overflow=bool(overflowed))
            if level > SILENCE_THRESHOLD:
                heard_speech = True
                silence = 0
            elif not heard_speech and len(frames) >= startup_limit:
                break
            elif heard_speech:
                silence += 1
                if silence >= silence_limit:
                    break
    return wav_bytes(frames), heard_speech


def main() -> int:
    try:
        audio, heard_speech = record()
        emit("level", value=0.0)
        if not heard_speech:
            emit("empty", message="Nenhuma fala foi detectada.")
            return 0

        emit("transcribing")
        from openjarvis.cli._voice_chat import VoiceSession

        backend = VoiceSession().get_stt_backend()
        if backend is None:
            raise RuntimeError("O transcritor local não está disponível.")
        result = backend.transcribe(audio, format="wav", language="pt")
        text = result.text.strip()
        if text:
            emit("transcript", text=text)
        else:
            emit("empty", message="Não consegui reconhecer a fala.")
        return 0
    except Exception as exc:
        emit("error", message=str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
