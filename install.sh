#!/bin/bash
# JARVIS - Script de Instalação Completa
# Instala todas as dependências e configura o ambiente
# Uso: chmod +x install.sh && ./install.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

JARVIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.jarvis"

log() { echo -e "${GREEN}[JARVIS]${NC} $1"; }
warn() { echo -e "${YELLOW}[AVISO]${NC} $1"; }
error() { echo -e "${RED}[ERRO]${NC} $1"; }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }

check_command() {
    command -v "$1" >/dev/null 2>&1
}

install_system_deps() {
    log "Instalando dependências do sistema..."

    if check_command apt; then
        sudo apt update
        sudo apt install -y \
            python3 python3-pip python3-venv python3-dev \
            ffmpeg espeak-ng libespeak-ng1 \
            portaudio19-dev libportaudio2 libportaudiocpp0 \
            libasound2-dev libsndfile1-dev portaudio19-dev python3-pyaudio \
            mss-tools \
            tesseract-ocr tesseract-ocr-por \
            poppler-utils \
            libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
            libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
            libxfixes3 libxrandr2 libgbm1 libasound2 \
            git curl wget unzip \
            build-essential cmake pkg-config \
            libopencv-dev python3-opencv \
            brightnessctl playerctl pamixer \
            wmctrl xdotool \
            docker.io docker-compose \
            sqlite3 libsqlite3-dev \
            libjpeg-dev libpng-dev libtiff-dev \
            libfreetype6-dev liblcms2-dev libwebp-dev \
            libharfbuzz-dev libfribidi-dev \
            libxcb1-dev libx11-dev libxext-dev libxrender-dev \
            libxi-dev libxtst-dev \
            2>/dev/null || warn "Alguns pacotes do sistema falharam (continuando...)"
    elif check_command pacman; then
        sudo pacman -S --needed --noconfirm \
            python python-pip python-virtualenv \
            ffmpeg espeak-ng \
            portaudio python-pyaudio \
            tesseract tesseract-data-por \
            poppler \
            opencv python-opencv \
            brightnessctl playerctl pamixer \
            wmctrl xdotool \
            docker docker-compose \
            sqlite3 \
            base-devel cmake pkg-config \
            unzip \
            2>/dev/null || warn "Alguns pacotes do sistema falharam"
    elif check_command dnf; then
        sudo dnf install -y \
            python3 python3-pip python3-virtualenv \
            ffmpeg espeak-ng \
            portaudio-devel \
            tesseract tesseract-langpack-por \
            poppler-utils \
            opencv-python3 \
            brightnessctl playerctl pamixer \
            wmctrl xdotool \
            docker docker-compose \
            sqlite3 sqlite-devel \
            gcc gcc-c++ make cmake pkgconfig \
            unzip \
            2>/dev/null || warn "Alguns pacotes do sistema falharam"
    else
        warn "Gerenciador de pacotes não reconhecido. Instale manualmente:"
        echo "  python3, pip, ffmpeg, espeak-ng, portaudio, tesseract-ocr, poppler, opencv"
        echo "  brightnessctl, playerctl, pamixer, wmctrl, xdotool"
        echo "  docker, sqlite3, build tools, unzip"
    fi
}

setup_python_env() {
    log "Configurando ambiente Python..."

    cd "$JARVIS_DIR"

    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log "Virtualenv criado em $JARVIS_DIR/venv"
    fi

    source venv/bin/activate
    pip install --upgrade pip setuptools wheel

    log "Instalando dependências Python principais..."
    pip install -r requirements.txt

    log "Instalando dependências Python opcionais..."
    pip install kokoro faster-whisper 2>/dev/null || warn "kokoro/faster-whisper opcionais"
    pip install playwright 2>/dev/null && playwright install chromium 2>/dev/null || warn "Playwright opcional"
    pip install chromadb sentence-transformers 2>/dev/null || warn "ChromaDB opcional"
    pip install opencv-python opencv-contrib-python 2>/dev/null || warn "OpenCV contrib opcional"
    pip install apscheduler watchdog 2>/dev/null || warn "Scheduler opcional"
    pip install pyannote-audio speechbrain 2>/dev/null || warn "Audio avançado opcional"
    pip install docker 2>/dev/null || warn "Docker SDK opcional"
    pip install googletrans==4.0.0-rc1 2>/dev/null || warn "Tradutor opcional"
    pip install deep-translator qrcode[pil] pyttsx3 paramiko 2>/dev/null || warn "Extras opcionais"
}

