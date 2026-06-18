#!/bin/bash
# JARVIS - Script de Instalação Completa
# Instala todas as dependências e configura o ambiente

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
            libasound2-dev libsndfile1-dev \
            mss-tools \
            tesseract-ocr tesseract-ocr-por \
            poppler-utils \
            libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
            libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
            libxfixes3 libxrandr2 libgbm1 libasound2 \
            git curl wget \
            build-essential cmake pkg-config \
            libopencv-dev python3-opencv \
            brightnessctl playerctl pamixer \
            wmctrl xdotool \
            docker.io docker-compose \
            nmap net-tools iproute2 \
            bluetooth bluez libbluetooth-dev \
            wireguard-tools \
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
            portaudio tesseract tesseract-data-por \
            poppler \
            opencv python-opencv \
            brightnessctl playerctl pamixer \
            wmctrl xdotool \
            docker docker-compose \
            nmap net-tools iproute2 \
            bluez bluez-utils \
            wireguard-tools \
            sqlite3 \
            base-devel cmake pkg-config \
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
            nmap-ncat net-tools iproute \
            bluez bluez-libs-devel \
            wireguard-tools \
            sqlite3 sqlite-devel \
            gcc gcc-c++ make cmake pkgconfig \
            2>/dev/null || warn "Alguns pacotes do sistema falharam"
    else
        warn "Gerenciador de pacotes não reconhecido. Instale manualmente:"
        echo "  python3, pip, ffmpeg, espeak-ng, portaudio, tesseract-ocr, poppler, opencv"
        echo "  brightnessctl, playerctl, pamixer, wmctrl, xdotool"
        echo "  docker, nmap, wireguard-tools, sqlite3, build tools"
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
    
    log "Instalando dependências Python..."
    pip install -r requirements.txt
    
    # Instalações extras que podem falhar silenciosamente
    pip install edge-tts kokoro faster-whisper 2>/dev/null || warn "Alguns pacotes de voz opcionais falharam"
    pip install playwright 2>/dev/null && playwright install chromium 2>/dev/null || warn "Playwright opcional"
    pip install chromadb sentence-transformers 2>/dev/null || warn "ChromaDB opcional"
    pip install opencv-python opencv-contrib-python 2>/dev/null || warn "OpenCV contrib opcional"
    pip install apscheduler watchdog 2>/dev/null || warn "Scheduler opcional"
    pip install pyannote-audio speechbrain 2>/dev/null || warn "Audio avançado opcional"
    pip install docker 2>/dev/null || warn "Docker SDK opcional"
    pip install googletrans==4.0.0-rc1 2>/dev/null || warn "Tradutor opcional"
    pip install deep-translator qrcode[pil] pyttsx3 paramiko 2>/dev/null || warn "Extras opcionais"
}

setup_config() {
    log "Configurando diretórios e arquivos..."
    
    mkdir -p "$CONFIG_DIR"/{memory,faces,plugins,icons,notes,clipboard}
    mkdir -p "$CONFIG_DIR"/chroma_db
    mkdir -p "$HOME/Pictures"
    mkdir -p "$HOME/Downloads/jarvis_downloads"
    
    # Copia config padrão se não existe
    if [ ! -f "$CONFIG_DIR/config.json" ]; then
        cp "$JARVIS_DIR/config/settings.py" "$CONFIG_DIR/config.json.template" 2>/dev/null || true
        python3 -c "
import config.settings as s
s.save(s.DEFAULT_CONFIG)
print('Configuração padrão criada em $CONFIG_DIR/config.json')
" 2>/dev/null || warn "Falha ao criar config padrão"
    fi
    
    # Face padrão opcional
    if [ ! -f "$CONFIG_DIR/face.png" ]; then
        info "Nenhuma face.png encontrada. O JARVIS usará orb padrão."
        info "Coloque uma imagem 200x200 em $CONFIG_DIR/face.png para personalizar."
    fi
}

setup_playwright() {
    log "Configurando Playwright..."
    source "$JARVIS_DIR/venv/bin/activate"
    playwright install chromium 2>/dev/null || warn "Playwright install falhou (precisa de dependências do sistema)"
    playwright install-deps chromium 2>/dev/null || true
}

setup_ollama() {
    log "Verificando Ollama (LLM local opcional)..."
    if ! check_command ollama; then
        warn "Ollama não instalado. Para usar LLM local:"
        echo "  curl -fsSL https://ollama.ai/install.sh | sh"
        echo "  ollama serve"
        echo "  ollama pull qwen2.5:3b"
    else
        info "Ollama encontrado. Modelos disponíveis:"
        ollama list 2>/dev/null | head -10 || true
    fi
}

