   

  ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
  ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
  ██║███████║██████╔╝██║   ██║██║███████╗
  ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
  ██║██║  ██║██║  ██║ ╚████╔╝ ██║███████║
  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝

  Assistente de IA Autônomo — Kali Linux
  ========================================
  Modelo: qwen2.5:3b (Ollama local)
  Interface: PyQt6 HUD Desktop + Telegram + Voz
  Linhas de Código: ~8.000 Python
  Testes: 43 (100% passing)
  Total de Ferramentas: 95+

  1.  VISÃO GERAL
  ─────────────────────────────────────────────────────────────

  Jarvis é um assistente de IA completo rodando 100% local no Kali Linux.
  Ele combina processamento de linguagem natural (LLM), reconhecimento
  de fala, síntese de voz, visão computacional, navegação web autônoma,
  automação de interface gráfica, memórias de longo prazo e capacidade
  de auto-evolução — tudo controlado por um modelo de linguagem local
  via Ollama.

  Diferente de assistentes na nuvem, Jarvis:
  • Funciona SEM internet (offline-first)
  • Tem acesso total ao sistema (terminal, arquivos, processos)
  • Controla mouse/teclado (pyautogui)
  • Vê a tela (screenshot + OCR + análise por IA)
  • Aprende e melhora o próprio código (auto-evolução)
  • Cria apps/sites completos (AppBuilder)
  • Se comunica por Telegram, voz e interface desktop


  2.  ARQUITETURA
  ─────────────────────────────────────────────────────────────

                        ┌─────────────────────┐
                        │     Interface        │
                        │  PyQt6 HUD Desktop   │
                        └──────┬──────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
    ┌─────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
    │  Telegram   │     │  Microfone  │     │  Terminal   │
    │  Listener   │     │  VAD+Whisper│     │  (digitar)  │
    └─────┬──────┘     └──────┬──────┘     └──────┬──────┘
          │                    │                    │
          └────────────────────┼────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │    Orchestrator     │
                    │  (process_text)     │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────────┐
          │                    │                        │
    ┌─────▼──────┐     ┌──────▼──────┐          ┌──────▼──────┐
    │   LLM      │     │  ToolRegistry│          │   Speech    │
    │ OllamaLLM  │◄───►│  95+ Tools  │          │ TTS Engine  │
    └────────────┘     └──────┬──────┘          └─────────────┘
                              │
        ┌─────────────────────┼──────────────────────────┐
        │                     │                          │
  ┌─────▼──────┐    ┌─────────▼────────┐       ┌─────────▼────────┐
  │  Memórias  │    │   Conhecimento   │       │   Agentes        │
  │  • Store   │    │   • RAG Vector   │       │   • Autônomo     │
  │  • Semant. │    │   • Ingestor     │       │   • Self-Evolve  │
  │  • Episód. │    │   • PDF/DOCX/IMG │       │   • ComputerUse  │
  │  • Proced. │    └──────────────────┘       │   • AppBuilder   │
  └────────────┘                               └──────────────────┘


  3.  COMPONENTES PRINCIPAIS
  ─────────────────────────────────────────────────────────────

  3.1  Orchestrator (core/orchestrator.py)
  ──────────────────────────────────────
  O cérebro do Jarvis. Recebe comandos (texto, voz, Telegram),
  roteia para comandos rápidos (via regex) ou envia para o LLM
  com ferramentas, e coordena a resposta final com TTS.

  Fluxo:
    Entrada → Roteamento Rápido → LLM + Tools → Resposta → TTS

  3.2  LLM — Ollama (llm/ollama_llm.py)
  ────────────────────────────────────
  • Modelo padrão: qwen2.5:3b
  • URL: http://127.0.0.1:11434
  • Suporte a tool calling (function calling)
  • Trocável via model_switch tool
  • Fallback para chat simples se tools não disponíveis

  3.3  Memórias (memory/)
  ─────────────────────────
  Quatro tipos de memória:

  • MemoryStore: Chave-valor simples (lembrar nome, preferências)
  • SemanticMemory: Fatos categorizados com relevância (ex: "o
    usuário se chama Alex")
  • EpisodicMemory: Histórico de eventos com timestamp (últimos
    comandos, respostas)
  • ProceduralMemory: Procedimentos aprendidos (sequências de
    passos reutilizáveis)

  3.4  Conhecimento — RAG (brain/)
  ─────────────────────────────────
  • Base vetorial ChromaDB para busca semântica
  • Ingestão de PDFs, DOCX, TXT, imagens
  • Consulta por similaridade com contexto

  3.5  Visão (vision/)
  ─────────────────────
  • ScreenCapture: Screenshot + análise via LLM de visão
  • GUIAutomation: Localizar imagem/texto na tela e clicar (OCR)

  3.6  Navegador (browser/)
  ──────────────────────────
  • Playwright para navegação web automatizada
  • Navegar, pesquisar, clicar, preencher formulários, extrair

  3.7  Sandbox (sandbox/)
  ───────────────────────
  • Execução segura de Python, Bash, JavaScript
  • Isolado do sistema principal

  3.8  Reconhecimento Facial (auth/)
  ──────────────────────────────────
  • FaceAuth: Registrar e autenticar por rosto (câmera)
  • Não substitui senha — camada adicional

  3.9  Áudio/Fala (stt/, tts/, audio/)
  ─────────────────────────────────────
  • VAD (Voice Activity Detection) + Whisper STT
  • Edge-TTS (Microsoft) ou Kokoro TTS
  • Diarização de locutores


  4.  FERRAMENTAS (95+)
  ─────────────────────────────────────────────────────────────

  4.1  Base — 47 ferramentas (core/tools.py)
  ──────────────────────────────────────────

  ┌──────────────────────┬─────────────────────────────────────┐
  │ Categoria            │ Ferramentas                          │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Sistema              │ open_app, run_command, get_system_   │
  │                      │ info, list_files                     │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Web                  │ search_web, web_fetch, web_open      │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Mouse/Teclado        │ type_text, keyboard_hotkey, mouse_   │
  │                      │ move, mouse_click, mouse_scroll      │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Visão/Tela           │ screenshot, analyze_screen            │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Memória              │ remember, recall, knowledge_query,   │
  │                      │ knowledge_learn_file/dir, semantic_  │
  │                      │ remember/recall, episodic_query,     │
  │                      │ procedural_learn/recall              │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Agente               │ agent_run (tarefas complexas)        │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Navegador            │ browser_navigate/search/click/fill/  │
  │                      │ extract                              │
  ├──────────────────────┼─────────────────────────────────────┤
  │ GUI                  │ gui_find_click_image/text            │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Facial               │ face_register, face_auth             │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Agendamento          │ reminder_add/cron/list               │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Sandbox              │ sandbox_python/bash/javascript        │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Plugins              │ plugin_list                          │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Aprendizado          │ learner_stats                        │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Auto-Evolução        │ self_evolve                          │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Computador           │ computer_use, computer_stop          │
  └──────────────────────┴─────────────────────────────────────┘

  4.2  Extra — 48 ferramentas (core/extra_tools.py)
  ──────────────────────────────────────────────────

  ┌──────────────────────┬─────────────────────────────────────┐
  │ Categoria            │ Ferramentas                          │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Sistema              │ system_monitor, process_list/kill,   │
  │                      │ service_control, power_control       │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Arquivos             │ file_search/read/write/delete/copy_  │
  │                      │ move                                 │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Rede/Segurança       │ network_info, port_scan (nmap),      │
  │                      │ wifi_scan, bluetooth_control,        │
  │                      │ vpn_control, hash_file,              │
  │                      │ password_generate                    │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Mídia                │ camera_capture, record_audio,        │
  │                      │ play_audio, image_manipulate,        │
  │                      │ pdf_generate, ocr_file               │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Dev                  │ docker_ps/exec, git_status/commit,   │
  │                      │ api_request, sql_query, model_switch │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Comunicação          │ send_email, send_notification,       │
  │                      │ http_server/stop, telegram_send,     │
  │                      │ telegram_listener_start/stop         │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Credenciais          │ credential_save/get/list/delete      │
  ├──────────────────────┼─────────────────────────────────────┤
  │ AppBuilder           │ app_builder, app_status, app_list,   │
  │                      │ app_deploy                           │
  └──────────────────────┴─────────────────────────────────────┘

  4.3  AllFeatures — 50 ferramentas (core/all_features.py)
  ────────────────────────────────────────────────────────

  ┌──────────────────────┬─────────────────────────────────────┐
  │ Categoria            │ Ferramentas                          │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Arquivos             │ file_organizer, nlp_file_search,     │
  │                      │ backup_create/list                   │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Sistema              │ dependency_monitor, gpu_info          │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Clipboard            │ clipboard_history_start/stop/get/    │
  │                      │ clear                                │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Conversa             │ conversation_search                  │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Notas                │ notes_add/list/get/delete            │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Contatos             │ contacts_add/list/delete             │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Calendário           │ calendar_add/list                    │
  ├──────────────────────┼─────────────────────────────────────┤
  │ GitHub               │ github_issues/prs/search             │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Segurança            │ intrusion_scan, firewall_rule_add/   │
  │                      │ list, certificate_check/generate     │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Sessão               │ session_record_start/stop,           │
  │                      │ session_replay                       │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Personalização       │ wake_word_set, embedding_model_set,  │
  │                      │ theme_set, voice_emotion_set         │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Música               │ ambient_music_play/stop              │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Rede                 │ network_monitor_start/stop           │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Comunicação          │ email_fetch, discord_send,           │
  │                      │ whatsapp_send, sms_send              │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Home Assistant       │ home_assistant_query/control         │
  ├──────────────────────┼─────────────────────────────────────┤
  │ Código               │ code_review (AST analysis)           │
  └──────────────────────┴─────────────────────────────────────┘


  5.  COMUNICAÇÃO
  ─────────────────────────────────────────────────────────────

  5.1  Desktop (PyQt6 HUD)
  ────────────────────────
  Interface heads-up display que sobrepõe a área de trabalho.
  Mostra status (idle/listening/processing/speaking) e logs.

  5.2  Voz
  ────────
  • Ativação por palavra de alerta: "Jarvis"
  • Reconhecimento: Whisper STT (VAD para detecção de fala)
  • Síntese: Edge-TTS (voz pt-BR-AntonioNeural)
  • Guerra de áudio: gravação e reprodução

  5.3  Telegram
  ─────────────
  • Bot polling via getUpdates
  • Comandos: /start, /status, /help, /shell
  • Mensagens enviadas ao LLM via process_text
  • Respostas enviadas de volta ao chat
  • Token e chat_id configuráveis
  • Auto-start no boot do Jarvis


  6.  AUTO-EVOLUÇÃO
  ─────────────────────────────────────────────────────────────

  Jarvis pode modificar o próprio código-fonte de forma segura:

  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │   SelfGuard → SelfEditor → SelfVersioner → SelfEvolve  │
  │                                                         │
  │   • Guard: valida caminhos, rate-limit (5/h),           │
  │     bloqueia arquivos críticos (self_guard.py)          │
  │   • Editor: aplica patches, valida sintaxe,             │
  │     rollback automático em erro                         │
  │   • Versioner: git branch/commit/rollback/merge         │
  │     branches: self-edit/<timestamp>                     │
  │   • SelfAgent: análise AST, geração de sugestões        │
  │     via LLM, plano de evolução                          │
  │   • SelfRestarter: detecta mudanças estruturais,        │
  │     salva estado, reinicia processo                     │
  │                                                         │
  └─────────────────────────────────────────────────────────┘

  Testado: 25 testes de evolução (todos passando)


  7.  APP BUILDER
  ─────────────────────────────────────────────────────────────

  Jarvis pode criar apps e sites completos a partir de
  descrições em linguagem natural:

  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │   "cria um app de tarefas"                              │
  │       ↓                                                 │
  │   AppBuilder.analyze() → LLM decide tipo                │
  │   AppBuilder.scaffold() → estrutura de diretórios       │
  │   AppBuilder.generate() → código via template + LLM     │
  │   AppBuilder.build() → executa build.sh                 │
  │   AppBuilder.deploy() → GitHub Pages ou local           │
  │   AppBuilder.deliver() → URL/APK para o usuário        │
  │                                                         │
  │   Tipos suportados:                                     │
  │   • Site estático (HTML/CSS/JS)                         │
  │   • PWA (manifest + service worker + ícone)             │
  │   • APK Flutter (via Flutter SDK, se instalado)         │
  │   • PWA→APK via Bubblewrap                              │
  │                                                         │
  └─────────────────────────────────────────────────────────┘

  Ferramentas: app_builder, app_status, app_list, app_deploy
  Testado: 13 testes de AppBuilder (todos passando)


  8.  COMPUTER USE
  ─────────────────────────────────────────────────────────────

  Jarvis pode controlar o computador como uma pessoa:

  • Screenshot → OCR (extrair texto/elementos)
  • LLM decide próximo passo (clique, digitação, tecla)
  • Pyautogui com movimentos de mouse humanizados (bezier)
  • Loop de verificação até tarefa completa
  • Fallback: OCR → heurística → ação padrão
  • Botão de emergência: mover mouse para o canto


  9.  CREDENTIAL VAULT
  ─────────────────────────────────────────────────────────────

  Cofre de senhas criptografado:

  • Algoritmo: Fernet (AES-256 via PBKDF2)
  • Chave: ~/.jarvis/.vault_key (permissão 600)
  • Dados: ~/.jarvis/vault.json (criptografado)
  • 3 contas Google armazenadas
  • Ferramentas: credential_save/get/list/delete


  10.  CONFIGURAÇÃO
  ─────────────────────────────────────────────────────────────

  Arquivo: ~/.jarvis/config.json

  { "mic": { "device": null, "sample_rate": 16000 },
    "tts": { "engine": "edge", "voice": "pt-BR-AntonioNeural",
             "speed": 1.0 },
    "telegram": { "enabled": true, "token": "...",
                  "chat_id": "...", "auto_start": true },
    "evolution": { "max_changes_per_hour": 5,
                   "git_repo_path": "/home/alexkali/jarvis" },
    "vision": { "model": null },
    "memory_dir": "/media/cartao_memoria/jarvis_memory",
    "model": "qwen2.5:3b",
    "ollama_url": "http://127.0.0.1:11434" }


  11.  TESTES
  ─────────────────────────────────────────────────────────────

  43 testes, 100% passando:

  ┌─────────────────────────────────────┬────────┐
  │ Suite                                │ Testes │
  ├─────────────────────────────────────┼────────┤
  │ AppBuilder Core                      │   7    │
  │ AppBuilder Site Generator            │   2    │
  │ AppBuilder PWA Generator             │   3    │
  │ AppBuilder Flutter Generator         │   2    │
  │ AppBuilder Integration               │   4    │
  │ Self-Evolution (guard)               │   5    │
  │ Self-Evolution (versioner)           │   4    │
  │ Self-Evolution (editor)              │   4    │
  │ Self-Evolution (evolve agent)        │   4    │
  │ Self-Evolution (restarter)           │   3    │
  │ Self-Evolution (integration)         │   3    │
  │ Self-Evolution (settings)            │   1    │
  │ Self-Evolution (tools)               │   1    │
  ├─────────────────────────────────────┼────────┤
  │ Total                                │  43    │
  └─────────────────────────────────────┴────────┘


  12.  DEPENDÊNCIAS
  ─────────────────────────────────────────────────────────────

  Principais pacotes Python:
  • ollama, requests — LLM + API
  • PyQt6 — interface desktop
  • pyautogui, pyperclip — automação de mouse/teclado
  • beautifulsoup4, playwright — navegação web
  • cryptography — cofre de credenciais
  • psutil — monitoramento do sistema
  • pillow, pytesseract — processamento de imagem/OCR
  • fpdf2, python-docx — geração de documentos
  • chromadb, sentence-transformers — RAG vetorial
  • opencv-python — visão computacional
  • whisper (openai) — speech-to-text
  • edge-tts — síntese de voz


  13.  ESTRUTURA DE DIRETÓRIOS
  ─────────────────────────────────────────────────────────────

  jarvis/
  ├── agent/             # Agentes (evolução, computer_use, app_builder...)
  ├── app_templates/     # Templates para AppBuilder
  ├── audio/             # Diarização de áudio
  ├── auth/              # Reconhecimento facial
  ├── brain/             # Conhecimento (RAG + vetores)
  ├── browser/           # Automação de navegador (Playwright)
  ├── config/            # Configurações
  ├── core/              # Orquestrador, ferramentas, features
  ├── docs/              # Documentação de design e planos
  ├── learning/          # Aprendizado do usuário
  ├── llm/               # Interface com Ollama
  ├── memory/            # Memórias (store, semântica, episódica...)
  ├── plugins/           # Sistema de plugins
  ├── sandbox/           # Execução segura de código
  ├── scheduler/         # Agendador de tarefas
  ├── stt/               # Speech-to-text (VAD + Whisper)
  ├── tests/             # 43 testes pytest
  ├── tts/               # Text-to-speech (Edge/Kokoro)
  ├── vision/            # Captura de tela, automação GUI
  ├── web/               # Busca na web
  ├── main.py            # Ponto de entrada
  └── ui.py              # Interface PyQt6


  14.  LIMITAÇÕES ATUAIS
  ─────────────────────────────────────────────────────────────

  • Modelo qwen2.5:3b é pequeno para tarefas complexas de
    código — modelo maior recomendado para geração profissional
  • Flutter SDK não instalado (precisa de ~1.5GB)
  • APK via Bubblewrap (PWA→APK) não testado
  • GitHub CLI (gh) precisa de autenticação para deploy
  • Reconhecimento facial depende de câmera
  • WhatsApp/Discord/Home Assistant precisam de credenciais
  • ComputerUseAgent não testado end-to-end


  15.  PRÓXIMOS PASSOS SUGERIDOS
  ─────────────────────────────────────────────────────────────

  1. Testar ComputerUseAgent ("abre o Firefox e vai no YouTube")
  2. Instalar Flutter SDK para geração de APK nativo
  3. Configurar deploy GitHub Pages (autenticar gh CLI)
  4. Testar AppBuilder end-to-end com projeto real
  5. Implementar web dashboard (Flask/FastAPI)
  6. GPU acceleration para Ollama/Whisper
  7. Testar integrações WhatsApp/Discord/Home Assistant
