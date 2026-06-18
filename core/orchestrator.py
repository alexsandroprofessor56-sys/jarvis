import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
import agent.computer_use
import config.settings as settings

_POOL = ThreadPoolExecutor(max_workers=4)

BASE_PROMPT = (
    "Você é o J.A.R.V.I.S, um assistente inteligente, gentil e naturalmente curioso. "
    "Responda SEMPRE em português brasileiro natural e conversacional.\n\n"
    "PERSONALIDADE:\n"
    "- Seja gentil, acolhedor e educado\n"
    "- Demonstre curiosidade genuína pelo usuário\n"
    "- Faça perguntas de follow-up naturais quando apropriado\n"
    "- Use linguagem calorosa: 'com certeza', 'ficarei feliz em ajudar', 'interessante...'\n"
    "- Evite respostas robóticas ou excessivamente formais\n\n"
    "REGRAS OBRIGATÓRIAS PARA FALA:\n"
    "- NUNCA use símbolos: # * _ ` [ ] ( ) ~ | \\ / > + = -\n"
    "- NUNCA use markdown: ** __ ## ### ```\n"
    "- NUNCA use emojis: 😀 🎉 🤖 💡 ⚡ etc\n"
    "- NUNCA use formatação técnica ou código na fala\n"
    "- Fale como uma pessoa normal conversando\n"
    "- Respostas diretas, naturais, sem enfeites\n\n"
    "DIRETRIZES:\n"
    "- Analise o que o usuário pediu e escolha a ferramenta mais adequada\n"
    "- Se a pergunta for simples, responda diretamente sem ferramenta\n"
    "- Você pode usar quantas ferramentas precisar para realizar a tarefa\n"
    "- Se nenhuma ferramenta for adequada, use seu próprio conhecimento\n\n"
    "FERRAMENTAS DISPONÍVEIS:\n"
    "- tela: screen_capture, screen_ocr (ler texto), screen_ask (perguntar sobre a tela)\n"
    "- mouse: mouse_move, mouse_click, mouse_scroll\n"
    "- teclado: keyboard_type, keyboard_hotkey\n"
    "- sistema: get_system_info, app_launch, app_kill, app_list, system_run\n"
    "- arquivos: file_list, file_read, file_write, file_create, file_delete, file_copy, file_move\n"
    "- web: search_web, web_fetch, web_open, browser_navigate, browser_search, browser_click, browser_fill, browser_extract\n"
    "- memória: remember, recall, semantic_remember, semantic_recall, episodic_query\n"
    "- conhecimento: knowledge_query, knowledge_learn_file, knowledge_learn_dir\n"
    "- procedimentos: procedural_learn, procedural_recall, procedural_replay\n"
    "- desenvolvimento: run_command, sandbox_python, sandbox_bash, sandbox_javascript\n"
    "- utilidades: clipboard_get, clipboard_set, screenshot, analyze_screen, calculator, timer\n"
    "- hermes: hermes_tool (qualquer ferramenta), hermes_delegate (tarefa complexa)"
)

TOOL_ANNOUNCE = {
    "open_app": "abrir aplicativo",
    "run_command": "executar comando no terminal",
    "search_web": "pesquisar na web",
    "type_text": "digitar texto",
    "keyboard_hotkey": "pressionar teclas de atalho",
    "mouse_move": "mover o mouse",
    "mouse_click": "clicar com o mouse",
    "mouse_scroll": "rolar a tela",
    "screenshot": "capturar a tela",
    "analyze_screen": "analisar a tela com visão computacional",
    "screen_capture": "capturar tela",
    "screen_ocr": "ler texto da tela",
    "screen_ask": "perguntar sobre a tela",
    "clipboard_get": "ler área de transferência",
    "clipboard_set": "copiar para área de transferência",
    "keyboard_type": "digitar texto",
    "file_list": "listar arquivos",
    "file_create": "criar arquivo",
    "file_delete": "deletar arquivo",
    "file_copy": "copiar arquivo",
    "file_move": "mover arquivo",
    "app_launch": "abrir aplicativo",
    "app_kill": "fechar aplicativo",
    "app_list": "listar processos",
    "system_info": "info do sistema",
    "system_run": "executar comando",
    "browser_open": "abrir navegador",
    "web_fetch": "ler conteúdo de site",
    "web_open": "abrir site no navegador",
    "remember": "salvar na memória",
    "recall": "recuperar da memória",
    "get_clipboard": "ler área de transferência",
    "get_system_info": "obter informações do sistema",
    "knowledge_query": "consultar a base de conhecimento",
    "knowledge_learn_file": "aprender um arquivo",
    "knowledge_learn_dir": "aprender um diretório",
    "semantic_remember": "memorizar um fato",
    "semantic_recall": "buscar fatos na memória",
    "episodic_query": "consultar o histórico",
    "procedural_learn": "aprender um procedimento",
    "procedural_recall": "recuperar um procedimento",
    "agent_run": "iniciar tarefa complexa com o agente autônomo",
    "browser_navigate": "navegar no navegador",
    "browser_search": "pesquisar no navegador",
    "browser_click": "clicar em elemento da página",
    "browser_fill": "preencher formulário",
    "browser_extract": "extrair texto da página",
    "gui_find_click_image": "localizar imagem na tela e clicar",
    "gui_find_click_text": "localizar texto na tela e clicar",
    "face_register": "registrar rosto",
    "face_auth": "autenticar por rosto",
    "reminder_add": "criar lembrete",
    "reminder_cron": "agendar tarefa",
    "reminder_list": "listar lembretes",
    "sandbox_python": "executar código Python",
    "sandbox_bash": "executar comando Bash",
    "sandbox_javascript": "executar JavaScript",
    "plugin_list": "listar plugins",
    "learner_stats": "ver estatísticas de aprendizado",
    "self_evolve": "auto-melhorar o código",
    "computer_use": "controlar o computador",
    "computer_stop": "parar tarefa em andamento",
    "hermes_tool": "chamar ferramenta do Hermes",
    "hermes_delegate": "delegar tarefa complexa",
}