setup_vosk_model() {
    log "Baixando modelo Vosk para wake word..."

    local MODEL_DIR="$JARVIS_DIR/models"
    local MODEL_NAME="vosk-model-small-pt-0.3"
    local MODEL_URL="https://alphacephei.com/vosk/models/${MODEL_NAME}.zip"

    mkdir -p "$MODEL_DIR"

    if [ -d "$MODEL_DIR/$MODEL_NAME" ]; then
        info "Modelo Vosk PT-BR já existe em $MODEL_DIR/$MODEL_NAME"
        return 0
    fi

    log "Baixando modelo Vosk PT-BR (42MB)..."
    wget -q --show-progress "$MODEL_URL" -O /tmp/vosk-model.zip

    log "Extraindo modelo..."
    unzip -q /tmp/vosk-model.zip -d "$MODEL_DIR"
    rm -f /tmp/vosk-model.zip

    if [ -d "$MODEL_DIR/$MODEL_NAME" ]; then
        log "Modelo Vosk PT-BR instalado em $MODEL_DIR/$MODEL_NAME"
    else
        warn "Falha ao extrair modelo Vosk. Baixe manualmente:"
        echo "  wget $MODEL_URL"
        echo "  unzip ${MODEL_NAME}.zip -d $MODEL_DIR"
    fi
}

setup_config() {
    log "Configurando diretórios e arquivos..."

    mkdir -p "$CONFIG_DIR"/{memory,faces,plugins,icons,notes,clipboard,logs}
    mkdir -p "$CONFIG_DIR"/chroma_db
    mkdir -p "$HOME/Pictures"
    mkdir -p "$HOME/Downloads/jarvis_downloads"

    # Cria config padrao via Python (garante JSON valido)
    if [ ! -f "$CONFIG_DIR/config.json" ]; then
        cd "$JARVIS_DIR"
        source venv/bin/activate
        python3 -c "
import sys
sys.path.insert(0, '.')
from config.settings import save, DEFAULT_CONFIG
save(DEFAULT_CONFIG)
print('Configuracao padrao criada em $CONFIG_DIR/config.json')
"
    else
        info "Config já existe em $CONFIG_DIR/config.json"
    fi

    # Face padrao
    if [ ! -f "$CONFIG_DIR/face.png" ]; then
        info "Nenhuma face.png encontrada. Coloque uma imagem 200x200 em $CONFIG_DIR/face.png para personalizar."
    fi
}

setup_playwright() {
    log "Configurando Playwright..."
    source "$JARVIS_DIR/venv/bin/activate"
    playwright install chromium 2>/dev/null || warn "Playwright install falhou (precisa de dependencias do sistema)"
    playwright install-deps chromium 2>/dev/null || true
}

setup_ollama() {
    log "Verificando Ollama (LLM local)..."
    if ! check_command ollama; then
        warn "Ollama nao instalado. Instalando automaticamente..."
        curl -fsSL https://ollama.ai/install.sh | sh
    fi

    info "Ollama encontrado. Baixando modelos..."

    # LLM local principal
    log "Baixando qwen2.5:3b (LLM local, ~1.8GB)..."
    ollama pull qwen2.5:3b 2>&1 | tail -3

    # Modelo de visao (opcional)
    if ollama list 2>/dev/null | grep -q moondream; then
        info "Moondream ja disponivel"
    else
        info "Deseja baixar moondream (visao computacional, ~1.7GB)? [s/N]"
        read -r BAJAR_MOONDREAM
        if [[ "$BAJAR_MOONDREAM" =~ ^[Ss]$ ]]; then
            log "Baixando moondream (visao)..."
            ollama pull moondream 2>&1 | tail -3
        else
            info "Moondream nao baixado. Para baixar depois: ollama pull moondream"
        fi
    fi
}

