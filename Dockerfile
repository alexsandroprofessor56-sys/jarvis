# JARVIS Dockerfile - Container completo com suporte a GUI e áudio
FROM ubuntu:22.04

# Evita prompts interativos
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Variáveis de build
ARG USERNAME=jarvis
ARG USER_UID=1000
ARG USER_GID=1000

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Python & build
    python3 python3-pip python3-venv python3-dev \
    build-essential cmake pkg-config \
    # Áudio
    ffmpeg espeak-ng libespeak-ng1 portaudio19-dev libportaudio2 libportaudiocpp0 \
    libasound2-dev libsndfile1-dev pulseaudio pulseaudio-utils \
    # Visão & OCR
    tesseract-ocr tesseract-ocr-por libtesseract-dev \
    poppler-utils \
    libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libasound2 \
    # OpenCV
    libopencv-dev python3-opencv \
    # Utilitários
    git curl wget ca-certificates \
    sqlite3 libsqlite3-dev \
    # Sistema
    brightnessctl playerctl pamixer \
    wmctrl xdotool \
    # Rede
    nmap net-tools iproute2 \
    # Bluetooth
    bluetooth bluez libbluetooth-dev \
    # VPN
    wireguard-tools \
    # Imagem
    libjpeg-dev libpng-dev libtiff-dev libwebp-dev \
    libfreetype6-dev liblcms2-dev libharfbuzz-dev libfribidi-dev \
    # X11 para GUI
    libxcb1-dev libx11-dev libxext-dev libxrender-dev libxi-dev libxtst-dev \
    # Limpeza
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Cria usuário não-root
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m -s /bin/bash $USERNAME \
    && usermod -aG audio,video,plugdev,bluetooth,docker $USERNAME

# Diretório de trabalho
WORKDIR /home/$USERNAME/jarvis

# Copia requirements primeiro (cache de layers)
COPY requirements.txt .

# Instala dependências Python como usuário
USER $USERNAME
RUN python3 -m venv venv \
    && /home/$USERNAME/jarvis/venv/bin/pip install --upgrade pip setuptools wheel \
    && /home/$USERNAME/jarvis/venv/bin/pip install -r requirements.txt \
    # Extras que podem falhar silenciosamente
    && /home/$USERNAME/jarvis/venv/bin/pip install edge-tts kokoro faster-whisper 2>/dev/null || true \
    && /home/$USERNAME/jarvis/venv/bin/pip install playwright 2>/dev/null && /home/$USERNAME/jarvis/venv/bin/playwright install chromium 2>/dev/null || true \
    && /home/$USERNAME/jarvis/venv/bin/pip install chromadb sentence-transformers 2>/dev/null || true \
    && /home/$USERNAME/jarvis/venv/bin/pip install opencv-python opencv-contrib-python 2>/dev/null || true \
    && /home/$USERNAME/jarvis/venv/bin/pip install apscheduler watchdog 2>/dev/null || true \
    && /home/$USERNAME/jarvis/venv/bin/pip install pyannote-audio speechbrain 2>/dev/null || true \
    && /home/$USERNAME/jarvis/venv/bin/pip install docker 2>/dev/null || true \
    && /home/$USERNAME/jarvis/venv/bin/pip install googletrans==4.0.0-rc1 2>/dev/null || true \
    && /home/$USERNAME/jarvis/venv/bin/pip install deep-translator qrcode[pil] pyttsx3 paramiko 2>/dev/null || true

# Copia código fonte
USER root
COPY --chown=$USERNAME:$USERNAME . .

# Diretórios de dados
USER $USERNAME
RUN mkdir -p ~/.jarvis/{memory,faces,plugins,icons,notes,chroma_db,logs} \
    && mkdir -p ~/Pictures ~/Downloads/jarvis_downloads

# Configuração de áudio para PulseAudio
ENV PULSE_SERVER=unix:/run/user/1000/pulse/native
ENV PULSE_COOKIE=/run/user/1000/pulse/cookie

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /home/jarvis/jarvis/venv/bin/python /home/jarvis/jarvis/health_check.py || exit 1

# Entrypoint
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

# Comando padrão: UI gráfica
CMD ["python", "main.py"]

# Labels
LABEL maintainer="JARVIS Team"
LABEL description="JARVIS - Just A Rather Very Intelligent System"
LABEL version="1.0"