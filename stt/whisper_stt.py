import queue
import threading
import time
import numpy as np
import sounddevice as sd


class WhisperSTT:
    def __init__(self, model_name="base", language="pt", device=None, sample_rate=16000):
        self.model_name = model_name
        self.language = language
        self.device = device
        self.sample_rate = sample_rate
        self._model = None
        self._model_lock = threading.Lock()
        self._running = False
        self._q = queue.Queue()
        self._listener_thread = None
        self._error = None

    @property
    def model(self):
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    try:
                        from faster_whisper import WhisperModel
                        self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
                    except Exception as e:
                        self._error = str(e)
                        return None
        return self._model

    @property
    def available(self):
        self.model
        return self._model is not None

    def transcribe_array(self, audio_array):
        m = self.model
        if m is None:
            return ""
        try:
            audio_array = audio_array.astype(np.float32)
            segments, _ = m.transcribe(audio_array, language=self.language)
            return " ".join(seg.text for seg in segments)
        except Exception as e:
            self._error = str(e)
            return ""

    def _callback(self, indata, frames, time, status):
        if status:
            return
        self._q.put(indata.copy())

    def start_listening(self):
        if self._running:
            return
        self._running = True
        self._q = queue.Queue()
        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener_thread.start()

    def _listen_loop(self):
        try:
            with sd.InputStream(
                device=self.device,
                channels=1,
                samplerate=self.sample_rate,
                callback=self._callback,
                blocksize=1024,
            ):
                while self._running:
                    sd.sleep(100)
        except Exception as e:
            print(f"[STT ERROR] {e}")

    def stop_listening(self):
        self._running = False
        if self._listener_thread:
            self._listener_thread.join(timeout=2)

    def get_audio_chunk(self):
        frames = []
        while not self._q.empty():
            frames.append(self._q.get_nowait())
        if not frames:
            return None
        audio = np.concatenate(frames, axis=0).flatten()
        return audio

    def listen_and_transcribe(self, timeout=5.0):
        if not self.available:
            return ""
        self.start_listening()
        frames = []
        start = time.time()
        while time.time() - start < timeout:
            chunk = self.get_audio_chunk()
            if chunk is not None:
                frames.append(chunk)
            time.sleep(0.05)
        self.stop_listening()
        if not frames:
            return ""
        audio = np.concatenate(frames, axis=0).flatten()
        return self.transcribe_array(audio)
