import time
import random
import re
import subprocess
import os
import json
import pyautogui
import threading
from vision.screen_capture import ScreenCapture


COMPUTER_ACTION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "computer_action",
        "description": "Executar ação no computador: clicar, digitar, atalho, abrir app, rolar, esperar ou finalizar",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["click", "doubleclick", "rightclick", "type", "hotkey", "scroll", "open", "wait", "done"],
                    "description": "Tipo de ação a executar"
                },
                "value": {
                    "type": "string",
                    "description": "Texto para digitar, app para abrir (ex: firefox)"
                },
                "x": {
                    "type": "integer",
                    "description": "Coordenada X (obrigatório para click/doubleclick/rightclick)"
                },
                "y": {
                    "type": "integer",
                    "description": "Coordenada Y (obrigatório para click/doubleclick/rightclick)"
                },
                "keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Teclas para hotkey, ex: [\"ctrl\", \"c\"]"
                },
            },
            "required": ["action"]
        }
    }
}

COMMON_SITES = {
    "youtube": "youtube.com",
    "github": "github.com",
    "gmail": "mail.google.com",
    "google": "google.com",
    "facebook": "facebook.com",
    "twitter": "x.com",
    "instagram": "instagram.com",
    "linkedin": "linkedin.com",
    "reddit": "reddit.com",
    "amazon": "amazon.com.br",
    "netflix": "netflix.com",
    "spotify": "spotify.com",
    "chatgpt": "chatgpt.com",
    "claude": "claude.ai",
    "whatsapp": "web.whatsapp.com",
    "mercado livre": "mercadolivre.com.br",
}

BROWSER_APPS = ["firefox", "google-chrome", "chromium", "brave-browser", "opera", "microsoft-edge"]

SEARCH_KEYWORDS = ["pesquisa", "busca", "procura", "search", "find", "look for"]


