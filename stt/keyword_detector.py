#!/usr/bin/env python3
"""
Wake word detector com Porcupine (real wake word) + Whisper (command STT).
Fallback para detecção via Whisper + regex se Porcupine não tiver AccessKey.
"""
import importlib
import logging
import os
import queue
import re
import threading
import time

import numpy as np
import sounddevice as sd
import webrtcvad
from faster_whisper import WhisperModel

_CHIME_CACHE = None


def _get_chime():
    global _CHIME_CACHE
    if _CHIME_CACHE is not None:
        return _CHIME_CACHE
    sr = 44100
    t = np.linspace(0, 0.15, int(sr * 0.15), False)
    tone = np.sin(2 * np.pi * 880 * t) * 0.3 + np.sin(2 * np.pi * 1320 * t) * 0.15
    _CHIME_CACHE = (tone.astype(np.float32), sr)
    return _CHIME_CACHE


def play_chime(device=None):
    try:
        tone, sr = _get_chime()
        sd.play(tone, sr, device=device)
    except Exception:
        pass

logger = logging.getLogger("keyword_detector")

WAKE_WORDS_FALLBACK = [
    "jarvis", "javis",
    "djárvis", "djarviz", "djarvish",
    "hey jarvis", "ok jarvis",
    "jarviz", "jarbis", "jervis",
    "djávis", "járvis", "djarvis", "d javis",
    "jávez", "já vez", "já há vez",
    "javez", "javeis",
    "járvez", "ja vis", "djavez", "djá vez",
    "járvish", "gárvis", "gárviz",
    "já a vez", "já a vê", "já a vês",
    "já fiz", # variante fonética observada
    "jávis", "djárvis",
]




class PorcupineEngine:
    """Wrapper around pvporcupine for real audio-level wake word detection."""

    def __init__(self, access_key, keyword="jarvis", sensitivity=0.6):
        self.access_key = access_key
        self.keyword = keyword
        self.sensitivity = sensitivity
        self._porcupine = None

    def start(self, sample_rate=16000):
        try:
            import pvporcupine
            self._porcupine = pvporcupine.create(
                access_key=self.access_key,
                keywords=[self.keyword],
                sensitivities=[self.sensitivity],
            )
            logger.info(f"Porcupine ativo: '{self.keyword}' (sr={self._porcupine.sample_rate})")
            return self._porcupine.sample_rate, self._porcupine.frame_length
        except Exception as e:
            logger.error(f"Porcupine falhou: {e}")
            self._porcupine = None
            return None, None

    @property
    def frame_length(self):
        return self._porcupine.frame_length if self._porcupine else None

    @property
    def sample_rate(self):
        return self._porcupine.sample_rate if self._porcupine else None

    def process(self, audio_frame):
        if self._porcupine is None:
            return False
        return self._porcupine.process(audio_frame) >= 0

    def stop(self):
        if self._porcupine:
            self._porcupine.delete()
            self._porcupine = None
        logger.info("Porcupine parado")


