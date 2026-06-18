# JARVIS — Guia Rápido de Download e Instalação

Assistente de voz com IA multimodal: wake word "ok jarvis", controle total do PC por voz, LLM dual (online NVIDIA ou local Ollama), visão computacional, memória persistente.

---

## 1. Download

```bash
git clone https://github.com/alexsandroprofessor56-sys/jarvis
cd jarvis
```

Isso baixa o projeto completo para o diretório `~/jarvis`.

---

## 2. Instalação automática

```bash
chmod +x install.sh
./install.sh
```

O instalador faz tudo sozinho:

- Instala dependências do sistema (Python, ffmpeg, Tesseract OCR, PortAudio, OpenCV, Docker, etc.)
- Cria ambiente virtual Python (`venv/`)
- Instala todos os pacotes Python necessários
- **Baixa o modelo Vosk PT-BR** (42MB) — essencial para a wake word "ok jarvis"
- **Instala Ollama + qwen2.5:3b** (~1.8GB) — LLM local para quando não tiver internet
- Cria diretórios de configuração em `~/.jarvis/`
- Configura atalhos: `jarvis`, `jarvis-daemon`, `jarvis-api`, `hermes-proxy`
- Cria serviços systemd para rodar em background
- Executa health check para verificar se tudo funciona

**Tempo estimado:** 5–20 minutos (depende da internet para baixar modelos).

> 💡 O instalador **não faz**:
> - **Ollama Moondream** (visão computacional, ~1.7GB) — perguntará se quer baixar
> - **Hermes Tool Proxy** (192+ ferramentas avançadas) — opcional, requer instalação separada

---

## 3. Configurar chave da NVIDIA (modo online)

O JARVIS usa NVIDIA Nemotron como IA principal (mais inteligente). Você precisa de uma chave gratuita:

1. Acesse https://build.nvidia.com/explore/discover
2. Crie conta e gere uma API Key
3. Defina no ambiente:

```bash
export NVIDIA_API_KEY='sua-chave-aqui'
```

Para não precisar digitar toda vez, adicione ao `~/.bashrc`:

```bash
echo 'export NVIDIA_API_KEY="sua-chave-aqui"' >> ~/.bashrc
source ~/.bashrc
```

> 💡 **Sem chave NVIDIA?** Use modo local: a install.sh já baixou o Ollama + qwen2.5:3b. Após iniciar o JARVIS, diga **"modo local"** para usar IA offline.

---

## 4. Iniciar o JARVIS

### Modo daemon de voz (recomendado)

Escuta sua voz em background e responde quando ouvir "ok jarvis":

```bash
jarvis-daemon
```

Ou como serviço do sistema (inicia automático no boot):

```bash
sudo systemctl start jarvis-daemon
sudo systemctl enable jarvis-daemon
```

Logs:

```bash
journalctl -u jarvis-daemon -f
```

### Modo interface gráfica

Janela estilo HUD do Homem de Ferro com monitor do sistema:

```bash
jarvis
```

> Tecla **F4** = Push-to-talk | **F11** = Tela cheia

---

## 5. Testar

Após o daemon rodar, diga:

```
ok jarvis que horas são?
```

Você deve ouvir o chime de ativação seguido da resposta por voz.

---

## 6. Principais comandos de voz

### Sistema
- "ok jarvis abre firefox"
- "ok jarvis execute ls -la"
- "ok jarvis informações do sistema"
- "ok jarvis digite olá mundo"
- "ok jarvis pressione ctrl+c"

### Tela
- "ok jarvis tire print da tela"
- "ok jarvis o que tem na tela?" (requer Ollama + moondream)
- "ok jarvis analise a tela"

### Web
- "ok jarvis pesquise sobre inteligência artificial"
- "ok jarvis acesse github.com"

### Memória
- "ok jarvis lembre que meu nome é Alex"
- "ok jarvis qual é meu nome?"
- "ok jarvis busque na base sobre Python"

### Modos de IA
- "modo local" → usa Ollama (qwen2.5:3b, offline)
- "modo online" → usa NVIDIA Nemotron (padrão)

---

## 7. Personalização

Edite `~/.jarvis/config.json` para ajustar:

```json
{
  "tts": {"engine": "edge", "voice": "pt-BR-AntonioNeural"},
  "mic": {"device": null, "sample_rate": 16000},
  "vision": {"model": "qwen2.5:3b"}
}
```

Ou use o wizard:

```bash
python config_wizard.py
```

---

## 8. Adicionar novas ferramentas

Crie `~/.jarvis/plugins/meu_plugin.py`:

```python
from plugins.loader import tool

class MeuPlugin:
    @tool
    def minha_ferramenta(self, param: str) -> str:
        """Descrição para o LLM saber quando usar"""
        return f"Resultado: {param}"
```

O JARVIS carrega automaticamente na próxima inicialização.

---

## 9. Atualizar

```bash
cd ~/jarvis
git pull
source venv/bin/activate
pip install -r requirements.txt
```

---

**Dúvidas?** Abra issue em: https://github.com/alexsandroprofessor56-sys/jarvis/issues
