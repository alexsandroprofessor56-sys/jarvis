import os
import subprocess
import platform
import pyautogui
import pyperclip
import webbrowser
import json
from web.search import WebSearch
from core.extra_tools import ExtraTools, EXTRA_TOOLS
from core.tool_router import ToolRouter
from agent.computer_use import ComputerUse


class ToolRegistry:
    def __init__(self, orchestrator):
        self._o = orchestrator
        self.tools = {}
        self._extra = ExtraTools()
        self._computer = ComputerUse(orchestrator=orchestrator)
        self._register_all()

    @property
    def memory(self):
        return self._o.base_memory

    @property
    def vision(self):
        return self._o.vision

    @property
    def knowledge(self):
        return self._o.knowledge

    @property
    def semantic(self):
        return self._o.semantic

    @property
    def episodic(self):
        return self._o.episodic

    @property
    def procedural(self):
        return self._o.procedural

    @property
    def browser(self):
        return self._o.browser

    @property
    def gui(self):
        return self._o.gui_automation

    @property
    def face_auth(self):
        return self._o.face_auth

    @property
    def scheduler(self):
        return self._o.scheduler

    @property
    def sandbox(self):
        return self._o.sandbox

    @property
    def plugins(self):
        return self._o.plugins

    @property
    def learner(self):
        return self._o.learner

    @property
    def agent(self):
        return self._o.agent

    @agent.setter
    def agent(self, val):
        self._o._agent = val

    @property
    def evolution(self):
        return self._o.evolve_agent

    def _register_all(self):
        self.register("open_app", self.tool_open_app,
            "Abrir aplicativo instalado no sistema pelo nome. Use quando o usuário pedir para abrir/iniciar/executar um programa (firefox, code, terminal, spotify, etc).")
        self.register("run_command", self.tool_run_command,
            "Executar comandos shell no terminal. Use para rodar programas de terminal, scripts, comandos de sistema (ls, cd, git, apt, pip, etc).")
        self.register("search_web", self.tool_search_web,
            "Pesquisar na internet. Use quando o usuário perguntar sobre algo atual, notícias, clima, ou informação que você não sabe de cabeça.")
        self.register("type_text", self.tool_type_text,
            "Digitar texto como se fosse teclado. Use quando o usuário pedir para digitar/escrever algo em campos de texto ou formulários.")
        self.register("keyboard_hotkey", self.tool_keyboard_hotkey,
            "Pressionar combinação de teclas (ctrl+c, alt+tab, ctrl+v). Use para atalhos de teclado, copiar/colar, alternar janelas.")
        self.register("mouse_move", self.tool_mouse_move,
            "Mover cursor do mouse para coordenadas (x, y) na tela.")
        self.register("mouse_click", self.tool_mouse_click,
            "Clicar com botão do mouse (left, right, middle) na posição atual do cursor.")
        self.register("mouse_scroll", self.tool_mouse_scroll,
            "Rolar a tela para cima ou para baixo com o scroll do mouse.")
        self.register("screenshot", self.tool_screenshot,
            "Capturar print da tela inteira. Use antes de analyze_screen para dar contexto visual ao Jarvis.")
        self.register("analyze_screen", self.tool_analyze_screen,
            "Analisar o print da tela usando IA de visão computacional e descrever o que vê. Use depois de screenshot.")
        self.register("web_fetch", self.tool_web_fetch,
            "Baixar e ler o conteúdo textual de uma URL. Use para extrair informação de páginas web, artigos, documentação.")
        self.register("web_open", self.tool_web_open,
            "Abrir URL no navegador padrão do sistema para o usuário ver. Use quando o usuário pedir para 'abrir site X' ou 'ir para Y'.")
        self.register("hermes_delegate", self.tool_hermes_delegate,
            "Delegar tarefa complexa para o Hermes (cérebro avançado). Use para planejamento multi-etapas, pesquisa profunda, código, análise, automação web, skills, memória persistente. Args: task (str), use_voice (bool).")
        self.register("remember", self.tool_remember,
            "Salvar informação na memória chave-valor do Jarvis. Use quando o usuário disser 'lembre que ...' ou 'guarda isso'.")
        self.register("recall", self.tool_recall,
            "Recuperar informação salva na memória pela chave. Use quando o usuário perguntar algo que foi memorizado antes.")
        self.register("list_files", self.tool_list_files,
            "Listar arquivos e pastas em um diretório. Use quando o usuário pedir para ver/conferir/listar arquivos.")
        self.register("get_clipboard", self.tool_get_clipboard,
            "Ler o conteúdo atual da área de transferência (copiado pelo usuário).")
        self.register("get_system_info", self.tool_get_system_info,
            "Obter informações do sistema operacional: nome, versão, arquitetura, hostname.")
        self.register("knowledge_query", self.tool_knowledge_query,
            "Buscar conhecimento na base vetorial (RAG). Use quando o usuário perguntar sobre algo que você já aprendeu/indexou antes.")
        self.register("knowledge_learn_file", self.tool_knowledge_learn_file,
            "Ingerir arquivo na base de conhecimento (PDF, DOCX, TXT, imagem). Use quando o usuário pedir para aprender/estudar/indexar um arquivo específico.")
        self.register("knowledge_learn_dir", self.tool_knowledge_learn_dir,
            "Ingerir diretório inteiro na base de conhecimento. Use quando o usuário pedir para aprender/estudar uma pasta inteira.")
        self.register("semantic_remember", self.tool_semantic_remember,
            "Memorizar um fato semântico sobre o usuário ou o mundo. Use para informações que devem ser lembradas a longo prazo.")
        self.register("semantic_recall", self.tool_semantic_recall,
            "Buscar fatos na memória semântica por relevância. Use quando precisar lembrar de algo aprendido sobre o usuário.")
        self.register("episodic_query", self.tool_episodic_query,
            "Consultar memória episódica (histórico de eventos recentes). Use quando o usuário perguntar 'o que aconteceu', 'histórico', 'resumo do dia'.")
        self.register("procedural_learn", self.tool_procedural_learn,
            "Ensinar ao Jarvis um procedimento com passos. Use para aprender rotinas que o usuário repete com frequência.")
        self.register("procedural_recall", self.tool_procedural_recall,
            "Recuperar um procedimento aprendido. Use quando o usuário pedir para executar algo que foi ensinado como procedimento.")
        self.register("procedural_replay", self.tool_procedural_replay,
            "Executar um procedimento salvo na memória procedural pelo nome. Use quando um procedimento já foi aprendido e precisa ser repetido.")
        self.register("agent_run", self.tool_agent_run,
            "Executar tarefa complexa com planejamento multi-etapas. Use para tarefas que exigem múltiplas ações coordenadas.")
        self.register("browser_navigate", self.tool_browser_navigate,
            "Navegar o navegador controlado (Playwright) para uma URL específica.")
        self.register("browser_search", self.tool_browser_search,
            "Pesquisar no Google via navegador controlado e extrair os resultados da página.")
        self.register("browser_click", self.tool_browser_click,
            "Clicar em um elemento da página atual por seletor CSS (classe, ID, tag).")
        self.register("browser_fill", self.tool_browser_fill,
            "Preencher campo de formulário na página atual com um valor (por seletor CSS).")
        self.register("browser_extract", self.tool_browser_extract,
            "Extrair todo o texto visível da página atual no navegador controlado.")
        self.register("gui_find_click_image", self.tool_gui_find_click_image,
            "Localizar uma imagem na tela por template matching e clicar nela. Use para clicar em botões/ícones sem seletor CSS.")
        self.register("gui_find_click_text", self.tool_gui_find_click_text,
            "Localizar texto na tela via OCR e clicar nele. Use para clicar em elementos que têm texto visível.")
        self.register("face_register", self.tool_face_register,
            "Registrar o rosto do usuário para autenticação facial futura. Use quando o usuário pedir para cadastrar/configurar reconhecimento facial.")
        self.register("face_auth", self.tool_face_auth,
            "Autenticar o usuário por reconhecimento facial. Use quando o usuário pedir para verificar/autenticar identidade.")
        self.register("reminder_add", self.tool_reminder_add,
            "Criar um lembrete com delay em minutos. Use quando o usuário disser 'lembrete ... em X minutos'.")
        self.register("reminder_cron", self.tool_reminder_cron,
            "Agendar tarefa com expressão cron para execução recorrente. Use para rotinas diárias/semanais.")
        self.register("reminder_list", self.tool_reminder_list,
            "Listar todos os lembretes ativos e agendados.")
        self.register("sandbox_python", self.tool_sandbox_python,
            "Executar código Python. Use quando o usuário pedir para rodar código ou testar script.")
        self.register("sandbox_bash", self.tool_sandbox_bash,
            "Executar comandos Bash em ambiente isolado (sandbox) sem afetar o sistema real.")
        self.register("sandbox_javascript", self.tool_sandbox_javascript,
            "Executar código JavaScript em ambiente isolado (sandbox).")
        self.register("plugin_list", self.tool_plugin_list,
            "Listar todos os plugins carregados pelo sistema de plugins do Jarvis.")
        self.register("learner_stats", self.tool_learner_stats,
            "Ver estatísticas de aprendizado: comandos mais usados, taxa de sucesso, padrões.")
        self.register("self_evolve", self.tool_self_evolve,
            "Auto-melhorar o código do Jarvis (analisar, editar, versionar, reiniciar). Use quando o usuário sugerir melhoria ou pedir para o Jarvis se atualizar.")
        self.register("computer_use", self.tool_computer_use,
            "Controlar o computador como uma pessoa faria: ver tela, clicar, digitar, abrir apps. Use para tarefas complexas de automação GUI.")
        self.register("computer_stop", self.tool_computer_stop,
            "Parar a tarefa em andamento do ComputerUseAgent imediatamente.")
        self.register("hermes_delegate", self.tool_hermes_delegate,
            "Delegar tarefa complexa para o Hermes (cérebro avançado): planejamento multi-etapas, skills auto-evolutivas, browser automation, code execution, web search, file ops. Use para tarefas que exigem raciocínio profundo, pesquisa, programação, automação web complexa. Args: task (str), use_voice (bool).")
        self.register("hermes_tool", self.tool_hermes_tool,
            "Chamar ferramenta específica do Hermes (browser avançado, web_search, terminal, code_execution, skills, memória, visão). Args: name (str) nome da ferramenta, args (dict) argumentos da ferramenta.")
        self._register_hermes_tools()
        for name, method, desc, schema in EXTRA_TOOLS:
            bound = method.__get__(self._extra, type(self._extra))
            self.register(name, bound, desc, schema)

    def register(self, name, func, description="", schema=None):
        self.tools[name] = {"func": func, "description": description, "schema": schema}

    def _tool_schema(self, name, info):
        params = {"type": "object", "properties": {}, "required": []}
        if info.get("schema") is not None:
            params["properties"] = info["schema"]
            params["required"] = list(info["schema"].keys())
            return {"type": "function", "function": {"name": name, "description": info["description"], "parameters": params}}
        schemas = {
            "open_app": {"app_name": {"type": "string"}}, "run_command": {"command": {"type": "string"}},
            "search_web": {"query": {"type": "string"}}, "type_text": {"text": {"type": "string"}},
            "keyboard_hotkey": {"keys": {"type": "array", "items": {"type": "string"}}},
            "mouse_move": {"x": {"type": "integer"}, "y": {"type": "integer"}},
            "mouse_click": {"button": {"type": "string", "enum": ["left", "right", "middle"]}},
            "mouse_scroll": {"clicks": {"type": "integer"}},
            "remember": {"key": {"type": "string"}, "value": {"type": "string"}},
            "recall": {"key": {"type": "string"}},
            "list_files": {"path": {"type": "string"}},
            "web_fetch": {"url": {"type": "string"}}, "web_open": {"url": {"type": "string"}},
            "knowledge_query": {"question": {"type": "string"}, "n_results": {"type": "integer"}},
            "knowledge_learn_file": {"file_path": {"type": "string"}},
            "knowledge_learn_dir": {"directory": {"type": "string"}, "recursive": {"type": "boolean"}},
            "semantic_remember": {"fact": {"type": "string"}, "category": {"type": "string"}, "confidence": {"type": "number"}},
            "semantic_recall": {"query": {"type": "string"}, "top_k": {"type": "integer"}},
            "episodic_query": {"hour_range": {"type": "integer"}, "episode_type": {"type": "string"}},
            "procedural_learn": {"name": {"type": "string"}, "steps": {"type": "array", "items": {"type": "string"}}, "description": {"type": "string"}, "category": {"type": "string"}},
            "procedural_recall": {"name": {"type": "string"}, "category": {"type": "string"}},
            "procedural_replay": {"name": {"type": "string"}},
            "agent_run": {"task": {"type": "string"}},
            "browser_navigate": {"url": {"type": "string"}},
            "browser_search": {"query": {"type": "string"}},
            "browser_click": {"selector": {"type": "string"}},
            "browser_fill": {"selector": {"type": "string"}, "value": {"type": "string"}},
            "browser_extract": {},
            "gui_find_click_image": {"template_path": {"type": "string"}, "threshold": {"type": "number"}},
            "gui_find_click_text": {"text": {"type": "string"}},
            "face_register": {"user_id": {"type": "string"}},
            "face_auth": {},
            "reminder_add": {"message": {"type": "string"}, "delay_minutes": {"type": "integer"}},
            "reminder_cron": {"message": {"type": "string"}, "cron_expr": {"type": "string"}},
            "reminder_list": {},
            "sandbox_python": {"code": {"type": "string"}},
            "sandbox_bash": {"code": {"type": "string"}},
            "sandbox_javascript": {"code": {"type": "string"}},
            "plugin_list": {},
            "learner_stats": {},
            "self_evolve": {"goal": {"type": "string"}, "auto_approve": {"type": "boolean"}},
            "hermes_delegate": {"task": {"type": "string"}, "use_voice": {"type": "boolean"}},
            "hermes_tool": {"name": {"type": "string"}, "args": {"type": "object"}},
        }
        if name in schemas:
            params["properties"] = schemas[name]
            if name in ("open_app", "run_command", "search_web", "type_text", "query", "fact",
                        "file_path", "question", "url", "task", "code", "message", "selector", "value",
                        "user_id", "name", "directory", "key", "command", "text"):
                for req_key in schemas[name]:
                    params["required"].append(req_key)
        if name in ("remember",):
            params["required"] = ["key", "value"]
        if name in ("mouse_move",):
            params["required"] = ["x", "y"]
        if name in ("keyboard_hotkey",):
            params["required"] = ["keys"]
        if name in ("semantic_remember", "procedural_learn", "reminder_add", "reminder_cron",
                    "knowledge_learn_file", "knowledge_query", "agent_run", "browser_navigate",
                    "browser_search", "browser_fill", "gui_find_click_image", "gui_find_click_text",
                    "sandbox_python", "sandbox_bash", "sandbox_javascript", "face_register",
                    "self_evolve", "hermes_delegate", "hermes_tool"):
            params["required"] = list(params["properties"].keys())
        return {"type": "function", "function": {"name": name, "description": info["description"], "parameters": params}}

    def get_ollama_tools(self):
        return [self._tool_schema(name, info) for name, info in self.tools.items()]

    def get_relevant_tools(self, query, top_n=12):
        if not hasattr(self, '_router') or self._router is None:
            self._router = ToolRouter(self.tools)
        return self._router.get_relevant_schemas(query, top_n=top_n)

    def execute(self, name, **kwargs):
        tool = self.tools.get(name)
        if not tool:
            return f"[ERRO] Ferramenta '{name}' não encontrada."
        try:
            result = tool["func"](**kwargs)
            if self.learner:
                self.learner.record_command(name, tool_used=name, success=True)
            return result
        except Exception as e:
            if self.learner:
                self.learner.record_command(name, tool_used=name, success=False)
            return f"[ERRO] {e}"

    COMMON_APPS = {
        "firefox": ["firefox", "firefox-esr"],
        "chromium": ["chromium", "chromium-browser", "google-chrome"],
        "chrome": ["google-chrome", "chromium", "chromium-browser"],
        "terminal": ["gnome-terminal", "konsole", "xfce4-terminal", "terminator", "xterm", "alacritty", "kitty"],
        "code": ["code", "codium", "vscode"],
        "gedit": ["gedit", "pluma", "mousepad", "nano"],
        "nautilus": ["nautilus", "dolphin", "thunar", "pcmanfm", "nemo", "caja"],
        "calculator": ["gnome-calculator", "kcalc", "qalculate-gtk"],
        "files": ["nautilus", "dolphin", "thunar", "pcmanfm", "nemo", "caja"],
        "browser": ["firefox", "chromium", "google-chrome", "brave-browser"],
        "gerenciador de arquivos": ["nautilus", "dolphin", "thunar", "pcmanfm", "nemo", "caja"],
        "arquivos": ["nautilus", "dolphin", "thunar", "pcmanfm", "nemo", "caja"],
        "navegador": ["firefox", "chromium", "google-chrome"],
        "explorador": ["nautilus", "dolphin", "thunar", "pcmanfm", "nemo", "caja"],
        "calculadora": ["gnome-calculator", "kcalc", "qalculate-gtk"],
        "editor": ["gedit", "code", "pluma", "mousepad", "nano", "vim"],
        "texto": ["gedit", "code", "pluma", "mousepad"],
    }

    def tool_open_app(self, app_name=None):
        if not app_name:
            return "Nome do aplicativo não fornecido."
        system = platform.system()
        app_name = app_name.lower().strip()
        candidates = [app_name]
        if app_name in self.COMMON_APPS:
            candidates.extend(self.COMMON_APPS[app_name])
        tried = []
        for candidate in candidates:
            try:
                if system == "Linux":
                    proc = subprocess.Popen([candidate], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                    proc.poll()
                    if proc.returncode is None or proc.returncode == 0:
                        return f"Aplicativo '{app_name}' aberto com '{candidate}'."
                elif system == "Windows":
                    os.startfile(candidate)
                    return f"Aplicativo '{app_name}' aberto."
                elif system == "Darwin":
                    subprocess.Popen(["open", "-a", candidate])
                    return f"Aplicativo '{app_name}' aberto."
                tried.append(candidate)
            except Exception:
                tried.append(candidate)
                continue
        return f"Não foi possível abrir '{app_name}'. Tentei: {', '.join(tried)}"

    def tool_run_command(self, command=None):
        if not command:
            return "Comando não fornecido."
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout or result.stderr
            return output[:2000] if output else "Comando executado sem saída."
        except subprocess.TimeoutExpired:
            return "Comando excedeu o tempo limite de 30s."
        except Exception as e:
            return f"Erro ao executar comando: {e}"

    def tool_search_web(self, query=None):
        if not query:
            return "Consulta não fornecida."
        ws = WebSearch()
        return ws.search_text(query)

    def tool_type_text(self, text=None):
        if not text:
            return "Texto não fornecido."
        pyautogui.write(text)
        return "Texto digitado."

    def tool_keyboard_hotkey(self, keys=None):
        if not keys:
            return "Teclas não fornecidas."
        if isinstance(keys, str):
            keys = keys.split("+")
        pyautogui.hotkey(*keys)
        return f"Teclas {keys} pressionadas."

    def tool_mouse_move(self, x=None, y=None):
        if x is None or y is None:
            return "Coordenadas não fornecidas."
        pyautogui.moveTo(x, y)
        return f"Mouse movido para ({x}, {y})."

    def tool_mouse_click(self, button="left"):
        pyautogui.click(button=button)
        return f"Clique {button}."

    def tool_mouse_scroll(self, clicks=3):
        pyautogui.scroll(clicks)
        return f"Rolagem de {clicks} clicks."

    def tool_web_fetch(self, url=None):
        if not url:
            return "URL não fornecida."
        try:
            import requests
            from bs4 import BeautifulSoup
            resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                return f"Erro HTTP {resp.status_code} ao acessar {url}"
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            lines = [l for l in text.split("\n") if len(l.strip()) > 30]
            return "\n".join(lines[:60])[:3000]
        except ImportError:
            return "Pacotes requests/beautifulsoup4 nao instalados."
        except Exception as e:
            return f"Erro ao acessar {url}: {e}"

    def tool_web_open(self, url=None):
        if not url:
            return "URL não fornecida."
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)
        return f"Aberto {url} no navegador."

    def tool_screenshot(self):
        path = self.vision.capture()
        return f"Screenshot salvo em: {path}"

    def tool_analyze_screen(self):
        return self.vision.analyze()

    def tool_remember(self, key=None, value=None):
        if not key or not value:
            return "Chave e valor são necessários."
        self.memory.remember(key, value)
        return f"Lembrei: {key} = {value}"

    def tool_recall(self, key=None):
        if not key:
            return "Chave não fornecida."
        val = self.memory.recall(key)
        return val if val else f"Não encontrei nada para '{key}'."

    def tool_list_files(self, path=None):
        path = path or "."
        try:
            files = os.listdir(path)
            return "\n".join(files[:50])
        except Exception as e:
            return f"Erro ao listar: {e}"

    def tool_get_clipboard(self):
        try:
            return pyperclip.paste()
        except Exception as e:
            return f"Erro: {e}"

    def tool_get_system_info(self):
        uname = platform.uname()
        return f"Sistema: {uname.system} {uname.release}\nNome: {uname.node}\nArquitetura: {uname.machine}"

    def tool_knowledge_query(self, question=None, n_results=5):
        if not self.knowledge or not question:
            return "Base de conhecimento não disponível"
        context, results = self.knowledge.query(question, n_results=n_results)
        if not context:
            return "Nada encontrado na base de conhecimento."
        sources = list(set(r["metadata"].get("source", "?") for r in results))
        return f"Fontes: {', '.join(sources[:5])}\n\n{context[:2000]}"

    def tool_knowledge_learn_file(self, file_path=None):
        if not self.knowledge or not file_path:
            return "Base de conhecimento não disponível"
        return self.knowledge.learn_file(file_path)

    def tool_knowledge_learn_dir(self, directory=None, recursive=True):
        if not self.knowledge or not directory:
            return "Base de conhecimento não disponível"
        results = self.knowledge.learn_directory(directory, recursive=recursive)
        return "\n".join(results[:20]) if results else "Nada indexado."

    def tool_semantic_remember(self, fact=None, category="general", confidence=1.0):
        if not self.semantic or not fact:
            return "Memória semântica não disponível"
        self.semantic.remember_fact(fact, category, confidence)
        return f"Fato memorizado: {fact}"

    def tool_semantic_recall(self, query=None, top_k=5):
        if not self.semantic or not query:
            return "Memória semântica não disponível"
        facts = self.semantic.recall_fact(query, top_k=top_k)
        if not facts:
            return "Nada encontrado na memória semântica."
        return "\n".join(f"[{f['relevance']:.2f}] {f['fact']} (cat: {f['category']})" for f in facts)

    def tool_episodic_query(self, hour_range=24, episode_type=None):
        if not self.episodic:
            return "Memória episódica não disponível"
        episodes = self.episodic.get_episodes(hours=hour_range, episode_type=episode_type)
        if not episodes:
            return "Nada encontrado no período."
        return "\n".join(f"[{e['time'][:19]}] {e['type']}: {e['summary'][:100]}" for e in episodes[:10])

    def tool_procedural_learn(self, name=None, steps=None, description="", category="general"):
        if not self.procedural or not name or not steps:
            return "Memória procedural não disponível"
        self.procedural.learn_procedure(name, steps, description, category)
        return f"Procedimento '{name}' aprendido com {len(steps)} passos."

    def tool_procedural_recall(self, name=None, category=None):
        if not self.procedural:
            return "Memória procedural não disponível"
        proc = self.procedural.recall_procedure(name=name, category=category)
        if isinstance(proc, list):
            return "\n".join(f"• {p['name']}: {p['description']}" for p in proc)
        elif proc:
            steps = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(proc["steps"]))
            return f"{proc['name']}: {proc['description']}\n{steps}"
        return "Procedimento não encontrado."

    def tool_procedural_replay(self, name=None):
        if not self.procedural or not name:
            return "Memória procedural não disponível"
        proc = self.procedural.recall_procedure(name=name)
        if not proc:
            return f"Procedimento '{name}' não encontrado."
        import agent.computer_use
        cu = agent.computer_use.ComputerUse(llm=self.orchestrator.llm if self.orchestrator else None,
                                            orchestrator=self.orchestrator)
        result = cu.replay_from_memory(name)
        if result.get("success"):
            return f"Replay '{name}' concluído: {result['steps']} passos"
        return f"Falha no replay: {result.get('error', 'erro')}"

    def tool_agent_run(self, task=None):
        if not self.agent or not task:
            return "Agente autônomo não disponível"
        result = self.agent.run(task)
        return result.get("summary", str(result))

    def tool_browser_navigate(self, url=None):
        if not self.browser or not url:
            return "Navegador não disponível"
        return self.browser.sync_navigate(url)

    def tool_browser_search(self, query=None):
        if not self.browser or not query:
            return "Navegador não disponível"
        return self.browser.sync_search_and_extract(query)

    def tool_browser_click(self, selector=None):
        if not self.browser or not selector:
            return "Navegador não disponível"
        return self.browser.sync_click(selector)

    def tool_browser_fill(self, selector=None, value=None):
        if not self.browser or not selector or value is None:
            return "Navegador não disponível"
        return self.browser.sync_fill_form(selector, value)

    def tool_browser_extract(self):
        if not self.browser:
            return "Navegador não disponível"
        return self.browser.sync_extract_text()

    def tool_gui_find_click_image(self, template_path=None, threshold=0.8):
        if not self.gui or not template_path:
            return "Automação GUI não disponível"
        return self.gui.locate_and_click(template_path, threshold)

    def tool_gui_find_click_text(self, text=None):
        if not self.gui or not text:
            return "Automação GUI não disponível"
        return self.gui.locate_text_and_click(text)

    def tool_face_register(self, user_id=None):
        if not self.face_auth or not user_id:
            return "Autenticação facial não disponível"
        return self.face_auth.register_face(user_id)

    def tool_face_auth(self):
        if not self.face_auth:
            return "Autenticação facial não disponível"
        result = self.face_auth.authenticate()
        if result:
            return f"Autenticado: {result['user']} (confiança: {result['confidence']})"
        return "Rosto não reconhecido."

    def tool_reminder_add(self, message=None, delay_minutes=0):
        if not self.scheduler or not message:
            return "Agendador não disponível"
        rid = self.scheduler.add_reminder(message, delay_minutes)
        return f"Lembrete {rid} agendado para {delay_minutes} minutos: {message}"

    def tool_reminder_cron(self, message=None, cron_expr=None):
        if not self.scheduler or not message or not cron_expr:
            return "Agendador não disponível"
        return self.scheduler.add_cron(message, cron_expr)

    def tool_reminder_list(self):
        if not self.scheduler:
            return "Agendador não disponível"
        reminders = self.scheduler.list_reminders()
        if not reminders:
            return "Nenhum lembrete ativo."
        return "\n".join(f"#{r['id']} [{r['remaining_min']}min] {r['message']}" for r in reminders)

    def tool_sandbox_python(self, code=None):
        if not self.sandbox or not code:
            return "Sandbox não disponível"
        return self.sandbox.execute_python(code)

    def tool_sandbox_bash(self, code=None):
        if not self.sandbox or not code:
            return "Sandbox não disponível"
        return self.sandbox.execute_bash(code)

    def tool_sandbox_javascript(self, code=None):
        if not self.sandbox or not code:
            return "Sandbox não disponível"
        return self.sandbox.execute_javascript(code)

    def tool_plugin_list(self):
        if not self.plugins:
            return "Plugin loader não disponível"
        plugins = self.plugins.list_plugins()
        if not plugins:
            return "Nenhum plugin carregado."
        return "\n".join(f"• {p['name']}: tools={p['tools']}, commands={p['commands']}" for p in plugins)

    def tool_learner_stats(self):
        if not self.learner:
            return "Learner não disponível"
        return json.dumps(self.learner.get_stats(), indent=2)

    def tool_self_evolve(self, goal="improve", auto_approve=False):
        if not self.evolution:
            return "Sistema de auto-evolução não disponível"
        result = self.evolution.execute_evolution(goal=goal)
        return json.dumps(result, indent=2)

    def tool_computer_use(self, goal=None):
        if not goal:
            return "Descreva a tarefa (ex: 'abre o Firefox e vai no YouTube')"
        import threading
        result = {}
        def run():
            nonlocal result
            r = self._computer.execute(goal)
            result.update(r)
        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(timeout=120)
        if result:
            return json.dumps(result, indent=2)
        return "Tarefa em andamento. Use computer_stop para parar."

    def tool_hermes_delegate(self, task=None, use_voice=False):
        if not task:
            return "Tarefa não fornecida."
        try:
            import subprocess
            cmd = ["hermes", "-z", task]
            if use_voice:
                cmd.extend(["--personality", "helpful"])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd="/home/alexkali")
            output = result.stdout or result.stderr
            return output[:5000] if output else "Hermes executado sem saída."
        except subprocess.TimeoutExpired:
            return "Hermes excedeu tempo limite (5 min)."
        except Exception as e:
            return f"Erro ao chamar Hermes: {e}"

    def tool_hermes_tool(self, name=None, args=None):
        if not name:
            return "Nome da ferramenta não fornecido."
        try:
            import requests
            payload = {"args": args or {}}
            resp = requests.post(f"http://127.0.0.1:8766/hermes/tools/{name}",
                                 json=payload, timeout=120)
            if resp.status_code == 404:
                return f"Ferramenta '{name}' não encontrada no Hermes."
            data = resp.json()
            result = data.get("result", data)
            if isinstance(result, str):
                return result[:5000]
            import json
            return json.dumps(result, ensure_ascii=False)[:5000]
        except requests.ConnectionError:
            return "Hermes Tool Proxy não está rodando (porta 8766). Execute hermes_tool_proxy.py primeiro."
        except Exception as e:
            return f"Erro ao chamar ferramenta Hermes '{name}': {e}"

    def _register_hermes_tools(self):
        """Auto-register all tools from the Hermes Tool Proxy."""
        try:
            import requests
            resp = requests.get("http://127.0.0.1:8766/hermes/tools", timeout=5)
            if resp.status_code == 200:
                tools = resp.json().get("tools", [])
                for t in tools:
                    name = t["name"]
                    if name in self.tools:
                        continue
                    desc = t.get("description", "")
                    schema = t.get("schema", {})
                    params = schema.get("parameters", {})
                    props = params.get("properties", {})
                    self.register(name, self._make_hermes_handler(name), desc, props)
        except Exception:
            pass

    def _make_hermes_handler(self, tool_name):
        def handler(**kwargs):
            return self._hermes_tool_call(tool_name, kwargs)
        return handler

    def _hermes_tool_call(self, name, args=None):
        """Call a tool on the Hermes Tool Proxy."""
        try:
            import requests
            payload = {"args": args or {}}
            resp = requests.post(f"http://127.0.0.1:8766/hermes/tools/{name}",
                                 json=payload, timeout=120)
            if resp.status_code == 404:
                return None
            data = resp.json()
            result = data.get("result", data)
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except (json.JSONDecodeError, TypeError):
                    pass
            return result
        except Exception:
            return None

    def tool_computer_stop(self):
        self._computer.stop()
        return "Tarefa interrompida"
