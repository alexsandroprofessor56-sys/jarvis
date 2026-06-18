import threading
import time
import queue
import numpy as np
import sounddevice as sd
import webrtcvad
from faster_whisper import WhisperModel


class VADSTT:
    WAKE_WORDS = [
        "jarvis", "javis", "djárvis", "djarviz", "djarvish",
        "hey jarvis", "ok jarvis", "jarvis",
        "jarviz", "jarbis", "jervis", "djávis", "járvis",
        "djarvis", "d javis", "djarv",
    ]

    def __init__(self, model_name="base", language="pt", device=None, sample_rate=48000):
        self.model_name = model_name
        self.language = language
        self.device = device
        self.sample_rate = sample_rate
        self.vad_sample_rate = 16000 if sample_rate not in (8000, 16000, 32000, 48000) else sample_rate
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
            # Match exato no início OU após espaço/pontuação (boundary)
            import re
            pattern = rf'(^|\s|[,.;:]){re.escape(ww)}(?=\s|$|[,.;:?!])'
            if re.search(pattern, t):
                # Extrai comando após a wake word
                idx = t.find(ww)
                if idx >= 0:
                    rest = t[idx + len(ww):].lstrip().strip(",.!? ").strip()
                    return True, rest if rest else None
        return False, None

    def _resample(self, audio, orig_rate, target_rate=16000):
        if orig_rate == target_rate:
            return audio
        ratio = target_rate / orig_rate
        new_len = int(len(audio) * ratio)
        return np.interp(np.linspace(0, len(audio) - 1, new_len), np.arange(len(audio)), audio)

    def start_capture(self):
        self.model
        self._capture_buffer = []
        self._capture_stream = sd.InputStream(
            device=self.device,
            channels=1,
            samplerate=self.sample_rate,
            callback=lambda indata, frames, t, status: (
                self._capture_buffer.append(indata.copy()) if not status else None
            ),
            blocksize=int(self.sample_rate * 0.03),
        )
        self._capture_stream.start()

    def stop_and_transcribe(self):
        if self._capture_stream:
            self._capture_stream.stop()
            self._capture_stream.close()
            self._capture_stream = None
        if not self._capture_buffer:
            return ""
        audio = np.concatenate(self._capture_buffer, axis=0).flatten()
        self._capture_buffer = []
        audio = self._resample(audio, self.sample_rate)
        try:
            segments, _ = self._model.transcribe(audio, language=self.language)
            return " ".join(seg.text for seg in segments).strip()
        except Exception as e:
            self._error = str(e)
            return ""

    def listen_for_command(self, timeout=8.0):
        return self.listen_for_speech(timeout=timeout, min_speech_ms=200, silence_ms=800)

    def listen_for_speech(self, timeout=10.0, min_speech_ms=400, silence_ms=1200):
        if self._model is None:
            self.model
        frame_ms = 30
        vad_rate = self.vad_sample_rate
        frame_samples = int(vad_rate * frame_ms / 1000)
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
            blocksize=int(self.sample_rate * 0.03),
        )
        stream.start()

        try:
            while time.time() - started < timeout:
                if not audio_buffer:
                    time.sleep(0.01)
                    continue

                chunk = audio_buffer.pop(0)
                # Resample for VAD
                if self.sample_rate != vad_rate:
                    ratio = vad_rate / self.sample_rate
                    new_len = int(len(chunk.flatten()) * ratio)
                    vad_chunk = np.interp(
                        np.linspace(0, len(chunk.flatten()) - 1, new_len),
                        np.arange(len(chunk.flatten())),
                        chunk.flatten()
                    )
                else:
                    vad_chunk = chunk.flatten()
                chunk_16 = (vad_chunk * 32767).astype(np.int16)
                is_speech = self._vad.is_speech(chunk_16.tobytes(), vad_rate)

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

    def listen_continuous(self, min_speech_ms=150, silence_ms=500, max_utterance_s=10):
        """
        Generator que escuta continuamente com um único stream persistente.
        Yields transcrições conforme detectadas.
        Parâmetros ajustados para resposta rápida a comandos.
        """
        if self._model is None:
            self.model
        frame_ms = 30
        vad_rate = self.vad_sample_rate
        silence_limit = max(3, silence_ms // frame_ms)
        min_speech_frames = max(2, min_speech_ms // frame_ms)
        max_frames = int(max_utterance_s * 1000 / frame_ms)

        audio_queue = queue.Queue()
        speech_frames = 0
        silence_frames = 0
        speech_detected = False
        recording = []
        frame_count = 0

        def callback(indata, frames, t, status):
            if status:
                return
            audio_queue.put(indata.copy())

        stream = sd.InputStream(
            device=self.device,
            channels=1,
            samplerate=self.sample_rate,
            callback=callback,
            blocksize=int(self.sample_rate * 0.03),
            latency='low',
        )
        stream.start()

        try:
            while True:
                try:
                    chunk = audio_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                if self.sample_rate != vad_rate:
                    ratio = vad_rate / self.sample_rate
                    new_len = int(len(chunk.flatten()) * ratio)
                    vad_chunk = np.interp(
                        np.linspace(0, len(chunk.flatten()) - 1, new_len),
                        np.arange(len(chunk.flatten())),
                        chunk.flatten()
                    )
                else:
                    vad_chunk = chunk.flatten()
                
                chunk_16 = (vad_chunk * 32767).astype(np.int16)
                is_speech = self._vad.is_speech(chunk_16.tobytes(), vad_rate)

                if is_speech and not speech_detected:
                    speech_detected = True
                    recording = []
                    speech_frames = 0
                    silence_frames = 0
                    frame_count = 0
                    self._recording_start = time.time()

                if speech_detected:
                    recording.append(chunk)
                    frame_count += 1
                    if is_speech:
                        speech_frames += 1
                        silence_frames = 0
                    else:
                        silence_frames += 1

                    if silence_frames >= silence_limit or frame_count >= max_frames:
                        if len(recording) >= min_speech_frames:
                            audio = np.concatenate(recording, axis=0).flatten()
                            audio = self._resample(audio, self.sample_rate)
                            try:
                                segments, _ = self._model.transcribe(audio, language=self.language)
                                text = " ".join(seg.text for seg in segments).strip()
                                if text:
                                    yield text
                            except Exception as e:
                                self._error = str(e)
                        recording = []
                        speech_frames = 0
                        silence_frames = 0
                        frame_count = 0
                        speech_detected = False
        finally:
            stream.stop()
            stream.close()