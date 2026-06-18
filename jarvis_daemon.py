#!/usr/bin/env python3
"""
JARVIS Daemon — Assistente de voz unificado com wake word "jarvis"
Roda em background, escuta continuamente, processa comando por voz.
Modo dual: online (NVIDIA Hermes) · local (Ollama) — troca por comando de voz.

DELEGAÇÃO: O wake word detection é feito pelo KeywordService dentro do
Orchestrator (stt/keyword_detector.py). Este daemon é apenas um wrapper
que inicia o Orchestrator e mantém o processo vivo para o systemd.
"""
import os
import sys
import signal
import time
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.orchestrator import Orchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("jarvis_daemon")


class JarvisDaemon:
    def __init__(self):
        self.orchestrator = None
        self.running = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        logger.info(f"Sinal {signum} recebido, encerrando...")
        self.stop()

    def start(self):
        logger.info("Iniciando JARVIS Daemon...")
        self.orchestrator = Orchestrator()
        self.orchestrator.set_callbacks(
            on_log=self._on_log,
            on_state=self._on_state_change
        )
        self.orchestrator.start()
        logger.info("Orchestrator iniciado — wake word detection delegado")
        self.running = True
        logger.info("JARVIS Daemon rodando em background.")
        return True

    def _on_log(self, msg, tag):
        if tag == "error":
            logger.error(msg)
        elif tag == "system":
            logger.info(msg)
        else:
            logger.debug(f"[{tag}] {msg}")

    def _on_state_change(self, state):
        logger.debug(f"Estado: {state}")

    def stop(self):
        logger.info("Parando JARVIS Daemon...")
        self.running = False
        if self.orchestrator:
            self.orchestrator.stop()
        logger.info("JARVIS Daemon parado")


def main():
    daemon = JarvisDaemon()
    if daemon.start():
        try:
            while daemon.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            daemon.stop()
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
