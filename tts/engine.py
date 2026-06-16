import asyncio
import io
import os
import subprocess
import tempfile
import threading


class TTS:
    def __init__(self, engine="edge", voice="pt-BR-AntonioNeural", speed=1.0):
        self.engine = engine
        self.voice = voice
        self.speed = speed
        self._kokoro_available = False
        try:
            import kokoro
            self._kokoro_available = True
        except ImportError:
            pass

    def speak(self, text):
        if not text:
            return
        if self.engine == "kokoro" and self._kokoro_available:
            self._speak_kokoro(text)
        elif self.engine == "edge":
            self._speak_edge(text)
        else:
            self._speak_espeak(text)

    def _speak_kokoro(self, text):
        try:
            from kokoro import KPipeline
            import sounddevice as sd
            import numpy as np
            pipeline = KPipeline(lang_code='a')
            generator = pipeline(text, voice=self.voice, speed=self.speed, split_pattern=r"\n+")
            for _, _, audio in generator:
                audio_np = audio.numpy() if hasattr(audio, 'numpy') else audio
                try:
                    sd.play(audio_np, samplerate=24000)
                    sd.wait()
                except Exception as e:
                    print(f"[TTS PLAY WARN] {e}")
        except Exception as e:
            print(f"[TTS KOKORO ERROR] {e}")
            self._speak_espeak(text)

    def _speak_edge(self, text):
        try:
            import edge_tts

            async def _run():
                communicate = edge_tts.Communicate(text, self.voice)
                audio_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                if not audio_data:
                    return
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    tmp_path = f.name
                try:
                    proc = subprocess.run(
                        ["ffmpeg", "-i", "pipe:0", "-f", "wav", "-acodec", "pcm_s16le",
                         "-ar", "24000", "-ac", "1", "-y", tmp_path],
                        input=audio_data, capture_output=True, timeout=30
                    )
                    if proc.returncode == 0:
                        import sounddevice as sd
                        import numpy as np
                        import wave
                        with wave.open(tmp_path, "rb") as wf:
                            frames = wf.readframes(wf.getnframes())
                            audio_np = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                        try:
                            sd.play(audio_np, samplerate=24000)
                            sd.wait()
                        except Exception as e:
                            print(f"[TTS PLAY WARN] {e}")
                    else:
                        subprocess.run(["ffplay", "-nodisp", "-autoexit", "-i", "pipe:0"],
                                       input=audio_data, capture_output=True, timeout=30)
                finally:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass

            asyncio.run(_run())
        except Exception as e:
            print(f"[TTS EDGE ERROR] {e}")
            self._speak_espeak(text)

    def _speak_espeak(self, text):
        try:
            subprocess.run(
                ["espeak-ng", "-v", "pt-br", "-s", "160", text],
                timeout=60,
                capture_output=True
            )
        except Exception as e:
            print(f"[TTS ESPEAK ERROR] {e}")

    def speak_async(self, text):
        t = threading.Thread(target=self.speak, args=(text,), daemon=True)
        t.start()
        return t

    def set_voice(self, voice):
        self.voice = voice

    def set_speed(self, speed):
        self.speed = speed