class KeywordDetector:
    def __init__(self, sample_rate=16000, device=None, on_command=None, model_name="tiny",
                 porcupine_key=None):
        self.sample_rate = sample_rate
        self.device = device
        self.on_command = on_command
        self.model_name = model_name
        self._running = False
        self._vad = webrtcvad.Vad(2)
        self._model = None
        self._lock = threading.Lock()
        self._porcupine = None

        if porcupine_key:
            self._porcupine = PorcupineEngine(porcupine_key)
            logger.info("Porcupine engine carregado")

    @property
    def model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    self._model = WhisperModel(
                        self.model_name, device="cpu", compute_type="int8"
                    )
        return self._model

    def start(self):
        if self._running:
            return
        self._running = True
        threading.Thread(target=self._loop, daemon=True, name="keyword-detector").start()

    def stop(self):
        self._running = False
        if self._porcupine:
            self._porcupine.stop()

    @property
    def active(self):
        return self._running

    def _loop(self):
        frame_ms = 30
        silence_limit = 1500 // frame_ms
        min_speech = 300 // frame_ms
        max_utterance = 600 // frame_ms

        audio_queue = queue.Queue()
        rec = []
        speech_active = False
        speech_frames = 0
        silence_frames = 0
        frame_count = 0
        after_wake = False
        wake_sample_rate = None
        wake_frame_length = None
        last_transcribe = 0.0

        porcupine_ok = self._porcupine is not None

        if porcupine_ok:
            wake_sample_rate, wake_frame_length = self._porcupine.start(sample_rate=self.sample_rate)
            if wake_sample_rate is None:
                porcupine_ok = False
                logger.warning("Porcupine indisponível, modo energia (energy gate)")

        def callback(indata, frames, t, status):
            if status or not self._running:
                return
            audio_queue.put(indata.copy())

        stream = sd.InputStream(
            device=self.device,
            channels=1,
            samplerate=self.sample_rate,
            callback=callback,
            blocksize=int(self.sample_rate * 0.03),
        )
        stream.start()

        try:
            while self._running:
                if audio_queue.empty():
                    time.sleep(0.005)
                    continue

                chunk = audio_queue.get()

                if not after_wake and porcupine_ok:
                    chunk_16 = (chunk.flatten() * 32767).astype(np.int16)
                    if self._detect_wake(chunk_16, wake_sample_rate, wake_frame_length):
                        logger.info("Wake word detectada pelo Porcupine!")
                        after_wake = True
                        rec = []
                        speech_active = False
                        speech_frames = 0
                        silence_frames = 0
                        frame_count = 0
                        continue

                if not after_wake and not porcupine_ok:
                    chunk_float = chunk.flatten()
                    now = time.time()

                    chunk_16 = (chunk_float * 32767).astype(np.int16)
                    rms = float(np.sqrt(np.mean(chunk_float**2)))
                    is_speech = self._vad.is_speech(chunk_16.tobytes(), self.sample_rate)
                    is_voice = is_speech and rms > 0.01

                    if frame_count % 50 == 0 or is_voice:
                        logger.info(f"RMS={rms:.4f} VAD={is_speech} voice={is_voice}")

                    if not speech_active:
                        if is_voice:
                            speech_active = True
                            rec = [chunk]
                            speech_frames = 1
                            silence_frames = 0
                            frame_count = 1
                    else:
                        rec.append(chunk)
                        frame_count += 1
                        if is_voice:
                            speech_frames += 1
                            silence_frames = 0
                        else:
                            silence_frames += 1
                        total_sec = frame_count * 0.03

                        if silence_frames >= silence_limit or total_sec >= 5.0:
                            if speech_frames >= min_speech and (now - last_transcribe) > 2.0:
                                last_transcribe = now
                                self._transcribe_and_check(rec)
                            rec = []
                            speech_active = False
                            speech_frames = 0
                            silence_frames = 0
                            frame_count = 0
                    continue

                if after_wake:
                    rec.append(chunk)
                    frame_count += 1
                    chunk_16 = (chunk.flatten() * 32767).astype(np.int16)
                    is_speech = self._vad.is_speech(chunk_16.tobytes(), self.sample_rate)

                    if is_speech:
                        speech_frames += 1
                        silence_frames = 0
                    else:
                        silence_frames += 1

                    if (silence_frames >= silence_limit and speech_frames >= min_speech) or frame_count >= max_utterance:
                        if len(rec) >= min_speech:
                            self._transcribe_command(rec)
                        rec = []
                        speech_active = False
                        speech_frames = 0
                        silence_frames = 0
                        frame_count = 0
                        after_wake = False
        finally:
            stream.stop()
            stream.close()
            if self._porcupine:
                self._porcupine.stop()

    def _detect_wake(self, chunk_16, wake_sr, wake_fl):
        if self._porcupine is None:
            return False
        if self.sample_rate != wake_sr:
            ratio = wake_sr / self.sample_rate
            new_len = int(len(chunk_16) * ratio)
            chunk_16 = np.interp(
                np.linspace(0, len(chunk_16) - 1, new_len),
                np.arange(len(chunk_16)), chunk_16
            ).astype(np.int16)
        return self._porcupine.process(chunk_16)

    def _transcribe_command(self, audio_chunks):
        try:
            audio = np.concatenate(audio_chunks, axis=0).flatten()
            audio = self._resample(audio, self.sample_rate)
            segments, _ = self.model.transcribe(audio, language="pt")
            text = " ".join(seg.text for seg in segments).strip()
            if text and self.on_command:
                logger.info(f"Comando: '{text}'")
                self.on_command(text)
            else:
                logger.info("Comando vazio após transcrição")
                if self.on_command:
                    self.on_command("")
        except Exception as e:
            logger.error(f"Erro transcrevendo comando: {e}")

    def _find_wake_word(self, text):
        t = text.lower().strip().rstrip(",.!?;:")
        # Find which wake word matched (try each)
        for ww in WAKE_WORDS_FALLBACK:
            pattern = re.compile(rf'(?:^|[\s,.;:!?]+){re.escape(ww)}(?=[\s,.;:!?]|$)', re.IGNORECASE)
            m = pattern.search(t)
            if m:
                rest = t[m.end():].lstrip().strip(",.!? ").strip()
                return rest
        return None

    def _transcribe_and_check(self, audio_chunks):
        try:
            audio = np.concatenate(audio_chunks, axis=0).flatten()
            audio = self._resample(audio, self.sample_rate)
            segments, _ = self.model.transcribe(audio, language="pt")
            text = " ".join(seg.text for seg in segments).strip()
            logger.info(f"Transcrito: '{text}'")
            if not text:
                return

            rest = self._find_wake_word(text)
            if rest is not None:
                logger.info(f"Wake word detectado em: '{text}' -> comando: '{rest}'")
                if self.on_command:
                    self.on_command(rest)
                return

            # Fallback: if text is short (1-3 words) and contains "j"+"v" sounds → treat as wake
            t_clean = text.lower().strip().rstrip(",.!?;:")
            words = [w for w in re.split(r"[\s,.;:!?]+", t_clean) if w]
            logger.info(f"Sem wake word em: '{text}'")
        except Exception as e:
            logger.error(f"Erro transcrevendo: {e}")

    def _resample(self, audio, orig_rate, target_rate=16000):
        if orig_rate == target_rate:
            return audio
        ratio = target_rate / orig_rate
        new_len = int(len(audio) * ratio)
        return np.interp(np.linspace(0, len(audio) - 1, new_len), np.arange(len(audio)), audio)


