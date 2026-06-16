import numpy as np
import sounddevice as sd
from kokoro import KPipeline


class KokoroTTS:
    def __init__(self, voice="af_heart", speed=1.0, lang_code='a'):
        self.voice = voice
        self.speed = speed
        self.lang_code = lang_code
        self._pipeline = None

    @property
    def pipeline(self):
        if self._pipeline is None:
            self._pipeline = KPipeline(lang_code=self.lang_code)
        return self._pipeline

    def speak(self, text):
        if not text:
            return
        try:
            generator = self.pipeline(
                text, voice=self.voice,
                speed=self.speed, split_pattern=r"\n+"
            )
            for _, _, audio in generator:
                audio_np = audio.numpy() if hasattr(audio, 'numpy') else audio
                sd.play(audio_np, samplerate=24000)
                sd.wait()
        except Exception as e:
            print(f"[TTS ERROR] {e}")

    def speak_async(self, text):
        import threading
        t = threading.Thread(target=self.speak, args=(text,), daemon=True)
        t.start()
        return t

    def set_voice(self, voice):
        self.voice = voice

    def set_speed(self, speed):
        self.speed = speed
