import json
import logging
import os
import queue
import re
import threading
import time

import numpy as np
import sounddevice as sd
import vosk

logger = logging.getLogger("vosk_detector")

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


MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "vosk-model-small-pt-0.3")

# Wake phrase: "ok jarvis" — mas Vosk transcreve foneticamente.
# Usamos matching em dois níveis:
#   1. Palavra longa (≥4 chars) isolada: pega "jarvis", "djarviz" sem "já"/"jazz"
#   2. Bigrama "ok"+"palavra": pega "ok jarvis", "ok já", "ok jazz", "oc jarvis"
#
# Toda partial/final é logada em debug para ajustar as listas.

# Variantes fonéticas do nome "Jarvis" (≥4 chars para evitar falso-positivo)
_NAME_VARIANTS = {
    "jarvis", "djarviz", "djárvis", "járvis",
    "javis", "jávis", "jarbas",
}

# Bigramas "ok" + variante
_PREFIXES_OK = {"ok", "oc", "oque"}  # "oque" = Vosk ouve "ok" como "o que"


def _tokenize(text: str) -> list[str]:
    return text.strip().lower().split()


def _match_wake(text: str) -> bool:
    tokens = _tokenize(text)
    if not tokens:
        return False

    # Nível 1: palavra longa isolada (≥5 chars) — pega "jarvis"
    for t in tokens:
        if len(t) >= 5 and t in _NAME_VARIANTS:
            logger.info(f"🔊 Wake (palavra longa): '{t}'")
            return True

    # Nível 2: bigrama com prefixo "ok"/"oc"/"oque" + variante
    if len(tokens) >= 2:
        for i in range(len(tokens) - 1):
            if tokens[i] in _PREFIXES_OK and tokens[i+1] in _NAME_VARIANTS:
                logger.info(f"🔊 Wake (bigrama): '{tokens[i]} {tokens[i+1]}'")
                return True
            # Também match "ok já" (qualquer palavra ≥2 chars após prefixo)
            if tokens[i] in _PREFIXES_OK and len(tokens[i+1]) >= 2:
                logger.info(f"🔊 Wake (ok+qualquer): '{tokens[i]} {tokens[i+1]}'")
                return True

    return False


def _strip_wake(text: str) -> str:
    """Remove wake prefix from text."""
    tokens = _tokenize(text)
    if not tokens:
        return text

    # Find longest matching wake pattern and remove it
    best_remove = 0
    for i in range(len(tokens)):
        # Single long name variant
        if len(tokens[i]) >= 5 and tokens[i] in _NAME_VARIANTS:
            best_remove = max(best_remove, 1)
        # Bigram "ok" + word
        if i < len(tokens) - 1 and tokens[i] in _PREFIXES_OK:
            best_remove = max(best_remove, 2)

    if best_remove > 0:
        return " ".join(tokens[best_remove:])
    return text