setup_hermes() {
    log "Configurando Hermes Tool Proxy (integração com ferramentas avançadas)..."

    local HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
    local HERMES_AGENT="$HERMES_HOME/hermes-agent"

    # Verifica se Hermes ja esta instalado
    if [ -d "$HERMES_AGENT" ] && [ -f "$HERMES_AGENT/setup.py" ]; then
        info "Hermes Agent ja instalado em $HERMES_AGENT"
    else
        warn "Hermes Agent nao encontrado."
        info "Para integrar com ferramentas avancadas (192+ ferramentas), instale o Hermes manualmente:"
        echo "  git clone <hermes-repo> $HERMES_AGENT"
        echo "  cd $HERMES_AGENT && pip install -e ."
        echo ""
        info "Ou ignore esta etapa — o JARVIS funciona com as ferramentas internas."
        return 0
    fi

    # Copia tools Jarvis para o Hermes (se Hermes estiver instalado)
    local JARVIS_TOOLS_SRC="$JARVIS_DIR/tools/jarvis_system.py"
    local JARVIS_TOOLS_DST="$HERMES_AGENT/tools/jarvis_system.py"

    if [ -f "$JARVIS_TOOLS_SRC" ]; then
        mkdir -p "$HERMES_AGENT/tools"
        if [ ! -f "$JARVIS_TOOLS_DST" ]; then
            cp "$JARVIS_TOOLS_SRC" "$JARVIS_TOOLS_DST"
            log "Ferramentas Jarvis copiadas para $JARVIS_TOOLS_DST"
        fi
    fi

    # Instala dependencias do Hermes
    if [ -f "$HERMES_AGENT/requirements.txt" ]; then
        log "Instalando dependencias do Hermes..."
        pip install -r "$HERMES_AGENT/requirements.txt" 2>/dev/null || warn "Algumas deps do Hermes falharam"
    fi

    # Cria systemd para Hermes Tool Proxy
    local HERMES_SERVICE="/etc/systemd/system/hermes-tool-proxy.service"
    if [ ! -f "$HERMES_SERVICE" ]; then
        info "Criando systemd service para Hermes Tool Proxy..."
        sudo bash -c "cat > $HERMES_SERVICE" <<EOF
[Unit]
Description=Hermes Tool Proxy (JARVIS bridge)
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$JARVIS_DIR
ExecStart=$JARVIS_DIR/venv/bin/python $JARVIS_DIR/hermes_tool_proxy.py
Restart=on-failure
RestartSec=5
Environment=HERMES_HOME=$HERMES_HOME
Environment=PATH=$JARVIS_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=default.target
EOF
        log "Service Hermes criado. Ativar com: sudo systemctl enable hermes-tool-proxy"
    fi
}

setup_api_bridge() {
    log "Configurando Jarvis API Bridge..."

    local API_SERVICE="/etc/systemd/system/jarvis-api.service"
    if [ ! -f "$API_SERVICE" ]; then
        sudo bash -c "cat > $API_SERVICE" <<EOF
[Unit]
Description=JARVIS API Bridge (porta 8765)
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$JARVIS_DIR
ExecStart=$JARVIS_DIR/venv/bin/python $JARVIS_DIR/jarvis_api.py
Restart=on-failure
RestartSec=5
Environment=PATH=$JARVIS_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=default.target
EOF
        log "Service API criado. Ativar com: sudo systemctl enable jarvis-api"
    fi
}

setup_nvidia_api() {
    log "Verificando NVIDIA API Key (LLM cloud)..."
    if [ -z "$NVIDIA_API_KEY" ] && [ -z "$JARVIS_NVIDIA_API_KEY" ]; then
        warn "NVIDIA_API_KEY nao definida no ambiente."
        echo "  Obtenha em: https://build.nvidia.com/explore/discover"
        echo "  Adicione ao ~/.bashrc: export NVIDIA_API_KEY='sua-chave'"
        echo "  Ou use modo local: ollama serve + 'modo local' no Jarvis"
    else
        info "NVIDIA_API_KEY configurada"
    fi
}

setup_telegram() {
    log "Configuracao do Telegram (opcional)..."
    info "Para ativar bot do Telegram:"
    echo "  1. Crie bot com @BotFather"
    echo "  2. Edite $CONFIG_DIR/config.json:"
    echo '     "telegram": {"enabled": true, "token": "SEU_TOKEN", "chat_id": "SEU_CHAT_ID"}'
}