class ComputerUse:
    """Agente que opera o computador com heurísticas inteligentes"""

    def __init__(self, llm=None, vision=None, orchestrator=None):
        self.orchestrator = orchestrator
        self.llm = llm or (orchestrator.llm if orchestrator else None)
        self.vision = vision or ScreenCapture()
        self._running = False
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1

    def execute(self, goal: str, max_steps: int = 12) -> dict:
        self._running = True
        steps = []
        success = False

        self._announce_goal(goal)
        plan = self._parse_goal(goal)

        for step_num in range(1, max_steps + 1):
            if not self._running:
                break

            screenshot = self._capture()
            elements = self._extract_screen_elements(screenshot)
            icons = self._detect_icons()

            action = self._decide_next(plan, elements, icons, steps, step_num)

            self._announce_action(action)
            result = self._execute_action(action)
            steps.append({"step": step_num, "action": action, "result": result})
            time.sleep(self._natural_delay())

            if self._check_done(action, result, plan):
                success = True
                break

        self._running = False

        if success:
            self._save_procedure(goal, steps)

        return {
            "success": success,
            "steps": len(steps),
            "summary": self._summarize(steps),
            "log": steps,
        }

    def stop(self):
        self._running = False
        self._log("Tarefa interrompida pelo usuário")

    # ── Parsing ──────────────────────────────────────────────────

    def _parse_goal(self, goal: str) -> dict:
        g = goal.lower().strip()
        parsed = {"raw": goal, "site": None, "search": None, "app": None, "url": None}

        # Detect site
        for name, domain in COMMON_SITES.items():
            if name in g:
                parsed["site"] = name
                parsed["url"] = domain
                break

        # Detect "pesquisar X" or "buscar X"
        for kw in SEARCH_KEYWORDS:
            m = re.search(rf"{kw}\s+(.+?)(?:\s*(?:no|na|em|dentro)\s+|$)", g)
            if m:
                parsed["search"] = m.group(1).strip()
                break

        # Detect app to open
        for app in BROWSER_APPS + ["terminal", "code", "spotify", "discord", "whatsapp", "slack"]:
            if app in g and re.search(rf"(abre|abra|open|inicia|inicie|launch)", g):
                parsed["app"] = app
                break
        if not parsed["app"] and any(a in g for a in ["youtube", "github", "gmail", "facebook"]):
            parsed["app"] = "firefox"

        # Detect "clique em TEXTO"
        m = re.search(r"clique\s+(?:em|no|na)\s+(.+)", g)
        if m:
            parsed["click_text"] = m.group(1)

        # Detect "digite TEXTO"
        m = re.search(r"digite\s+(.+)", g)
        if m:
            parsed["type_text"] = m.group(1)

        return parsed

    # ── Decision ─────────────────────────────────────────────────

    def _decide_next(self, plan: dict, elements: list, icons: dict, steps: list, step_num: int) -> dict:
        if self.llm:
            llm_action = self._try_llm(plan, elements, icons, steps, step_num)
            if llm_action:
                return llm_action
        return self._decide_heuristic(plan, elements, steps)

    def _try_llm(self, plan, elements, icons, steps, step_num):
        screen_text = "\n".join(
            f"  [{i}] '{e['text']}' em ({e['x']},{e['y']}) tam {e['w']}x{e['h']}"
            for i, e in enumerate(elements[:25])
        ) if elements else "  (vazio)"

        if icons:
            screen_text += "\n" + "\n".join(
                f"  ICONE '{name}' em ({x},{y})" for name, (x, y) in icons.items()
            )

        last3 = "\n".join(
            f"  {s.get('action',{}).get('action','?')} -> {str(s.get('result',''))[:60]}"
            for s in steps[-3:]
        )

        messages = [
            {"role": "system", "content": "Você controla o computador. Responda APENAS com computer_action."},
            {"role": "user", "content": f"TAREFA: {plan['raw']}\nTELA:\n{screen_text[:2000]}\nULTIMOS:\n{last3}\nProxima acao?"},
        ]

        try:
            resp = self.llm.chat_with_tools(messages, [COMPUTER_ACTION_SCHEMA])
            msg = resp.get("message", {})
            if msg.get("tool_calls"):
                tc = msg["tool_calls"][0]
                args = tc["function"].get("arguments", {})
                if isinstance(args, str):
                    args = json.loads(args)
                return args
            content = msg.get("content", "")
            if content:
                cleaned = content.strip().removeprefix("```json").removesuffix("```").strip()
                return json.loads(cleaned)
        except Exception:
            pass
        return None

    def _decide_heuristic(self, plan: dict, elements: list, steps: list) -> dict:
        site = plan.get("site")
        url = plan.get("url")
        app = plan.get("app")
        search = plan.get("search")
        click_text = plan.get("click_text")
        type_text = plan.get("type_text")
        n = len(steps)

        # ── Actions log (what we already did) ──
        did_open = any(s.get("action", {}).get("action") == "open" for s in steps)
        all_typed = [s.get("action", {}).get("value", "") for s in steps if s.get("action", {}).get("action") == "type"]
        did_url = any("." in v and not v.endswith(".") for v in all_typed)
        any_type_done = bool(all_typed)
        did_search_type = any(v == search for v in all_typed)
        did_focus = any(
            s.get("action", {}).get("action") == "hotkey"
            and isinstance(s.get("action", {}).get("keys"), list)
            and "l" in s.get("action", {}).get("keys", [])
            for s in steps
        )
        did_enter = any(s.get("action", {}).get("action") == "hotkey" and s.get("action", {}).get("value") == "navegar" for s in steps)
        did_search_enter = any(s.get("action", {}).get("action") == "hotkey" and s.get("action", {}).get("value") == "buscar" for s in steps)

        # ── Click specific text ──
        if click_text and n == 0:
            for e in elements:
                if click_text.lower() in e["text"].lower():
                    return {"action": "click", "x": e["x"] + 5, "y": e["y"] + 5}

        # ── Type specific text ──
        if type_text and n == 0:
            return {"action": "type", "value": type_text}

        # ── State machine ──
        if site or app:
            if search and did_search_enter:
                return {"action": "done", "value": f"Pesquisa '{search}' concluída em {site or 'site'}"}

            if search and did_search_type:
                return {"action": "hotkey", "keys": ["enter"], "value": "buscar"}

            if did_enter and search:
                return {"action": "type", "value": search}

            if did_focus and did_url:
                return {"action": "hotkey", "keys": ["enter"], "value": "navegar"}

            if did_focus and (site or url):
                return {"action": "type", "value": url}

            if did_open and (site or url):
                return {"action": "hotkey", "keys": ["ctrl", "l"], "value": "focar barra"}

            if did_open and any_type_done and not site:
                return {"action": "hotkey", "keys": ["ctrl", "l"], "value": "focar barra"}

            # Open browser
            if not did_open:
                return {"action": "open", "value": app or "firefox"}

        # ── Fallback ──
        if n == 0:
            return {"action": "open", "value": "firefox"}
        if n > 3:
            return {"action": "done", "value": "tarefa finalizada"}
        return {"action": "wait", "value": "2"}

    # ── Announcements ────────────────────────────────────────────

    def _announce_goal(self, goal: str):
        if not self.orchestrator:
            return
        text = f"Vou realizar a tarefa: {goal[:100]}"
        self.orchestrator.log(f"ComputerUse: {goal}", "system")
        self.orchestrator._speak_clean(text)

    def _announce_action(self, action: dict):
        if not self.orchestrator:
            return
        atype = action.get("action", "")
        value = action.get("value", "")
        friendly = {
            "click": "clicar", "doubleclick": "clicar duas vezes", "rightclick": "clicar direito",
            "type": "digitar", "hotkey": "pressionar teclas", "scroll": "rolar",
            "open": "abrir", "wait": "aguardar", "screenshot": "capturar tela", "done": "finalizar",
        }
        name = friendly.get(atype, atype)
        text = f"Vou {name}: {value[:40]}" if value else f"Vou {name}"
        self.orchestrator.log(f"ComputerUse: {text}", "system")
        self.orchestrator._speak_clean(text)

    # ── Execution ────────────────────────────────────────────────

    def _capture(self) -> str:
        return self.vision.capture()

    def _extract_screen_elements(self, screenshot_path: str) -> list:
        elements = []
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(screenshot_path)
            data = pytesseract.image_to_data(img, lang="por+eng", output_type=pytesseract.Output.DICT)
            for i in range(len(data["text"])):
                text = data["text"][i].strip()
                if text and int(data["conf"][i]) > 30:
                    elements.append({
                        "text": text,
                        "x": data["left"][i],
                        "y": data["top"][i],
                        "w": data["width"][i],
                        "h": data["height"][i],
                        "conf": data["conf"][i],
                    })
        except ImportError:
            pass
        return elements[:50]

    def _detect_icons(self) -> dict:
        icons = {}
        icons_dir = os.path.expanduser("~/.jarvis/icons")
        if os.path.isdir(icons_dir):
            for fname in os.listdir(icons_dir):
                if not fname.lower().endswith(('.png', '.jpg', '.jpeg')):
                    continue
                path = os.path.join(icons_dir, fname)
                try:
                    pos = pyautogui.locateCenterOnScreen(path, confidence=0.7)
                    if pos:
                        icons[os.path.splitext(fname)[0].lower()] = (int(pos.x), int(pos.y))
                except Exception:
                    pass
        return icons

    def _execute_action(self, action: dict) -> str:
        atype = action.get("action", "")
        value = action.get("value", "")
        x = action.get("x")
        y = action.get("y")
        keys = action.get("keys")

        try:
            if atype == "click" and x is not None and y is not None:
                self._human_move(x, y)
                pyautogui.click()
                return f"Clique em ({x},{y})"
            elif atype == "doubleclick" and x is not None and y is not None:
                self._human_move(x, y)
                pyautogui.doubleClick()
                return f"Duplo clique em ({x},{y})"
            elif atype == "rightclick":
                cx = x or pyautogui.position().x
                cy = y or pyautogui.position().y
                self._human_move(cx, cy)
                pyautogui.rightClick()
                return f"Clique direito em ({cx},{cy})"
            elif atype == "type" and value:
                pyautogui.write(value, interval=self._natural_type_speed())
                return f"Digitado: {value[:50]}"
            elif atype == "hotkey" and keys:
                pyautogui.hotkey(*keys)
                return f"Atalho: {'+'.join(keys)}"
            elif atype == "scroll":
                amount = -3 if value and "cima" in value.lower() else 3
                pyautogui.scroll(amount)
                return f"Scroll {amount}"
            elif atype == "open" and value:
                self._open_app(value)
                return f"Abrindo: {value}"
            elif atype == "wait":
                t = float(value) if value else 1.5
                time.sleep(t)
                return f"Aguardou {t}s"
            elif atype == "screenshot":
                path = self._capture()
                return f"Screenshot: {path}"
            elif atype == "done":
                return f"Concluído: {value or 'ok'}"
            return f"Ação '{atype}' não reconhecida"
        except Exception as e:
            return f"Erro: {e}"

    def _human_move(self, x: int, y: int):
        duration = random.uniform(0.15, 0.45)
        pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeInOutQuad)

    def _natural_type_speed(self):
        return random.uniform(0.02, 0.08)

    def _natural_delay(self):
        return random.uniform(0.3, 1.0)

    def _open_app(self, app: str):
        try:
            subprocess.Popen([app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        except Exception:
            self._log(f"Falha ao abrir {app}")

    def _check_done(self, action: dict, result: str, plan: dict) -> bool:
        return action.get("action") == "done"

    def _summarize(self, steps: list) -> str:
        if not steps:
            return "Nenhum passo executado"
        actions = [s.get("action", {}).get("action", "?") for s in steps]
        return f"{len(steps)} passos: {', '.join(actions[:6])}{'...' if len(actions) > 6 else ''}"

    def _save_procedure(self, goal: str, steps: list):
        if not self.orchestrator or not self.orchestrator.procedural:
            return
        name = self._extract_procedure_name(goal)
        action_steps = [
            f"{s.get('action', {}).get('action', '?')}: {json.dumps(s.get('action', {}))}"
            for s in steps
        ]
        self.orchestrator.procedural.learn_procedure(
            name=name,
            steps=action_steps,
            description=f"Como {goal[:100]}",
            category="computer_use"
        )
        self.orchestrator.log(f"📖 Procedimento '{name}' aprendido ({len(steps)} passos)", "system")

    def _extract_procedure_name(self, goal: str) -> str:
        words = re.sub(r'[^a-z0-9\s]', '', goal.lower().strip())[:50].split()
        return '_'.join(words[:6]) if words else f'proc_{int(time.time())}'

    def replay_from_memory(self, name: str) -> dict:
        if not self.orchestrator or not self.orchestrator.procedural:
            return {"success": False, "error": "Memória procedural indisponível"}
        proc = self.orchestrator.procedural.recall_procedure(name=name)
        if not proc:
            return {"success": False, "error": f"Procedimento '{name}' não encontrado"}
        self._running = True
        replay_steps = []
        for step_str in proc["steps"]:
            if not self._running:
                break
            try:
                action = json.loads(step_str.split(": ", 1)[1])
            except Exception:
                continue
            self._announce_action(action)
            result = self._execute_action(action)
            replay_steps.append({"action": action, "result": result})
            time.sleep(self._natural_delay())
        self._running = False
        self.orchestrator.procedural.record_success(name)
        self.orchestrator.log(f"📖 Replay '{name}' concluído ({len(replay_steps)} passos)", "system")
        return {"success": True, "steps": len(replay_steps)}

    def _log(self, msg: str):
        if self.orchestrator:
            self.orchestrator.log(msg, "system")
