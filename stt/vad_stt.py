import threading
import time
import numpy as np
import sounddevice as sd
import webrtcvad
from faster_whisper import WhisperModel


class VADSTT:
    WAKE_WORDS = ["jarvis", "javis", "djárvis", "djarviz"]

    def __init__(self, model_name="base", language="pt", device=None, sample_rate=16000):
        self.model_name = model_name
        self.language = language
        self.device = device
        self.sample_rate = sample_rate
        self._vad = webrtcvad.Vad(3)
        self._model = None
        self._model_lock = threading.Lock()
        self._recording = []
        self._error = None

    @property
    def model(self):
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    try:
                        self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
                    except Exception as e:
                        self._error = str(e)
                        return None
        return self._model

    @property
    def available(self):
        self.model
        return self._model is not None

    def _check_wake_word(self, text):
        t = text.lower().strip().rstrip(",.!?;:")
        for ww in self.WAKE_WORDS:
            if t.startswith(ww) and (len(t) == len(ww) or t[len(ww):].lstrip().startswith(" ") or t[len(ww):] in ",.!"):
                rest = t[len(ww):].lstrip().strip(",.!? ").strip()
                return True, rest if rest else None
            if t == ww:
                return True, None
        return False, None

    def _resample(self, audio, orig_rate, target_rate=16000):
        if orig_rate == target_rate:
            return audio
        ratio = target_rate / orig_rate
        new_len = int(len(audio) * ratio)
        return np.interp(np.linspace(0, len(audio) - 1, new_len), np.arange(len(audio)), audio)

    def listen_for_command(self, timeout=8.0):
        return self.listen_for_speech(timeout=timeout, min_speech_ms=200, silence_ms=800)

    def listen_for_speech(self, timeout=10.0, min_speech_ms=400, silence_ms=1200):
        if self._model is None:
            self.model
        frame_ms = 30
        frame_samples = int(self.sample_rate * frame_ms / 1000)
        silence_limit = silence_ms // frame_ms
        min_speech_frames = min_speech_ms // frame_ms

        audio_buffer = []
        vad_buffer = []
        speech_frames = 0
        silence_frames = 0
        speech_detected = False
        started = time.time()

        def callback(indata, frames, t, status):
            if status:
                return
            audio_buffer.append(indata.copy())

        stream = sd.InputStream(
            device=self.device,
            channels=1,
            samplerate=self.sample_rate,
            callback=callback,
            blocksize=frame_samples,
        )
        stream.start()

        try:
            while time.time() - started < timeout:
                if not audio_buffer:
                    time.sleep(0.01)
                    continue

                chunk = audio_buffer.pop(0)
                chunk_16 = (chunk.flatten() * 32767).astype(np.int16)
                is_speech = self._vad.is_speech(chunk_16.tobytes(), self.sample_rate)

                if is_speech and not speech_detected:
                    vad_buffer.extend([False] * len(vad_buffer))
                    vad_buffer.append(True)
                else:
                    vad_buffer.append(is_speech)
                vad_buffer = vad_buffer[-50:]

                recent_speech = sum(vad_buffer) / max(len(vad_buffer), 1)
                if not speech_detected and recent_speech > 0.4:
                    speech_detected = True
                    self._recording = []
                    speech_frames = 0
                    silence_frames = 0
                    self._recording.append(chunk)

                elif speech_detected:
                    self._recording.append(chunk)
                    if is_speech:
                        speech_frames += 1
                        silence_frames = 0
                    else:
                        silence_frames += 1

                    if silence_frames >= silence_limit:
                        if speech_frames >= min_speech_frames:
                            audio = np.concatenate(self._recording, axis=0).flatten()
                            audio = self._resample(audio, self.sample_rate)
                            try:
                                segments, _ = self._model.transcribe(audio, language=self.language)
                                text = " ".join(seg.text for seg in segments)
                                return text.strip()
                            except Exception as e:
                                self._error = str(e)
                                return ""
                        speech_detected = False
                        self._recording = []
                        speech_frames = 0
                        silence_frames = 0

                if len(audio_buffer) > 100:
                    audio_buffer.clear()
        finally:
            stream.stop()
            stream.close()

        return ""
