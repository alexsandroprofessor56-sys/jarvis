# JARVIS - Just A Rather Very Intelligent System

![JARVIS](https://img.shields.io/badge/JARVIS-v1.0-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-green?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

> **Assistente de IA completo com controle total do computador, memória persistente, automação web, auto-evolução de código e interface estilo Iron Man.**

---

## 🎯 Visão Geral

O JARVIS é um assistente pessoal avançado inspirado no sistema do Homem de Ferro. Roda **localmente** no seu computador com:

| Capacidade | Descrição |
|------------|-----------|
| 🎤 **Voz** | Wake word "jarvis", STT (Whisper), TTS (Edge/Kokoro/espeak) |
| 🖥️ **Controle do PC** | Clicar, digitar, atalhos, abrir apps, screenshots, OCR |
| 🌐 **Web** | Busca, navegação (Playwright), extração, formulários |
| 🧠 **Memória** | Semântica (fatos), Episódica (histórico), Procedural (rotinas) |
| 📚 **RAG** | ChromaDB + embeddings para ingestão de arquivos/diretórios |
| 🤖 **Agentes** | Planejamento multi-etapas, retry automático, computer-use |
| ⚡ **Auto-evolução** | AST analysis → LLM suggestions → Git versioning → Restart |
| 🔌 **Plugins** | Sistema dinâmico de extensões em `~/.jarvis/plugins/` |
| 🖼️ **UI** | PyQt6 com HUD animado, monitor de sistema, push-to-talk |

---

## 🚀 Instalação Rápida

```bash
# 1. Clone/entre no diretório
cd ~/jarvis

# 2. Execute instalador (instala deps sistema + Python + configura)
chmod +x install.sh
./install.sh

# 3. Configure API keys (NVIDIA para Nemotron-3-Ultra)
export NVIDIA_API_KEY="sua-chave-aqui"
# Ou use Ollama local: ollama serve && ollama pull qwen2.5:3b

# 4. Rode!
jarvis              # Interface gráfica
jarvis-daemon       # Daemon voz (wake word "jarvis")
```

### Instalação Manual (se preferir)

```bash
# Dependências do sistema (Ubuntu/Debian)
sudo apt update && sudo apt install -y \
    python3 python3-pip python3-venv ffmpeg espeak-ng \
    portaudio19-dev libasound2-dev tesseract-ocr tesseract-ocr-por \
    poppler-utils libopencv-dev python3-opencv \
    brightnessctl playerctl pamixer wmctrl xdotool \
    docker.io nmap wireguard-tools sqlite3

# Ambiente Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install edge-tts kokoro faster-whisper playwright chromadb sentence-transformers
playwright install chromium

# Configuração
python config_wizard.py
```

---

## ⚙️ Configuração

### Arquivo Principal: `~/.jarvis/config.json`

```json
{
  "stt": {"engine": "whisper", "model": "base", "language": "pt"},
  "llm": {
    "engine": "nvidia",
    "url": "https://integrate.api.nvidia.com/v1",
    "model": "nvidia/nemotron-3-ultra",
    "api_key": "SUA_CHAVE_AQUI",
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "tts": {"engine": "edge", "voice": "pt-BR-AntonioNeural", "speed": 0.8},
  "vision": {"enabled": true, "model": "qwen2.5:3b"},
  "memory": {"enabled": true, "path": "~/.jarvis/memory"},
  "mic": {"device": null, "sample_rate": 16000},
  "evolution": {"enabled": true, "max_changes_per_hour": 5, "risk_limit": "medium"},
  "wake_word": {"enabled": true, "model": "tiny"},
  "telegram": {"enabled": false, "token": "", "chat_id": ""}
}
```

### Wizard Interativo
```bash
python config_wizard.py
```

---

## 🎮 Como Usar

### Interface Gráfica (PyQt6)
```bash
python main.py
# ou
jarvis
```
- **HUD central**: Estado visual animado (idle/listening/thinking/speaking)
- **Painel esquerdo**: CPU, RAM, Rede, GPU, Temp, Uptime
- **Painel direito**: Log de atividades, upload de arquivos, input de comando
- **Teclas**: F4 = Push-to-talk | F11 = Tela cheia

### Daemon de Voz (Background)
```bash
python jarvis_daemon.py
# ou
jarvis-daemon
```
- Escuta continuamente por **"jarvis"**
- Processa comando após wake word
- TTS responde automaticamente
- Logs em `~/.jarvis/logs/`

### Testes Rápidos
```bash
# Testa STT/wake word
python jarvis_daemon.py --test-stt

# Health check completo
python health_check.py
```

---

## 🗣️ Exemplos de Comandos

### Sistema & Apps
```
"abre firefox"
"abre terminal"
"execute ls -la"
"informações do sistema"
"liste arquivos em ~/Documentos"
```

### Web & Busca
```
"pesquise sobre inteligência artificial"
"acesse github.com"
"leia o site https://exemplo.com"
```

### Controle do Computador
```
"tire print da tela"
"analise a tela"
"digite olá mundo"
"clique em 500 300"
"pressione ctrl+c"
"role para baixo"
```

### Memória & Conhecimento
```
"lembre que meu nome é Alex"
"qual é meu nome?"
"aprenda o arquivo ~/docs/manual.pdf"
"aprenda o diretório ~/projetos"
"busque na base sobre Python"
"o que aconteceu hoje?"
```

### Automação Complexa (Computer Use)
```
"jarvis faça: abre o Firefox e vai no YouTube"
"jarvis faça: abre o terminal e roda git status"
"agente: organize meus arquivos de downloads por tipo"
```

### Lembretes & Agendamento
```
"lembrete reunião em 30 minutos"
"agende backup diário às 2h"
"liste lembretes"
```

### Ferramentas Avançadas (160+ disponíveis)
```
"calcule 15 * 23 + 45"
"clima São Paulo"
"gere senha 20 caracteres"
"crie QR code https://meusite.com"
"timer 5 minutos café pronto"
"traduz hello world para português"
"converta 100 USD para BRL"
"compacta pasta ~/projetos"
"ssh user@servidor ls -la"
```

---

## 🏗️ Arquitetura

```
jarvis/
├── main.py                 # Entry point UI
├── jarvis_daemon.py        # Daemon voz (wake word)
├── config_wizard.py        # Configuração interativa
├── health_check.py         # Verificação de saúde
├── install.sh              # Instalador completo
├── requirements.txt        # Deps Python
├── config/
│   └── settings.py         # Config loader/saver
├── core/
│   ├── orchestrator.py     # Cérebro central (939 linhas)
│   ├── tools.py            # Registry 60+ tools
│   ├── extra_tools.py      # 100+ ferramentas extras
│   └── tool_router.py      # Roteamento semântico de tools
├── agent/
│   ├── agent.py            # Agente autônomo
│   ├── computer_use.py     # Controle PC (LLM + heurísticas)
│   ├── self_evolve.py      # Auto-evolução código
│   ├── self_editor.py      # Editor de código
│   ├── self_guard.py       # Rate limiting
│   ├── self_versioner.py   # Git versioning
│   ├── self_restarter.py   # Restart automático
│   ├── planner.py          # Planejamento de tarefas
│   └── executor.py         # Execução paralela
├── memory/
│   ├── semantic.py         # SQLite + sentence-transformers
│   ├── episodic.py         # SQLite temporal
│   ├── procedural.py       # SQLite procedimentos
│   └── store.py            # Memória base (JSON)
├── brain/
│   ├── knowledge.py        # RAG ChromaDB
│   ├── vector_store.py     # Wrapper ChromaDB
│   └── ingestor.py         # Ingestão arquivos
├── stt/
│   ├── vad_stt.py          # Whisper + WebRTC VAD
│   ├── whisper_stt.py      # Whisper simples
│   └── keyword_detector.py # Detecção wake word
├── tts/
│   └── engine.py           # Edge/Kokoro/espeak
├── vision/
│   ├── screen_capture.py   # MSS screenshots
│   └── gui_automation.py   # PyAutoGUI + OCR
├── browser/
│   └── automator.py        # Playwright automation
├── scheduler/
│   └── scheduler.py        # Lembretes + cron (APScheduler)
├── sandbox/
│   └── sandbox.py          # Python/JS/Bash isolado
├── plugins/
│   └── loader.py           # Plugin system dinâmico
├── auth/
│   └── face.py             # OpenCV face recognition
├── llm/
│   ├── nvidia_llm.py       # NVIDIA Nemotron API
│   └── ollama_llm.py       # Ollama local
├── web/
│   └── search.py           # DuckDuckGo search
├── ui.py                   # PyQt6 HUD (1295 linhas)
└── docs/                   # Documentação adicional
```

---

## 🔌 Sistema de Plugins

Crie `~/.jarvis/plugins/meu_plugin.py`:

```python
from plugins.loader import tool, command

class MeuPlugin:
    @tool
    def minha_ferramenta(self, param: str) -> str:
        """Descrição para o LLM saber quando usar"""
        return f"Resultado: {param}"

    @command(r"meu comando (.+)")
    def meu_comando(self, texto: str) -> str:
        return f"Processado: {texto}"
```

O JARVIS carrega automaticamente na inicialização.

---

## ⚡ Auto-Evolução

O JARVIS pode **melhorar seu próprio código**:

```bash
# Via comando
"jarvis, melhore o código de ferramentas"
"auto-evolua para melhor performance"

# Via código
from agent.self_evolve import SelfAgent
agent = SelfAgent(llm=llm, guard=guard, editor=editor, versioner=versioner)
result = agent.execute_evolution("otimizar uso de memória")
```

**Fluxo**: AST Analysis → LLM Suggestion → Guard Check → Git Branch → Edit → Commit → Merge → Restart

---

## 🐳 Docker

```dockerfile
# Dockerfile incluído
docker build -t jarvis .
docker run -it --rm \
  -e NVIDIA_API_KEY=$NVIDIA_API_KEY \
  -v ~/.jarvis:/root/.jarvis \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -e DISPLAY=$DISPLAY \
  jarvis
```

---

## 🔧 Systemd Service (Daemon Voz)

```bash
# Instala
sudo cp jarvis-daemon.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable jarvis-daemon
systemctl start jarvis-daemon

# Logs
journalctl -u jarvis-daemon -f
```

---

## 📊 Health Check

```bash
python health_check.py
```

Verifica: Orchestrator, Tools, Memórias, Knowledge Base, LLM, STT, TTS, Config.

---

## 🛠️ Desenvolvimento

### Estrutura de Tool
```python
def minha_tool(self, param: str) -> str:
    """Descrição clara para o LLM"""
    return "resultado"

# Registrar em core/tools.py:
self.register("minha_tool", self.minha_tool, "Descrição", {"param": {"type": "string"}})
```

### Adicionar Comando Direto (Orchestrator)
Em `orchestrator.py`, adicione regex em `_route_command`:
```python
(r"^meu padrão (.+)$", self._cmd_meu_comando),
```

---

## 📁 Diretórios de Dados

| Diretório | Conteúdo |
|-----------|----------|
| `~/.jarvis/config.json` | Configuração principal |
| `~/.jarvis/memory/` | SQLite: semântica, episódica, procedural |
| `~/.jarvis/chroma_db/` | Vetores RAG (ChromaDB) |
| `~/.jarvis/faces/` | Modelos de reconhecimento facial |
| `~/.jarvis/plugins/` | Plugins personalizados |
| `~/.jarvis/icons/` | Ícones para GUI automation |
| `~/.jarvis/notes/` | Notas salvas |
| `~/.jarvis/logs/` | Logs do daemon |

---

## 🐛 Troubleshooting

### Microfone não funciona
```bash
# Lista devices
arecord -l
pactl list sources short

# Testa
arecord -d 3 -f cd /tmp/test.wav && aplay /tmp/test.wav

# Configura no config.json: "mic": {"device": 5, "sample_rate": 16000}
```

### Wake word não detecta
```bash
# Testa STT isolado
python -c "
from stt.vad_stt import VADSTT
stt = VADSTT(model_name='tiny')
print(stt.listen_for_command(timeout=10))
"
```

### LLM não responde
- Verifique `NVIDIA_API_KEY` no ambiente
- Ou Ollama: `ollama serve` + `ollama pull qwen2.5:3b`
- Teste: `python -c "from llm.nvidia_llm import NvidiaLLM; print(NvidiaLLM().warmup())"`

### TTS sem áudio
```bash
# Testa engines
python -c "
from tts.engine import TTS
TTS(engine='edge').speak('teste')
TTS(engine='espeak').speak('teste')
"
# Instale: pip install edge-tts kokoro pyttsx3
```

### Permissões Docker
```bash
sudo usermod -aG docker $USER
newgrp docker
```

---

## 📝 Licença

MIT License - Use livremente, modifique, distribua.

---

## 🤝 Contribuição

1. Fork o projeto
2. Crie branch: `git checkout -b feature/nova-funcionalidade`
3. Commit: `git commit -m "feat: adiciona X"`
4. Push: `git push origin feature/nova-funcionalidade`
5. Abra Pull Request

---

## 🙏 Créditos

- **NVIDIA Nemotron-3-Ultra** - LLM principal
- **OpenAI Whisper** - STT local
- **Microsoft Edge TTS / Kokoro** - Síntese de voz
- **ChromaDB** - Vector store
- **Playwright** - Browser automation
- **PyQt6** - Interface gráfica
- **Sentence Transformers** - Embeddings
- **APScheduler** - Agendamento

---

**Desenvolvido com ❤️ para a comunidade open source.**

> *"Às vezes você precisa correr antes de poder andar."* — Tony Stark