run_health_check() {
    log "Executando health check..."
    cd "$JARVIS_DIR"
    source venv/bin/activate
    python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from core.orchestrator import Orchestrator
    o = Orchestrator()
    print('Orchestrator carrega')

    tools = o.tools
    print(f'{len(tools.tools)} ferramentas registradas')

    print(f'Memoria base: {type(o.base_memory).__name__}')
    print(f'Semantica: {type(o.semantic).__name__}')
    print(f'Episodica: {type(o.episodic).__name__}')
    print(f'Procedural: {type(o.procedural).__name__}')

    kb = o.knowledge
    stats = kb.stats()
    print(f'Knowledge Base: {stats}')

    llm = o.llm
    print(f'LLM: {type(llm).__name__} ({llm.model})')

    from stt.vad_stt import VADSTT
    stt = VADSTT(model_name='tiny')
    print(f'STT: {type(stt).__name__} (modelo: {stt.model_name})')
    print(f'   Disponivel: {stt.available}')

    from tts.engine import TTS
    tts = TTS()
    print(f'TTS: {tts.engine} ({tts.voice})')

    # Verifica Vosk
    try:
        from stt.vosk_detector import VoskDetector
        v = VoskDetector()
        print(f'Vosk: OK (modelo: {v.model_path})')
    except Exception as e:
        print(f'Vosk: {e}')

    print()
    print(' TODOS OS SISTEMAS OPERACIONAIS!')

except Exception as e:
    print(f' ERRO: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
}

create_shortcuts() {
    log "Criando atalhos..."

    mkdir -p "$HOME/.local/bin"

    cat > "$HOME/.local/bin/jarvis" << 'JARVIS_SCRIPT'
#!/bin/bash
cd ~/jarvis
source venv/bin/activate
python main.py "$@"
JARVIS_SCRIPT
    chmod +x "$HOME/.local/bin/jarvis"

    cat > "$HOME/.local/bin/jarvis-daemon" << 'JARVIS_DAEMON_SCRIPT'
#!/bin/bash
cd ~/jarvis
source venv/bin/activate
python jarvis_daemon.py "$@"
JARVIS_DAEMON_SCRIPT
    chmod +x "$HOME/.local/bin/jarvis-daemon"

    cat > "$HOME/.local/bin/jarvis-api" << 'JARVIS_API_SCRIPT'
#!/bin/bash
cd ~/jarvis
source venv/bin/activate
python jarvis_api.py "$@"
JARVIS_API_SCRIPT
    chmod +x "$HOME/.local/bin/jarvis-api"

    cat > "$HOME/.local/bin/hermes-proxy" << 'HERMES_PROXY_SCRIPT'
#!/bin/bash
cd ~/jarvis
source venv/bin/activate
python hermes_tool_proxy.py "$@"
HERMES_PROXY_SCRIPT
    chmod +x "$HOME/.local/bin/hermes-proxy"

    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
        warn "Adicionado ~/.local/bin ao PATH. Reinicie o terminal ou rode: source ~/.bashrc"
    fi

    info "Atalhos criados:"
    echo "  jarvis          - Interface grafica"
    echo "  jarvis-daemon   - Daemon de voz (wake word 'ok jarvis')"
    echo "  jarvis-api      - API REST (porta 8765)"
    echo "  hermes-proxy    - Hermes Tool Proxy (porta 8766)"
}

setup_systemd() {
    log "Configurando systemd service para o daemon de voz..."

    if [ ! -f "/etc/systemd/system/jarvis-daemon.service" ]; then
        sudo bash -c "cat > /etc/systemd/system/jarvis-daemon.service" <<EOF
[Unit]
Description=JARVIS Voice Daemon
After=network.target sound.target
Wants=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$JARVIS_DIR
ExecStart=$JARVIS_DIR/venv/bin/python $JARVIS_DIR/jarvis_daemon.py
Restart=on-failure
RestartSec=5
Environment=PATH=$JARVIS_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=HOME=$HOME
Environment=DISPLAY=:0
Environment=PULSE_SERVER=unix:/run/user/$(id -u)/pulse/native

[Install]
WantedBy=default.target
EOF
        log "Service jarvis-daemon criado em /etc/systemd/system/jarvis-daemon.service"
    else
        info "Service jarvis-daemon ja existe"
    fi

    sudo systemctl daemon-reload 2>/dev/null || true
}

main() {
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    JARVIS INSTALLER v1.1                      ║"
    echo "║              Just A Rather Very Intelligent System            ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo

    install_system_deps
    echo
    setup_python_env
    echo
    setup_vosk_model
    echo
    setup_config
    echo
    setup_playwright
    echo
    setup_ollama
    echo
    setup_nvidia_api
    echo
    setup_hermes
    echo
    setup_api_bridge
    echo
    setup_telegram
    echo
    run_health_check
    echo
    create_shortcuts
    echo
    setup_systemd

    echo
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    INSTALACAO CONCLUIDA!                       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo
    info "Proximos passos:"
    echo "  1. source ~/.bashrc"
    echo "  2. Configure NVIDIA_API_KEY: export NVIDIA_API_KEY='sua-chave'"
    echo "     Ou use modo local: export JARVIS_LLM_MODE=local"
    echo "  3. Para iniciar o daemon de voz:"
    echo "     sudo systemctl start jarvis-daemon"
    echo "     journalctl -u jarvis-daemon -f  # logs"
    echo "  4. Ou rode manualmente: jarvis-daemon"
    echo "  5. Interface grafica: jarvis"
    echo
    info "Documentacao completa: $JARVIS_DIR/README.md"
    echo
    info "Wake word: 'ok jarvis'"
    info "Modos: 'modo local' (Ollama) | 'modo online' (NVIDIA)"
}

main "$@"