setup_nvidia_api() {
    log "Verificando NVIDIA API Key (LLM cloud)..."
    if [ -z "$NVIDIA_API_KEY" ]; then
        warn "NVIDIA_API_KEY não definida no ambiente."
        echo "  Obtenha em: https://build.nvidia.com/explore/discover"
        echo "  Adicione ao ~/.bashrc: export NVIDIA_API_KEY='sua-chave'"
    else
        info "NVIDIA_API_KEY configurada ✓"
    fi
}

setup_telegram() {
    log "Configuração do Telegram (opcional)..."
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
    print('✅ Orchestrator carrega')
    
    # Testa ferramentas básicas
    tools = o.tools
    print(f'✅ {len(tools.tools)} ferramentas registradas')
    
    # Testa memórias
    print(f'✅ Memória base: {type(o.base_memory).__name__}')
    print(f'✅ Semântica: {type(o.semantic).__name__}')
    print(f'✅ Episódica: {type(o.episodic).__name__}')
    print(f'✅ Procedural: {type(o.procedural).__name__}')
    
    # Testa knowledge base
    kb = o.knowledge
    stats = kb.stats()
    print(f'✅ Knowledge Base: {stats}')
    
    # Testa LLM
    llm = o.llm
    print(f'✅ LLM: {type(llm).__name__} ({llm.model})')
    
    # Testa STT
    from stt.vad_stt import VADSTT
    stt = VADSTT(model_name='tiny')
    print(f'✅ STT: {type(stt).__name__} (modelo: {stt.model_name})')
    print(f'   Disponível: {stt.available}')
    
    # Testa TTS
    from tts.engine import TTS
    tts = TTS()
    print(f'✅ TTS: {tts.engine} ({tts.voice})')
    
    print()
    print('🎉 TODOS OS SISTEMAS OPERACIONAIS!')
    
except Exception as e:
    print(f'❌ ERRO: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
}

create_shortcuts() {
    log "Criando atalhos..."
    
    # Script de inicialização
    cat > "$HOME/.local/bin/jarvis" << 'EOF'
#!/bin/bash
cd ~/jarvis
source venv/bin/activate
python main.py "$@"
EOF
    chmod +x "$HOME/.local/bin/jarvis"
    
    # Script do daemon
    cat > "$HOME/.local/bin/jarvis-daemon" << 'EOF'
#!/bin/bash
cd ~/jarvis
source venv/bin/activate
python jarvis_daemon.py "$@"
EOF
    chmod +x "$HOME/.local/bin/jarvis-daemon"
    
    # Adiciona ao PATH se necessário
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
        warn "Adicionado ~/.local/bin ao PATH. Reinicie o terminal ou rode: source ~/.bashrc"
    fi
    
    info "Atalhos criados: 'jarvis' e 'jarvis-daemon'"
}

setup_systemd() {
    log "Configurando systemd service (opcional)..."
    
    cat > /tmp/jarvis-daemon.service << EOF
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

[Install]
WantedBy=default.target
EOF
    
    info "Service file criado em /tmp/jarvis-daemon.service"
    info "Para instalar: sudo cp /tmp/jarvis-daemon.service /etc/systemd/system/"
    info "Para ativar: systemctl --user enable jarvis-daemon && systemctl --user start jarvis-daemon"
}

main() {
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    JARVIS INSTALLER v1.0                      ║"
    echo "║              Just A Rather Very Intelligent System            ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo
    
    install_system_deps
    echo
    setup_python_env
    echo
    setup_config
    echo
    setup_playwright
    echo
    setup_ollama
    echo
    setup_nvidia_api
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
    echo "║                    INSTALAÇÃO CONCLUÍDA!                       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo
    info "Próximos passos:"
    echo "  1. source ~/.bashrc"
    echo "  2. Configure NVIDIA_API_KEY: export NVIDIA_API_KEY='sua-chave'"
    echo "  3. (Opcional) ollama serve && ollama pull qwen2.5:3b"
    echo "  4. Rode: jarvis          # Interface gráfica"
    echo "  5. Rode: jarvis-daemon   # Daemon de voz (wake word 'jarvis')"
    echo
    info "Documentação completa: $JARVIS_DIR/README.md"
}

main "$@"