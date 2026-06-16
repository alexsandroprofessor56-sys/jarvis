import os
import tempfile
import numpy as np


class SpeakerDiarization:
    def __init__(self):
        self._pipeline = None
        self._known_speakers = {}
        self._data_dir = os.path.expanduser("~/.jarvis/speakers")
        os.makedirs(self._data_dir, exist_ok=True)

    @property
    def pipeline(self):
        if self._pipeline is None:
            try:
                from pyannote.audio import Pipeline
                self._pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=None
                )
            except Exception:
                pass
        return self._pipeline

    def diarize(self, audio_path):
        if not self.pipeline:
            return []
        try:
            diarization = self.pipeline(audio_path)
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append({
                    "speaker": speaker,
                    "start": turn.start,
                    "end": turn.end,
                    "duration": turn.end - turn.start
                })
            return segments
        except Exception as e:
            return [{"error": str(e)}]

    def register_speaker(self, name, audio_path):
        import shutil
        speaker_dir = os.path.join(self._data_dir, name)
        os.makedirs(speaker_dir, exist_ok=True)
        dest = os.path.join(speaker_dir, "sample.wav")
        shutil.copy2(audio_path, dest)
        self._known_speakers[name] = dest
        return f"Falante '{name}' registrado"

    def identify_speaker(self, audio_path):
        segments = self.diarize(audio_path)
        if not segments:
            return "desconhecido"
        speakers = set(s["speaker"] for s in segments)
        return ", ".join(sorted(speakers)) or "desconhecido"