class VoskKeywordDetector:
    def __init__(self, sample_rate=16000, device=None, on_command=None):
        self.sample_rate = sample_rate
        self.device = device
        self.on_command = on_command
        self._running = False
        self._model = None
        self._pending_wake = False
        self._wake_frames = 0
        self._command_frames = 0
        self._silent_frames = 0
        self._command_parts = []

    def start(self):
        if self._running:
            return
        self._running = True
        threading.Thread(target=self._loop, daemon=True, name="vosk-detector").start()

    def stop(self):
        self._running = False

    @property
    def active(self):
        return self._running

    def _load_model(self):
        path = os.path.expanduser(MODEL_PATH)
        if not os.path.isdir(path):
            logger.error(f"Modelo Vosk não encontrado em {path}")
            return None
        return vosk.Model(path)

    def _loop(self):
        model = self._load_model()
        if model is None:
            return

        audio_queue = queue.Queue()

        def callback(indata, frames, t, status):
            if status or not self._running:
                return
            audio_queue.put(indata.copy())

        stream = sd.InputStream(
            device=self.device,
            channels=1,
            samplerate=self.sample_rate,
            callback=callback,
            blocksize=int(self.sample_rate * 0.05),
        )
        stream.start()

        rec = vosk.KaldiRecognizer(model, self.sample_rate)
        rec.SetWords(False)
        rec.SetMaxAlternatives(5)

        logger.info("Vosk: escutando...")
        try:
            while self._running:
                if audio_queue.empty():
                    time.sleep(0.01)
                    continue

                data = audio_queue.get().flatten()
                rms = np.sqrt(np.mean(data ** 2))
                data_16 = (data * 32767).astype(np.int16).tobytes()

                partial = None
                finals = []

                # Get partial result
                try:
                    partial_raw = rec.PartialResult()
                    if partial_raw:
                        pj = json.loads(partial_raw)
                        partial = pj.get("partial", "").strip().lower()
                        if partial:
                            logger.info(f"🎤 Vosk partial: '{partial}'")
                except Exception:
                    pass

                # Feed waveform
                if rec.AcceptWaveform(data_16):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").strip().lower()
                    if text:
                        finals.append(text)
                    for a in result.get("alternatives", []):
                        at = a.get("text", "").strip().lower()
                        if at and at != text:
                            finals.append(at)

                # --- State machine ---
                if self._pending_wake:
                    # We detected wake word, now capture command
                    self._command_frames += 1

                    # Collect partial for command (strip wake word)
                    if partial and partial not in self._command_parts:
                        cleaned_partial = _strip_wake(partial)
                        if cleaned_partial and cleaned_partial != partial:
                            self._command_parts.append(cleaned_partial)
                            logger.info(f"📝 cmd parcial: '{cleaned_partial}'")
                        elif not _match_wake(partial):
                            self._command_parts.append(partial)
                            logger.info(f"📝 cmd parcial: '{partial}'")

                    # Check for silence
                    if rms < 0.008:
                        self._silent_frames += 1
                    else:
                        self._silent_frames = 0

                    # Timeout: silence for ~1s (20 frames) or total ~10s (200 frames)
                    if self._silent_frames >= 20 or self._command_frames >= 200:
                        # Finalize command
                        full_text = " ".join(self._command_parts)
                        # Also get final result
                        try:
                            final_raw = rec.FinalResult()
                            if final_raw:
                                fj = json.loads(final_raw)
                                ft = fj.get("text", "").strip().lower()
                                if ft:
                                    full_text = ft
                        except Exception:
                            pass

                        # Strip wake word from command
                        cleaned = _strip_wake(full_text)
                        logger.info(f"🎯 Comando final: '{cleaned}' (raw: '{full_text}')")
                        if self.on_command and cleaned:
                            self.on_command(cleaned)
                        self._reset_state()
                        # Re-create recognizer for fresh listening
                        rec = vosk.KaldiRecognizer(model, self.sample_rate)
                        rec.SetWords(False)
                        rec.SetMaxAlternatives(5)
                else:
                    # Look for wake word in partial + final
                    wake_detected = False

                    if partial and _match_wake(partial):
                        logger.info(f"🔊 Wake detectada (parcial): '{partial}'")
                        wake_detected = True

                    if not wake_detected:
                        for f in finals:
                            if _match_wake(f):
                                logger.info(f"🔊 Wake detectada (final): '{f}'")
                                wake_detected = True
                                break

                    if wake_detected:
                        self._pending_wake = True
                        self._command_frames = 0
                        self._silent_frames = 0
                        self._command_parts = []
                        play_chime(device=self.device)
                        logger.info("🎵 Chime tocado, ouvindo comando...")
        finally:
            stream.stop()
            stream.close()

    def _reset_state(self):
        self._pending_wake = False
        self._command_frames = 0
        self._silent_frames = 0
        self._command_parts = []


class VoskKeywordService:
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
        self._detector = VoskKeywordDetector(
            sample_rate=16000,
            device=device,
            on_command=self._on_wake,
        )
        self._detector.start()
        self._enabled = True
        self.orchestrator.log("🎤 Vosk ativo: ouvindo...", "system")

    def stop(self):
        if self._detector:
            self._detector.stop()
            self._detector = None
        self._enabled = False

    def _on_wake(self, command_text):
        o = self.orchestrator
        o.log("🔊 Comando recebido!", "system")
        if command_text:
            o.process_text(command_text)
