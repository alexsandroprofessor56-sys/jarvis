#!/bin/bash
# Launcher para JARVIS Voice Daemon
# Força backend ALSA antes de importar sounddevice

export PYTHONPATH=/home/alexkali/jarvis
export NVIDIA_API_KEY=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
export DISPLAY=:0
export SDL_AUDIODRIVER=alsa
export PA_ALSA_PLUGHW=1
export PULSE_SERVER=
export AUDIODEV=hw:0,0

cd /home/alexkali/jarvis
exec /usr/bin/python3 /home/alexkali/jarvis/jarvis_daemon.py
