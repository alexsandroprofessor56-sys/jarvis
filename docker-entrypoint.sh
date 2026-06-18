#!/bin/bash
# Docker entrypoint para JARVIS

set -e

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[JARVIS]${NC} $1"; }
warn() { echo -e "${YELLOW}[AVISO]${NC} $1"; }
error() { echo -e "${RED}[ERRO]${NC} $1"; }

# Configura PulseAudio para container
if [ -n "$PULSE_SERVER" ]; then
    log "Configurando PulseAudio..."
    mkdir -p /run/user/1000/pulse
    # Se não existir socket, tenta conectar no host
    if [ ! -S "$PULSE_SERVER" ]; then
        warn "PulseAudio socket não encontrado em $PULSE_SERVER"
        warn "Áudio pode não funcionar. Use: docker run -v /run/user/1000/pulse:/run/user/1000/pulse ..."
    fi
fi

# Configura X11 para GUI
if [ -n "$DISPLAY" ]; then
    log "Display: $DISPLAY"
    if [ ! -f /tmp/.X11-unix/X${DISPLAY#*:} ]; then
        warn "X11 socket não encontrado. GUI pode não funcionar."
        warn "Use: docker run -v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=\$DISPLAY ..."
    fi
    # Permite conexões X11 locais
    xhost +local: 2>/dev/null || true
fi

# Verifica configuração
CONFIG_FILE="$HOME/.jarvis/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    warn "Config não encontrada. Criando padrão..."
    python3 -c "
import config.settings as s
s.save(s.DEFAULT_CONFIG)
print('Config padrão criada')
" 2>/dev/null || error "Falha ao criar config"
fi

# Verifica NVIDIA_API_KEY se usando NVIDIA
if grep -q '"engine": "nvidia"' "$CONFIG_FILE" 2>/dev/null; then
    if [ -z "$NVIDIA_API_KEY" ]; then
        warn "NVIDIA_API_KEY não definida no ambiente!"
        warn "Defina com: docker run -e NVIDIA_API_KEY=sua_chave ..."
    else
        log "NVIDIA_API_KEY configurada ✓"
    fi
fi

# Executa health check rápido
log "Executando health check..."
if /home/jarvis/jarvis/venv/bin/python /home/jarvis/jarvis/health_check.py >/dev/null 2>&1; then
    log "Health check: PASSOU ✓"
else
    warn "Health check: FALHOU (continuando mesmo assim)"
fi

# Executa comando passado
log "Iniciando: $@"
exec "$@"