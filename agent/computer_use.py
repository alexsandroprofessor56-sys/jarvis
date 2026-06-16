import time
import random
import subprocess
import os
import json
import re
import pyautogui
from vision.screen_capture import ScreenCapture


class ComputerUse:
    """Agente que opera o computador como uma pessoa:
       ver tela → pensar → agir (mouse/teclado) → verificar → repetir"""

    def __init__(self, llm=None, vision=None):
        self.llm = llm
        self.vision = vision or ScreenCapture()
        self._running = False
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1

    def execute(self, goal: str, max_steps: int = 15) -> dict:
        """Executa uma tarefa no computador automaticamente"""
        self._running = True
        steps = []
        success = False

        for step in range(1, max_steps + 1):
            if not self._running:
                break

            screenshot = self._capture()
            elements = self._extract_screen_elements(screenshot)

            action = self._decide_next(goal, elements, steps, step)

            result = self._execute_action(action)
            steps.append({"step": step, "action": action, "result": result})
            time.sleep(self._natural_delay())

            if self._check_done(action, result, goal):
                success = True
                break

        self._running = False
        return {
            "success": success,
            "steps": len(steps),
            "summary": self._summarize(steps),
            "log": steps,
        }

    def stop(self):
        self._running = False

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

    def _decide_next(self, goal: str, elements: list, steps: list, step_num: int) -> dict:
        if self.llm:
            return self._decide_with_llm(goal, elements, steps, step_num)
        return self._decide_heuristic(goal, elements, steps)

    def _decide_with_llm(self, goal: str, elements: list, steps: list, step_num: int) -> dict:
        screen_text = "\n".join(
            f"{i}: '{e['text']}' em ({e['x']},{e['y']}) tam {e['w']}x{e['h']}"
            for i, e in enumerate(elements[:30])
        ) if elements else "(vazio)"

        history = ""
        for s in steps[-3:]:
            act = s.get("action", {})
            history += f"  {act.get('type','?')}: {act.get('value','')} → {s.get('result','')[:100]}\n"

        prompt = (
            f"Você é um agente operando um computador. Complete a tarefa:\n\n"
            f"TAREFA: {goal}\n\n"
            f"PASSO {step_num}\n"
            f"TELA:\n{screen_text[:2000]}\n"
            f"HISTÓRICO:\n{history}\n\n"
            f"Responda APENAS JSON:\n"
            f"{'{\n  \"action\": \"click|doubleclick|rightclick|type|hotkey|scroll|open|wait|done\",\n  \"value\": \"texto ou coordenada\",\n  \"x\": 0,\n  \"y\": 0,\n  \"keys\": [\"ctrl\",\"c\"],\n  \"reason\": \"por que esta acao\"\n}'}"
        )

        try:
            resp = self.llm.chat([
                {"role": "system", "content": "Você é um agente de computador. Responda apenas JSON sem formatação."},
                {"role": "user", "content": prompt},
            ])
            content = ""
            if isinstance(resp, dict):
                content = resp.get("message", {}).get("content", "")
            else:
                content = str(resp)
            cleaned = content.strip().removeprefix("```json").removesuffix("```").strip()
            action = json.loads(cleaned)
            return action
        except Exception:
            pass
        return self._decide_heuristic(goal, elements, steps)

    def _decide_heuristic(self, goal: str, elements: list, steps: list) -> dict:
        goal_lower = goal.lower()
        for e in elements:
            t = e["text"].lower()
            if "firefox" in t and "firefox" in goal_lower:
                return {"action": "click", "x": e["x"] + 5, "y": e["y"] + 5, "reason": "Firefox encontrado"}
            if "terminal" in t and "terminal" in goal_lower:
                return {"action": "click", "x": e["x"] + 5, "y": e["y"] + 5, "reason": "Terminal encontrado"}
            if any(w in t for w in goal_lower.split()) and e["conf"] > 50:
                return {"action": "click", "x": e["x"] + 5, "y": e["y"] + 5, "reason": f"Texto '{e['text']}' encontrado"}

        if "abre" in goal_lower or "abra" in goal_lower or "open" in goal_lower:
            for app in ["firefox", "terminal", "code", "chrome"]:
                if app in goal_lower:
                    return {"action": "open", "value": app, "reason": f"Abrindo {app}"}

        if not steps:
            return {"action": "open", "value": "firefox", "reason": "Tentando abrir firefox"}
        return {"action": "screenshot", "reason": "Analisando tela"}

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
                amount = int(value) if value else 3
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
                return f"Tarefa concluída: {value or 'ok'}"

            return f"Ação '{atype}' não reconhecida"
        except Exception as e:
            return f"Erro: {e}"

    def _human_move(self, x: int, y: int):
        start_x, start_y = pyautogui.position()
        duration = random.uniform(0.15, 0.45)
        pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeInOutQuad)

    def _natural_type_speed(self):
        return random.uniform(0.02, 0.08)

    def _natural_delay(self):
        return random.uniform(0.3, 1.0)

    def _open_app(self, app: str):
        from core.tools import ToolRegistry
        tr = ToolRegistry()
        tr.execute("open_app", app_name=app)

    def _check_done(self, action: dict, result: str, goal: str) -> bool:
        return action.get("action") == "done"

    def _summarize(self, steps: list) -> str:
        if not steps:
            return "Nenhum passo executado"
        actions = [s.get("action", {}).get("action", "?") for s in steps]
        return f"{len(steps)} passos: {', '.join(actions[:5])}{'...' if len(actions)>5 else ''}"