class KeywordService:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self._detector = None
        self._enabled = False

    @property
    def enabled(self):
        return self._enabled

    def start(self):
        cfg = self.orchestrator.cfg.get("wake_word", {})
        if not cfg.get("enabled", False):
            self.orchestrator.log("⏸ Palavra-chave desligada na config", "system")
            return

        mic_cfg = self.orchestrator.cfg.get("mic", {})
        device = cfg.get("device") or mic_cfg.get("device")
        model = cfg.get("model", "tiny")
        porcupine_key = os.getenv("PICOVOICE_API_KEY") or cfg.get("picovoice_key")

        self._detector = KeywordDetector(
            sample_rate=16000,
            device=device,
            on_command=self._on_wake,
            model_name=model,
            porcupine_key=porcupine_key,
        )
        self._detector.start()
        self._enabled = True
        engine = "Porcupine" if porcupine_key else "Whisper (fallback)"
        self.orchestrator.log(f"🎤 Palavra-chave ativa: 'Jarvis' ({engine})", "system")

    def stop(self):
        if self._detector:
            self._detector.stop()
            self._detector = None
        self._enabled = False

    def _on_wake(self, command_text):
        o = self.orchestrator
        o.log("🔊 Palavra-chave detectada!", "system")
        play_chime()

        if command_text:
            o.process_text(command_text)
        else:
            o.tts.speak_async("Estou escutando, fale agora.")