class Orchestrator:
    def __init__(self):
        self.cfg = settings.load()

        self._llm = None
        self._tts = None
        self._base_memory = None
        self._tools = None
        self._agent = None

        self._stt = None
        self._semantic = None
        self._episodic = None
        self._procedural = None
        self._knowledge = None
        self._sandbox = None
        self._scheduler = None
        self._plugins = None
        self._learner = None
        self._gui_automation = None
        self._face_auth = None
        self._browser = None
        self._vision = None

        self._evolve_guard = None
        self._evolve_versioner = None
        self._evolve_editor = None
        self._evolve_agent = None
        self._evolve_restarter = None
        self._telegram_listener = None
        self._keyword_service = None

        self._response_cache = {}

        self._lock = threading.Lock()
        self._running = False
        self._mic_active = False
        self._state = "idle"
        self._mode = "online"
        self._on_state_change = None
        self._on_log = None
        self._on_response = None

    @property
    def tts(self):
        if self._tts is None:
            from tts.engine import TTS
            tts_cfg = self.cfg.get("tts", {})
            self._tts = TTS(
                engine=tts_cfg.get("engine", "edge"),
                voice=tts_cfg.get("voice", "pt-BR-AntonioNeural"),
                speed=tts_cfg.get("speed", 1.0),
            )
        return self._tts

    @property
    def base_memory(self):
        if self._base_memory is None:
            from memory.store import MemoryStore
            self._base_memory = MemoryStore()
        return self._base_memory

    @property
    def stt(self):
        if self._stt is None:
            from stt.vad_stt import VADSTT
            mic_cfg = self.cfg.get("mic", {})
            self._stt = VADSTT(
                device=mic_cfg.get("device", None),
                sample_rate=mic_cfg.get("sample_rate", 16000),
            )
            self.log("🎤 Módulo de áudio ativado", "system")
        return self._stt

    @property
    def semantic(self):
        if self._semantic is None:
            from memory.semantic import SemanticMemory
            self._semantic = SemanticMemory()
            self.log("🧠 Memória semântica ativada", "system")
        return self._semantic

    @property
    def episodic(self):
        if self._episodic is None:
            from memory.episodic import EpisodicMemory
            self._episodic = EpisodicMemory()
            self.log("📅 Memória episódica ativada", "system")
        return self._episodic

    @property
    def procedural(self):
        if self._procedural is None:
            from memory.procedural import ProceduralMemory
            self._procedural = ProceduralMemory()
            self.log("📋 Memória procedural ativada", "system")
        return self._procedural

    @property
    def knowledge(self):
        if self._knowledge is None:
            from brain.knowledge import KnowledgeBase
            self._knowledge = KnowledgeBase()
            self.log("📚 Base de conhecimento ativada", "system")
        return self._knowledge

    @property
    def sandbox(self):
        if self._sandbox is None:
            from sandbox.sandbox import CodeSandbox
            self._sandbox = CodeSandbox()
            self.log("🏖️ Sandbox ativada", "system")
        return self._sandbox

    @property
    def scheduler(self):
        if self._scheduler is None:
            from scheduler.scheduler import Scheduler
            self._scheduler = Scheduler()
            self._scheduler.set_callback(self._on_reminder)
            self.log("⏰ Agendador ativado", "system")
        return self._scheduler

    @property
    def plugins(self):
        if self._plugins is None:
            from plugins.loader import PluginLoader
            self._plugins = PluginLoader()
            self._plugins.discover()
            self.log("🔌 Plugins ativados", "system")
        return self._plugins

    @property
    def learner(self):
        if self._learner is None:
            from learning.learner import Learner
            self._learner = Learner()
            self.log("📖 Aprendizado ativado", "system")
        return self._learner

    @property
    def gui_automation(self):
        if self._gui_automation is None:
            from vision.gui_automation import GUIAutomation
            self._gui_automation = GUIAutomation()
            self.log("🖱️ Automação GUI ativada", "system")
        return self._gui_automation

    @property
    def face_auth(self):
        if self._face_auth is None:
            from auth.face import FaceAuth
            self._face_auth = FaceAuth()
            self.log("👤 Reconhecimento facial ativado", "system")
        return self._face_auth

    @property
    def browser(self):
        if self._browser is None:
            from browser.automator import BrowserAutomator
            self._browser = BrowserAutomator()
            self.log("🌐 Navegador ativado", "system")
        return self._browser

    @property
    def vision(self):
        if self._vision is None:
            from vision.screen_capture import ScreenCapture
            vision_cfg = self.cfg.get("vision", {})
            self._vision = ScreenCapture(model=vision_cfg.get("model", None))
            self.log("👁️ Visão computacional ativada", "system")
        return self._vision

    @property
    def evolve_guard(self):
        if self._evolve_guard is None:
            from agent.self_guard import SelfGuard
            evolve_cfg = self.cfg.get("evolution", {})
            self._evolve_guard = SelfGuard(max_changes=evolve_cfg.get("max_changes_per_hour", 5))
        return self._evolve_guard

    @property
    def evolve_versioner(self):
        if self._evolve_versioner is None:
            from agent.self_versioner import SelfVersioner
            evolve_cfg = self.cfg.get("evolution", {})
            self._evolve_versioner = SelfVersioner(repo_path=evolve_cfg.get("git_repo_path"))
        return self._evolve_versioner

    @property
    def evolve_editor(self):
        if self._evolve_editor is None:
            from agent.self_editor import SelfEditor
            self._evolve_editor = SelfEditor(versioner=self.evolve_versioner)
        return self._evolve_editor

    @property
    def evolve_agent(self):
        if self._evolve_agent is None:
            from agent.self_evolve import SelfAgent
            self._evolve_agent = SelfAgent(
                llm=self.llm,
                guard=self.evolve_guard,
                editor=self.evolve_editor,
                versioner=self.evolve_versioner,
            )
            self.log("⚡ Auto-evolução ativada", "system")
        return self._evolve_agent

    @property
    def evolve_restarter(self):
        if self._evolve_restarter is None:
            from agent.self_restarter import SelfRestarter
            self._evolve_restarter = SelfRestarter()
        return self._evolve_restarter

    @property
    def agent(self):
        if self._agent is None:
            from agent.agent import AutonomousAgent
            self._agent = AutonomousAgent(
                llm=self.llm,
                tool_registry=self.tools,
                knowledge_base=self.knowledge,
                episodic_memory=self.episodic,
                semantic_memory=self.semantic,
            )
            self.tools.agent = self._agent
            self.log("🤖 Agente autônomo ativado", "system")
        return self._agent

    @property
    def tools(self):
        if self._tools is None:
            from core.tools import ToolRegistry
            self._tools = ToolRegistry(self)
        return self._tools

    @property
    def telegram_listener(self):
        if self._telegram_listener is None:
            from agent.telegram_listener import TelegramListener
            self._telegram_listener = TelegramListener(on_message=self._process_telegram)
            telegram_cfg = self.cfg.get("telegram", {})
            if telegram_cfg.get("enabled") and telegram_cfg.get("token"):
                self._telegram_listener.start()
                self.log("📱 Telegram ativado", "system")
        return self._telegram_listener

    @property
    def keyword_service(self):
        if self._keyword_service is None:
            from stt.vosk_detector import VoskKeywordService as KeywordService
            self._keyword_service = KeywordService(self)
        return self._keyword_service

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, val):
        self._mode = val

    def _create_llm(self, engine):
        llm_cfg = self.cfg.get("llm", {})
        if engine == "nvidia":
            from llm.nvidia_llm import NvidiaLLM
            key = os.getenv("JARVIS_NVIDIA_API_KEY") or os.getenv("NVIDIA_API_KEY") or llm_cfg.get("api_key")
            return NvidiaLLM(
                api_key=key,
                model=llm_cfg.get("model", "nvidia/nemotron-3-ultra"),
                base_url=llm_cfg.get("url", "https://integrate.api.nvidia.com/v1"),
                temperature=llm_cfg.get("temperature", 0.7),
                max_tokens=llm_cfg.get("max_tokens", 4096)
            )
        else:
            from llm.ollama_llm import OllamaLLM
            return OllamaLLM(
                model=llm_cfg.get("ollama_model", "qwen2.5:3b"),
                url=llm_cfg.get("ollama_url", "http://127.0.0.1:11434")
            )

    def set_mode(self, mode):
        if mode not in ("online", "local"):
            return
        self._mode = mode
        engine_map = {"online": "nvidia", "local": "ollama"}
        self._llm = self._create_llm(engine_map[mode])
        self.log(f"🔄 Modo alterado para: {mode.upper()} ({engine_map[mode]})", "system")

    @property
    def llm(self):
        if self._llm is None:
            engine_map = {"online": "nvidia", "local": "ollama"}
            self._llm = self._create_llm(engine_map[self._mode])
        return self._llm

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value
        if self._on_state_change:
            self._on_state_change(value)

    def set_callbacks(self, on_state=None, on_log=None, on_response=None):
        self._on_state_change = on_state
        self._on_log = on_log
        self._on_response = on_response

    def _on_reminder(self, message):
        self.log(f"⏰ LEMBRETE: {message}", "system")
        self._finalize(f"Lembrete: {message}")

    def log(self, msg, tag="jarvis"):
        if self._on_log:
            self._on_log(msg, tag)

    def start(self):
        self._running = True
        self.state = "idle"
        self.log("Jarvis online. Sistemas prontos sob demanda.", "system")
        if self.cfg.get("telegram", {}).get("enabled"):
            self.telegram_listener
        self.keyword_service.start()
        threading.Thread(target=self._prewarm, daemon=True).start()
        self._start_api_bridge()

    def _start_api_bridge(self):
        try:
            from jarvis_api import start_api_thread
            start_api_thread()
            self.log("🌉 API Bridge iniciado na porta 8765 (Hermes ↔ JARVIS)", "system")
        except Exception as e:
            self.log(f"⚠️ API Bridge falhou: {e}", "error")

    def _prewarm(self):
        self.log("🔥 Pré-aquecendo modelo...", "system")
        if self._mode == "local":
            ok = self.llm.warmup()
            if ok:
                self.log(f"✅ Ollama pronto: {self.llm.model}", "system")
            else:
                self.log("⚠️ Ollama não disponível, inicie com 'ollama serve'", "system")
        else:
            self.log("☁️ Modo online — NVIDIA pronto sob demanda", "system")

    def stop(self):
        self._running = False
        self.state = "idle"
        if self._scheduler:
            self._scheduler.stop()

    def push_to_talk(self):
        if self._mic_active:
            self._mic_active = False
            self.state = "processing"
            self.log("Processando áudio...", "system")
            text = self.stt.stop_and_transcribe()
            if text:
                self.log(f"Você: {text}", "user")
                self.state = "thinking"
                if self._episodic:
                    self._episodic.add_episode("user_command", text[:200], importance=0.5)
                if not self._route_command(text):
                    self._process_with_llm(text)
            else:
                self.log("Nada captado.", "system")
                self.state = "idle"
        else:
            self._mic_active = True
            self.state = "listening"
            self.log("🎤 Gravando... clique novamente para parar", "system")
            self.stt.start_capture()
        return self._mic_active

    def _is_simple_query(self, text):
        t = text.lower().strip()
        simple = re.match(
            r"^(oi|ola|olá|hey|hi|hello|tudo bem|bom dia|boa tarde|boa noite"
            r"|obrigado|valeu|brigado|sim|não|nao|talvez|ok|okay"
            r"|qual (é|e) (a|o) (capital|maior|menor)|quem (é|e)"
            r"|que (horas|hora|dia|data|dia (é|e) hoje)"
            r"|como (vai|est[aá]|ta|tá))",
            t,
        )
        if simple:
            return True
        return len(t) < 60

    def _route_command(self, text):
        t = text.lower().strip()

        if self._try_procedural_recall(t):
            return True

        if re.match(r"^modo\s+(local|offline|reserva)$", t):
            self.set_mode("local")
            self._finalize("Modo local ativado. Usando Ollama como assistente.")
            return True

        if re.match(r"^modo\s+(online|nvidia|hermes|normal)$", t):
            self.set_mode("online")
            self._finalize("Modo online ativado. Usando NVIDIA Hermes como assistente.")
            return True

        patterns = [
            (r"^(abra|abrir|open|inicie|iniciar|lance|lancar)\s+(.+)$", self._cmd_open),
            (r"^(tire|capture|faca\s+um\s+print|print|screenshot)", self._cmd_screenshot),
            (r"^(execute|executar|rode|rodar|run)\s*:?\s*(.+)$", self._cmd_run),
            (r"^(pesquise|pesquisar|busque|buscar|procure|procurar|google)\s+(.+)$", self._cmd_search),
            (r"^(lembre|memorize|salve|guarde|remember)\s+(.+)$", self._cmd_remember),
            (r"^(qual\s+(é|e)\s+meu\s+nome|qual\s+(é|e)\s+o\s+meu\s+nome|o\s+que\s+lembra|recall|lembra\s+de\s+mim|como\s+eu\s+me\s+chamo)", self._cmd_recall_name),
            (r"^(info|informacoes|informações|dados\s+do\s+sistema|sistema|system)", self._cmd_sysinfo),
            (r"^(liste|listar|mostre|mostrar|arquivos)\s+(.+)$", self._cmd_list),
            (r"^(analise|analisar|veja|olhe)\s+(a\s+)?tela", self._cmd_analyze),
            (r"^(digite|escreva|type|tecle|texte)\s+(.+)$", self._cmd_type),
            (r"^(clique|click|clicar)\s*(left|right|middle|esquerdo|direito)?\s*(em|no|na)?\s*(\d+)\s*[, ]\s*(\d+)$", self._cmd_click),
            (r"^(mova|mover|move|mouse)\s*(para)?\s*(\d+)\s*[, ]\s*(\d+)$", self._cmd_mouse_move),
            (r"^(role|rolar|scroll)\s*(para\s+)?(baixo|cima)?\s*(\d+)?$", self._cmd_scroll),
            (r"^(acesse|navegue|navegar|visite|abrir.url|url|web)\s+(.+)$", self._cmd_web_open),
            (r"^(leia|ler|pegar)\s+(o\s+)?(site|url|pagina|página|conteudo|conteúdo)\s+(.+)$", self._cmd_web_fetch),
            (r"^(aprenda|aprender|estude|estudar|indexe|indexar)\s+(.+)$", self._cmd_learn),
            (r"^(busque|consultar|consulte)\s+na\s+(base|conhecimento|memoria|memória)\s+(.+)$", self._cmd_knowledge_query),
            (r"^(lembrete|alarme|alerta|agende|agendar)\s+(.+)$", self._cmd_reminder),
            (r"^(codigo|código|python|roda|execute)\s+script\s+(.+)$", self._cmd_code),
            (r"^(agente|jarvis\s+faça|jarvis\s+faz|tarefa)\s+(.+)$", self._cmd_agent),
            (r"^(navegador|browser)\s+(.+)$", self._cmd_browser),
            (r"^(plugin|plugins)\s*(.+)?$", self._cmd_plugin),
            (r"^(o\s+que\s+aconteceu|historico|histórico|resumo\s+do\s+dia)\s*(.+)?$", self._cmd_episodic),
            (r"^(quem\s+sou|autenticar|auth|reconhecer)\s*(.+)?$", self._cmd_auth),
            (r"^(cria|criar|gere|gerar|construa|faca\s+um\s+app|faz\s+um\s+app|crie)\s+(.+)$", self._cmd_app_builder),
            (r"^(controla|controle|usa\s+o\s+computador|computer\s+use)\s*(o\s+computador\s*)?[:\-]?\s*(.+)$", self._cmd_computer),
            (r"^(aprenda\s+procedimento|ensine|learn_procedure|procedural_learn)\s+(.+?)(?:\s*:\s*|\s+)(.+)$", self._cmd_procedural_learn),
            (r"^(execute\s+procedimento|relembre|replay|procedural_recall)\s+(.+)$", self._cmd_procedural_recall),
        ]

        for pattern, handler in patterns:
            m = re.match(pattern, t)
            if m:
                self.state = "processing"
                handler(m)
                self._auto_learn_command(text, handler.__name__, m.group(0) if m.lastindex else "")
                return True
        return False

    def _extract_procedure_name(self, text: str) -> str:
        words = re.sub(r'[^a-z0-9\s]', '', text.lower().strip())[:50].split()
        return '_'.join(words[:6]) if words else f'proc_{int(time.time())}'

    def _auto_learn_command(self, text: str, handler_name: str, params: str = ""):
        if not self._procedural:
            return
        name = self._extract_procedure_name(text)
        step = f"{handler_name}: {params[:100]}" if params else f"{handler_name}: {text[:100]}"
        self._procedural.learn_procedure(
            name=name,
            steps=[step],
            description=f"{text[:150]}",
            category="command"
        )

    def _try_procedural_recall(self, text: str) -> bool:
        if not self._procedural:
            return False
        try:
            all_procs = self._procedural.recall_procedure()
        except Exception:
            return False
        if not all_procs:
            return False

        text_lower = text.lower()
        best = None
        best_score = 0

        for p in all_procs:
            desc = p.get("description", "").lower().replace("como ", "")
            keywords = {w for w in desc.split() if len(w) > 3}
            if not keywords:
                continue
            score = sum(1 for kw in keywords if kw in text_lower) / len(keywords)
            if score > best_score:
                best_score = score
                best = p

        if best and best_score >= 0.4:
            name = best["name"]
            cat = best.get("category", "")
            self.state = "processing"
            self.log(f"📖 Já sei! Replay: {name} (score {best_score:.0%})", "system")
            self.tts.speak_async(f"Já sei como fazer! Executando {name}")

            def run_replay(n=name, category=cat):
                if category == "computer_use":
                    cu = agent.computer_use.ComputerUse(llm=self.llm, orchestrator=self)
                    result = cu.replay_from_memory(n)
                else:
                    result = self.tools.execute("procedural_replay", name=n)
                    if isinstance(result, str):
                        result = {"success": "Falha" not in result, "steps": 0, "summary": result}
                msg = f"Procedimento '{n}' executado" if result.get("success") else f"Falha: {result.get('summary', result)}"
                self._finalize(msg)

            threading.Thread(target=run_replay, daemon=True).start()
            return True
        return False

    def _strip_articles(self, s):
        return re.sub(r"^(o|a|os|as|um|uma|uns|umas)\s+", "", s).strip()

    def _cmd_open(self, m):
        app = self._strip_articles(m.group(2).strip())
        result = self.tools.execute("open_app", app_name=app)
        self.log(f"⚙ Abrindo: {app}", "system")
        self.log(f"  → {result}", "system")
        self._finalize(f"{app} aberto com sucesso.")

    def _cmd_screenshot(self, m):
        result = self.tools.execute("screenshot")
        self.log(f"⚙ Print da tela", "system")
        self.log(f"  → {result}", "system")
        self._finalize("Print da tela salvo com sucesso.")

    def _cmd_run(self, m):
        cmd = m.group(2).strip()
        result = self.tools.execute("run_command", command=cmd)
        self.log(f"⚙ Comando: {cmd}", "system")
        self.log(f"  → {result[:300]}", "system")
        self._finalize(f"Comando executado. Saída: {result[:200]}")

    def _cmd_search(self, m):
        query = self._strip_articles(m.group(2).strip())
        query = re.sub(r"^(sobre|acerca|a respeito)\s+", "", query).strip()
        self.log(f"⚙ Pesquisando: {query}", "system")
        result = self.tools.execute("search_web", query=query)
        self.log(f"  → {result[:200]}", "system")
        self._finalize(f"Resultados: {result[:300]}")

    def _cmd_remember(self, m):
        text = m.group(2).strip()
        key = "nome_usuario"
        val = text
        if "que meu nome" in text or "meu nome" in text:
            parts = re.split(r"\s(é|e)\s", text, maxsplit=1)
            val = parts[-1].strip().rstrip(".") if len(parts) > 1 else text
        elif "que " in text and " " in text:
            val = text
        self.tools.execute("remember", key=key, value=val)
        self.tools.execute("semantic_remember", fact=f"O nome do usuário é {val}", category="usuario")
        self.log(f"⚙ Memoria: {key} = {val}", "system")
        self._finalize(f"Lembrei! Seu nome é {val}.")

    def _cmd_recall_name(self, m):
        val = self.tools.execute("recall", key="nome_usuario")
        self.log(f"⚙ Recall: nome_usuario", "system")
        self.log(f"  → {val}", "system")
        self._finalize(f"Claro! {val}" if "Não encontrei" not in val else "Ainda não sei seu nome. Diga 'lembre que meu nome é ...'")

    def _cmd_sysinfo(self, m):
        info = self.tools.execute("get_system_info")
        self.log(f"⚙ Info sistema", "system")
        self._finalize(f"Sistema: {info}")

    def _cmd_list(self, m):
        path = m.group(2).strip() if m.lastindex >= 2 else "/home/alexkali"
        result = self.tools.execute("list_files", path=path)
        self.log(f"⚙ Listando: {path}", "system")
        self._finalize(f"Arquivos em {path}:\n{result}")

    def _cmd_analyze(self, m):
        self.log(f"⚙ Analisando tela...", "system")
        self.tools.execute("screenshot")
        analysis = self.tools.execute("analyze_screen")
        self.log(f"  → {analysis[:200]}", "system")
        self._finalize(f"Análise da tela: {analysis[:300]}")

    def _cmd_type(self, m):
        text = m.group(2).strip()
        result = self.tools.execute("type_text", text=text)
        self.log(f"⚙ Digitando: {text[:50]}", "system")
        self._finalize(result)

    def _cmd_click(self, m):
        button = m.group(2) or "left"
        btn_map = {"esquerdo": "left", "direito": "right", "middle": "middle"}
        button = btn_map.get(button, button)
        g4, g5 = m.group(4), m.group(5)
        if g4 and g5:
            x, y = int(g4), int(g5)
            self.tools.execute("mouse_move", x=x, y=y)
        result = self.tools.execute("mouse_click", button=button)
        self.log(f"⚙ Clique {button}", "system")
        self._finalize(result)

    def _cmd_mouse_move(self, m):
        x, y = int(m.group(3)), int(m.group(4))
        result = self.tools.execute("mouse_move", x=x, y=y)
        self.log(f"⚙ Mouse para ({x}, {y})", "system")
        self._finalize(result)

    def _cmd_scroll(self, m):
        direction = m.group(3)
        amount = int(m.group(4)) if m.group(4) else 5
        if direction == "cima":
            amount = -amount
        result = self.tools.execute("mouse_scroll", clicks=amount)
        self.log(f"⚙ Scroll {amount}", "system")
        self._finalize(result)

    def _cmd_web_open(self, m):
        url = self._strip_articles(m.group(2).strip())
        if not url.startswith("http"):
            url = "https://" + url
        self.tools.execute("web_open", url=url)
        self.log(f"⚙ Abrindo: {url}", "system")
        self._finalize(f"Abrindo {url} no navegador.")

    def _cmd_web_fetch(self, m):
        url = self._strip_articles(m.group(4).strip())
        if not url.startswith("http"):
            url = "https://" + url
        self.log(f"⚙ Lendo: {url}", "system")
        result = self.tools.execute("web_fetch", url=url)
        self.log(f"  → {result[:200]}", "system")
        self._finalize(f"Conteúdo: {result[:500]}")

    def _cmd_learn(self, m):
        path = m.group(2).strip()
        path = os.path.expanduser(path)
        if os.path.isdir(path):
            self.log(f"⚙ Indexando diretório: {path}", "system")
            threading.Thread(target=self._learn_dir_async, args=(path,), daemon=True).start()
            self._finalize(f"Indexando {path} em segundo plano...")
        elif os.path.isfile(path):
            result = self.tools.execute("knowledge_learn_file", file_path=path)
            self.log(f"⚙ Indexado: {result}", "system")
            self._finalize(result)
        else:
            self._finalize(f"Caminho não encontrado: {path}")

    def _learn_dir_async(self, path):
        results = self.tools.execute("knowledge_learn_dir", directory=path)
        for r in results[:10]:
            self.log(f"  {r}", "system")
        self.log(f"✅ Indexação concluída", "system")

    def _cmd_knowledge_query(self, m):
        query = m.group(3).strip()
        self.log(f"⚙ Consultando base de conhecimento: {query}", "system")
        result = self.tools.execute("knowledge_query", question=query)
        self.log(f"  → {result[:200]}", "system")
        self._finalize(result[:1000])

    def _cmd_reminder(self, m):
        text = m.group(2).strip()
        time_match = re.search(r"em\s+(\d+)\s*(min|minuto|minutos|seg|segundo|segundos|h|hora|horas)", text)
        if time_match:
            amount = int(time_match.group(1))
            unit = time_match.group(2)
            if unit.startswith("seg"):
                delay = amount / 60
            elif unit.startswith("h"):
                delay = amount * 60
            else:
                delay = amount
            message = re.sub(r"em\s+\d+\s*(min|minuto|minutos|seg|segundo|segundos|h|hora|horas)", "", text).strip()
            result = self.tools.execute("reminder_add", message=message, delay_minutes=int(delay))
            self.log(f"⏰ {result}", "system")
            self._finalize(result)
        else:
            self._finalize("Use: 'lembrete [mensagem] em [N] minutos'")

    def _cmd_code(self, m):
        code = m.group(2).strip()
        self.log(f"⚙ Executando código...", "system")
        result = self.tools.execute("sandbox_python", code=code)
        self.log(f"  → {result[:200]}", "system")
        self._finalize(f"Resultado: {result[:500]}")

    def _cmd_agent(self, m):
        task = m.group(2).strip()
        self.log(f"🤖 Agente recebendo tarefa: {task}", "system")
        self.state = "thinking"

        def run_agent():
            result = self.agent.run(task, on_log=lambda msg, tag: self.log(msg, tag))
            summary = result.get("summary", str(result))
            self._finalize(summary)

        threading.Thread(target=run_agent, daemon=True).start()

    def _cmd_browser(self, m):
        cmd = m.group(2).strip()
        if cmd.startswith("vá para") or cmd.startswith("va para") or cmd.startswith("acesse"):
            url = re.sub(r"^(vá para|va para|acesse|abra|ir para)\s+", "", cmd)
            self.log(f"⚙ Navegando para: {url}", "system")
            result = self.tools.execute("browser_navigate", url=url)
            self._finalize(f"Navegador: {result}")
        elif cmd.startswith("pesquise") or cmd.startswith("busque"):
            query = re.sub(r"^(pesquise|busque|procure)\s+", "", cmd)
            self.log(f"⚙ Pesquisa no navegador: {query}", "system")
            result = self.tools.execute("browser_search", query=query)
            self._finalize(f"Resultados:\n{result[:500]}")
        elif cmd.startswith("clique em"):
            selector = re.sub(r"^clique\s+em\s+", "", cmd)
            self.log(f"⚙ Clicando em: {selector}", "system")
            result = self.tools.execute("browser_click", selector=selector)
            self._finalize(result)
        else:
            self.log(f"⚙ Extraindo página...", "system")
            result = self.tools.execute("browser_extract")
            self._finalize(f"Conteúdo: {result[:500]}")

    def _cmd_plugin(self, m):
        action = (m.group(2) or "").strip()
        if action == "" or action == "lista" or action == "listar":
            result = self.tools.execute("plugin_list")
            self._finalize(f"Plugins:\n{result}")
        else:
            self._finalize("Comandos: 'plugins listar' para ver plugins carregados.")

    def _cmd_episodic(self, m):
        self.log(f"⚙ Consultando histórico...", "system")
        result = self.tools.execute("episodic_query", hour_range=24)
        self._finalize(f"Últimas 24h:\n{result[:500]}" if result else "Nada registrado.")

    def _cmd_auth(self, m):
        self.log(f"⚙ Autenticando...", "system")
        result = self.tools.execute("face_auth")
        self._finalize(result)

    def _cmd_app_builder(self, m):
        desc = m.group(2).strip()
        self.log(f"⚙ AppBuilder: {desc}", "system")
        result = self.tools._extra.app_builder(descricao=desc)
        self.log(f"  → {result[:300]}", "system")
        self._finalize(f"App criado! {result[:200]}")

    def _cmd_computer(self, m):
        goal = m.group(3).strip()
        self.log(f"🖥️ ComputerUse: {goal}", "system")
        self._announce_tool("computer_use", {"goal": goal})

        def run():
            result = self.tools.execute("computer_use", goal=goal)
            if isinstance(result, dict):
                steps = result.get("steps", 0)
                summary = result.get("summary", "ok")
                self._finalize(f"Tarefa concluída em {steps} passos: {summary}")
            else:
                self._finalize(str(result)[:200])

        threading.Thread(target=run, daemon=True).start()

    def _cmd_procedural_learn(self, m):
        name = m.group(2).strip().replace(" ", "_")
        steps_text = m.group(3).strip()
        steps = [s.strip() for s in steps_text.split(",") if s.strip()]
        result = self.procedural.learn_procedure(name=name, steps=steps, category="learned")
        self.log(f"📖 Procedimento '{name}' aprendido manualmente", "system")
        self._finalize(f"Aprendi o procedimento '{name}' com {len(steps)} passos.")

    def _cmd_procedural_recall(self, m):
        name = m.group(2).strip()
        proc = self.procedural.recall_procedure(name=name)
        if proc:
            steps = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(proc["steps"]))
            self._finalize(f"📖 {proc['name']}: {proc['description']}\n{steps}")
        else:
            self._finalize(f"Procedimento '{name}' não encontrado.")

    def _announce_tool(self, name, args):
        friendly = TOOL_ANNOUNCE.get(name, name.replace("_", " "))
        param_str = ""
        if args:
            important_keys = ["query", "command", "app_name", "url", "text", "message",
                              "task", "code", "goal", "question", "key", "value",
                              "source", "dest", "domain", "target", "prompt",
                              "file_path", "directory", "input_path", "output"]
            vals = [str(v) for k, v in args.items()
                    if k in important_keys and isinstance(v, (str, int, float))]
            if vals:
                val = vals[0][:60]
                param_str = f" {val}"
        announcement = f"Vou usar {friendly}{param_str}"
        self.log(f"🔧 {announcement}", "system")
        self._speak_clean(announcement)

    def _clean_text_for_speech(self, text: str) -> str:
        if not text:
            return ""
        # strip markdown/symbols/emojis
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        text = re.sub(r'[*_`#\[\]()~|\\/>+=\-]', '', text)
        text = re.sub(r'\*\*|__|##+|```', '', text)
        # remove emojis and non-Latin chars
        text = re.sub(r'[^\x20-\x7E\xA0-\xFF\u00C0-\u024F\u0250-\u02AF\u0300-\u036F\u1E00-\u1EFF\u2000-\u206F\u2C60-\u2C7F\uA720-\uA7FF]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        return text[:500]

    def _speak_clean(self, text: str):
        """Fala texto limpo - remove símbolos antes de enviar pro TTS"""
        clean = self._clean_text_for_speech(text)
        if clean:
            self.tts.speak_async(clean)

    def _finalize(self, text):
        self.state = "speaking"
        clean_text = self._clean_text_for_speech(text)
        self.log(f"Jarvis: {clean_text}", "jarvis")
        self.base_memory.add_message("assistant", clean_text)
        if self._episodic:
            self._episodic.add_episode("response", clean_text[:200], importance=0.3)
        self._speak_clean(clean_text)
        if self._telegram_listener:
            self._telegram_listener._reply(clean_text)
        self.state = "idle"

    def _process_telegram(self, text):
        self.process_text(text)

    def process_text(self, text):
        if not text.strip():
            return
        self.log(f"Você: {text}", "user")
        self.state = "thinking"
        if self._episodic:
            self._episodic.add_episode("user_command", text[:200], importance=0.5)
        if self._route_command(text):
            return
        self.state = "processing"
        self._process_with_llm(text)

    def _process_with_llm(self, text):
        cache_key = text.lower().strip()
        cached = self._response_cache.get(cache_key)
        if cached:
            self._finalize(cached)
            return

        def process():
            history = self.base_memory.get_history(6)
            extra_context = ""
            is_simple = self._is_simple_query(text)

            if not is_simple:
                try:
                    ctx, _ = self.knowledge.query(text, n_results=2)
                    if ctx:
                        extra_context += f"\nContexto:\n{ctx[:600]}\n"
                except Exception:
                    pass
                try:
                    facts = self.semantic.recall_fact(text, top_k=2)
                    if facts:
                        extra_context += "\nFatos:\n" + "\n".join(f["fact"] for f in facts[:2]) + "\n"
                except Exception:
                    pass

            sys_content = BASE_PROMPT
            if extra_context:
                sys_content += "\n\n" + extra_context.strip()

            messages = [
                {"role": "system", "content": sys_content}
            ]
            messages.extend(history)
            messages.append({"role": "user", "content": text})

            try:
                response = self.llm.chat_with_tools(messages, self.tools.get_relevant_tools(text))
                msg = response.get("message", {})

                if msg.get("tool_calls"):
                    import json as _json
                    tool_seq = []
                    for tc in msg["tool_calls"]:
                        fn = tc.get("function", {})
                        name = fn.get("name", "")
                        args = fn.get("arguments", {})
                        if isinstance(args, str):
                            try:
                                args = _json.loads(args)
                            except Exception:
                                args = {}
                        self._announce_tool(name, args)
                        result = self.tools.execute(name, **args)
                        self.log(f"  → {str(result)[:200]}", "system")
                        tool_seq.append(f"{name}({_json.dumps(args, ensure_ascii=False)[:100]})")
                        messages.append({"role": "tool", "content": str(result)[:4000], "name": name})

                    if len(tool_seq) >= 2 and self._procedural:
                        proc_name = self._extract_procedure_name(text)
                        self._procedural.learn_procedure(
                            name=proc_name,
                            steps=tool_seq,
                            description=text[:150],
                            category="tool_sequence"
                        )
                        self.log(f"📖 Sequência aprendida: '{proc_name}' ({len(tool_seq)} ferramentas)", "system")

                    final = self.llm.chat(messages)
                    self._handle_final(final)
                else:
                    content = msg.get("content", "")
                    if len(self._response_cache) > 200:
                        self._response_cache.clear()
                    self._response_cache[cache_key] = content
                    self._handle_final(content)
            except Exception as e:
                err = f"[ERRO] {e}"
                self.log(err, "error")
                self.state = "idle"

        _POOL.submit(process)

    def _handle_final(self, content):
        if isinstance(content, dict):
            content = content.get("message", {}).get("content", "")
        self.state = "speaking"
        clean_text = self._clean_text_for_speech(content)
        self.log(f"Jarvis: {clean_text}", "jarvis")
        self.base_memory.add_message("assistant", clean_text)
        self._speak_clean(clean_text)
        if self._telegram_listener:
            self._telegram_listener._reply(clean_text)
        self.state = "idle"


