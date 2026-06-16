import re
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


class AgentPlanner:
    def __init__(self, llm):
        self.llm = llm

    def plan(self, task, context=None):
        prompt = (
            "Você é um planejador de tarefas. Dado o objetivo do usuário, crie um plano detalhado "
            "com etapas executáveis. Cada etapa deve ser independente e usar uma ferramenta disponível.\n\n"
            f"Objetivo: {task}\n"
        )
        if context:
            prompt += f"Contexto: {context}\n"
        prompt += (
            "\nResponda APENAS com um JSON array de etapas, onde cada etapa tem: "
            '{"step": numero, "action": "descricao", "tool": "nome_da_ferramenta", "args": {chaves}, "depends_on": [steps_anteriores]}\n'
            "Use 'think' como tool se for apenas raciocínio.\n"
        )
        try:
            response = self.llm.chat([{"role": "user", "content": prompt}])
            return self._parse_plan(response)
        except Exception as e:
            return [{"step": 1, "action": str(e), "tool": "think", "args": {"thought": f"Erro: {e}"}, "depends_on": []}]

    def _parse_plan(self, response):
        if isinstance(response, dict):
            response = response.get("message", {}).get("content", "")
        json_match = re.search(r'\[.*?\]', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return [{"step": 1, "action": response[:200], "tool": "think", "args": {"thought": response[:200]}, "depends_on": []}]
