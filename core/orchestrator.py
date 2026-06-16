import os
import re
import threading
from llm.ollama_llm import OllamaLLM
from agent.telegram_listener import TelegramListener
from stt.vad_stt import VADSTT
from tts.engine import TTS
from memory.store import MemoryStore
from memory.semantic import SemanticMemory
from memory.episodic import EpisodicMemory
from memory.procedural import ProceduralMemory
from core.tools import ToolRegistry
from brain.knowledge import KnowledgeBase
from agent.agent import AutonomousAgent
from agent.self_evolve import SelfAgent
from agent.self_editor import SelfEditor
from agent.self_versioner import SelfVersioner
from agent.self_guard import SelfGuard
from agent.self_restarter import SelfRestarter
from browser.automator import BrowserAutomator
from vision.gui_automation import GUIAutomation
from auth.face import FaceAuth
from scheduler.scheduler import Scheduler
from sandbox.sandbox import CodeSandbox
from plugins.loader import PluginLoader
from learning.learner import Learner
import config.settings as settings


class Orchestrator:
    def __init__(self):
        cfg = settings.load()
        self.llm = OllamaLLM()
        mic_cfg = cfg.get("mic", {})
        self.stt = VADSTT(
            device=mic_cfg.get("device", None),
            sample_rate=mic_cfg.get("sample_rate", 16000),
        )
        tts_cfg = cfg.get("tts", {})
        self.tts = TTS(
            engine=tts_cfg.get("engine", "edge"),
            voice=tts_cfg.get("voice", "pt-BR-AntonioNeural"),
            speed=tts_cfg.get("speed", 1.0),
        )

        self.base_memory = MemoryStore()
        self.semantic = SemanticMemory()
        self.episodic = EpisodicMemory()
        self.procedural = ProceduralMemory()
        self.knowledge = KnowledgeBase()
        self.sandbox = CodeSandbox()
        self.scheduler = Scheduler()
        self.plugins = PluginLoader()
        self.learner = Learner()
        self.gui_automation = GUIAutomation()
        self.face_auth = FaceAuth()
        self.browser = BrowserAutomator()

        vision_cfg = cfg.get("vision", {})
        from vision.screen_capture import ScreenCapture
        vision = ScreenCapture(model=vision_cfg.get("model", None))

        self.tools = ToolRegistry(
            memory=self.base_memory,
            vision=vision,
            knowledge=self.knowledge,
            semantic_memory=self.semantic,
            episodic_memory=self.episodic,
            procedural_memory=self.procedural,
            browser=self.browser,
            gui_automation=self.gui_automation,
            face_auth=self.face_auth,
            scheduler=self.scheduler,
            sandbox=self.sandbox,
            plugin_loader=self.plugins,
            learner=self.learner,
        )

        self.agent = AutonomousAgent(
            llm=self.llm,
            tool_registry=self.tools,
            knowledge_base=self.knowledge,
            episodic_memory=self.episodic,
            semantic_memory=self.semantic,
        )
        self.tools.agent = self.agent

        evolve_cfg = cfg.get("evolution", {})
        self.evolve_guard = SelfGuard(max_changes=evolve_cfg.get("max_changes_per_hour", 5))
        self.evolve_versioner = SelfVersioner(repo_path=evolve_cfg.get("git_repo_path"))
        self.evolve_editor = SelfEditor(versioner=self.evolve_versioner)
        self.evolve_agent = SelfAgent(
            llm=self.llm,
            guard=self.evolve_guard,
            editor=self.evolve_editor,
            versioner=self.evolve_versioner,
        )
        self.evolve_restarter = SelfRestarter()
        self.tools.evolution = self.evolve_agent

        telegram_cfg = cfg.get("telegram", {})
        if telegram_cfg.get("enabled") and telegram_cfg.get("token"):
            self.telegram_listener = TelegramListener(on_message=self.process_text)
            self.tools._extra.telegram_listener = self.telegram_listener
            if telegram_cfg.get("auto_start", True):
                self.telegram_listener.start()
        else:
            self.telegram_listener = None

        self.scheduler.set_callback(self._on_reminder)

        self.plugins.discover()

        self._lock = threading.Lock()
        self._running = False
        self._mic_active = False
        self._state = "idle"
        self._on_state_change = None
        self._on_log = None
        self._on_response = None

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
        self.log("Sistemas inicializados. Jarvis online.", "system")
        self.log("🧠 Módulos: Agente + RAG + Memórias + Browser + Visão + Agendador + Sandbox + Plugins", "system")
        self.log(f"📚 Base de conhecimento: {self.knowledge.stats()['total_chunks']} chunks", "system")
        threading.Thread(target=lambda: self.stt.available, daemon=True).start()

    def stop(self):
        self._running = False
        self.state = "idle"
        self.scheduler.stop()

    def toggle_mic(self):
        if self._mic_active:
            self._mic_active = False
            self.state = "idle"
            self.log("Microfone desativado.", "system")
        else:
            self._mic_active = True
            self.state = "listening"
            self.log("Microfone ativado. Aguardando comando...", "system")
        return self._mic_active

    def _strip_articles(self, s):
        return re.sub(r"^(o|a|os|as|um|uma|uns|umas)\s+", "", s).strip()

    def _route_command(self, text):
        t = text.lower().strip()

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
        ]

        for pattern, handler in patterns:
            m = re.match(pattern, t)
            if m:
                self.state = "processing"
                handler(m)
                return True
        return False

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
        path = self.tools.execute("screenshot")
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
        result = self.tools.execute("web_open", url=url)
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

    def _finalize(self, text):
        self.state = "speaking"
        self.log(f"Jarvis: {text}", "jarvis")
        self.base_memory.add_message("assistant", text)
        self.episodic.add_episode("response", text[:200], importance=0.3)
        self.tts.speak_async(text)
        self.state = "idle"

    def process_text(self, text):
        if not text.strip():
            return

        self.log(f"Você: {text}", "user")
        self.state = "thinking"
        self.episodic.add_episode("user_command", text[:200], importance=0.5)

        if self._route_command(text):
            return

        self.state = "processing"

        def process():
            history = self.base_memory.get_history(10)

            knowledge_context = ""
            try:
                ctx, _ = self.knowledge.query(text, n_results=3)
                if ctx:
                    knowledge_context = f"\nContexto da base de conhecimento:\n{ctx[:1000]}\n"
            except Exception:
                pass

            semantic_context = ""
            try:
                facts = self.semantic.recall_fact(text, top_k=3)
                if facts:
                    semantic_context = "\nFatos relevantes:\n" + "\n".join(f["fact"] for f in facts[:3]) + "\n"
            except Exception:
                pass

            procedural_context = ""
            try:
                procs = self.procedural.recall_procedure(category=None)
                if procs:
                    proc_names = ", ".join(p["name"] for p in procs[:5])
                    procedural_context = f"\nProcedimentos disponíveis: {proc_names}\n"
            except Exception:
                pass

            messages = [
                {"role": "system", "content": (
                    "Você é o J.A.R.V.I.S, um assistente de IA pessoal altamente avançado e estiloso. "
                    "Responda de forma direta, inteligente e com um toque de sofisticação. "
                    "Sempre responda em português brasileiro, de forma concisa.\n\n"
                    "CAPACIDADES DISPONÍVEIS:\n"
                    "• Agente autônomo: 'jarvis faça [tarefa complexa]' - planejamento multi-etapas\n"
                    "• Conhecimento (RAG): aprenda arquivos/diretórios, depois pergunte\n"
                    "• Memória semântica: fatos sobre o usuário e o mundo\n"
                    "• Memória episódica: 'o que aconteceu?' - histórico do dia\n"
                    "• Memória procedural: aprender e executar procedimentos\n"
                    "• Navegador: acessar sites, pesquisar, extrair conteúdo\n"
                    "• Automação GUI: localizar imagens/texto na tela e clicar\n"
                    "• Sandbox: executar código Python/JS/Bash\n"
                    "• Lembretes: agendar alarmes e tarefas cron\n"
                    "• Reconhecimento facial: autenticação\n"
                    "• Plugins: sistema extensível\n\n"
                    "Use as ferramentas disponíveis sempre que possível. "
                    "Quando uma tarefa for complexa (múltiplos passos), delegue ao agente autônomo."
                    + knowledge_context + semantic_context + procedural_context
                )}
            ]
            messages.extend(history)
            messages.append({"role": "user", "content": text})

            try:
                response = self.llm.chat_with_tools(messages, self.tools.get_ollama_tools())
                msg = response.get("message", {})

                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        fn = tc.get("function", {})
                        name = fn.get("name", "")
                        args = fn.get("arguments", {})
                        if isinstance(args, str):
                            import json
                            try:
                                args = json.loads(args)
                            except Exception:
                                args = {}
                        self.log(f"⚙ LLM executando: {name}", "system")
                        result = self.tools.execute(name, **args)
                        self.log(f"  → {str(result)[:200]}", "system")
                        messages.append({"role": "tool", "content": str(result)[:2000], "name": name})

                    final = self.llm.chat(messages)
                    self._handle_final(final)
                else:
                    self._handle_final(msg.get("content", ""))
            except Exception as e:
                err = f"[ERRO] {e}"
                self.log(err, "error")
                self.state = "idle"

        threading.Thread(target=process, daemon=True).start()

    def _handle_final(self, content):
        if isinstance(content, dict):
            content = content.get("message", {}).get("content", "")
        self.state = "speaking"
        self.log(f"Jarvis: {content}", "jarvis")
        self.base_memory.add_message("assistant", content)
        self.tts.speak_async(content)
        self.state = "idle"

    def hear_and_respond(self):
        if not self._mic_active:
            return

        self.state = "hotword"
        self.log("Aguardando 'Jarvis'...", "system")

        def loop():
            while self._mic_active:
                try:
                    text = self.stt.listen_for_speech(timeout=3.0)
                    if not text:
                        continue

                    is_wake, command = self.stt._check_wake_word(text)

                    if is_wake:
                        self.log(f"Jarvis detectado!", "system")
                        if command:
                            self.state = "thinking"
                            self.process_text(command)
                        else:
                            self.state = "listening"
                            self.log("Aguardando comando...", "system")
                            cmd = self.stt.listen_for_command(timeout=5.0)
                            if cmd:
                                self.state = "thinking"
                                self.process_text(cmd)
                        self.state = "hotword"
                        self.log("Aguardando 'Jarvis'...", "system")
                except Exception as e:
                    self.log(f"[ERRO ÁUDIO] {e}", "error")

            self.state = "idle"

        threading.Thread(target=loop, daemon=True).start()

