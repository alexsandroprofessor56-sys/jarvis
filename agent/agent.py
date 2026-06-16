import time
import json
import traceback

from agent.planner import AgentPlanner
from agent.executor import ParallelExecutor


class AutonomousAgent:
    def __init__(self, llm, tool_registry, knowledge_base=None,
                 episodic_memory=None, semantic_memory=None):
        self.llm = llm
        self.tools = tool_registry
        self.planner = AgentPlanner(llm)
        self.executor = ParallelExecutor(tool_registry)
        self.knowledge = knowledge_base
        self.episodic = episodic_memory
        self.semantic = semantic_memory
        self.max_retries = 3

    def run(self, task, context=None, on_log=None):
        if on_log:
            on_log(f"🤖 Planejando: {task}", "system")

        plan = self.planner.plan(task, context)
        if on_log:
            on_log(f"📋 Plano: {len(plan)} etapas", "system")
            for p in plan:
                on_log(f"  {p['step']}. {p['action']} [{p['tool']}]", "system")

        def step_callback(step):
            if step is None:
                return
            if on_log:
                on_log(f"⚙ Executando etapa {step['step']}: {step['tool']}", "system")
            if self.episodic:
                self.episodic.add_episode(
                    "agent_step",
                    f"Etapa {step['step']}: {step['tool']}({step['args']})",
                    importance=0.3
                )

        for attempt in range(self.max_retries):
            results = self.executor.execute_plan(plan, on_step=step_callback)

            successes = sum(1 for r in results.values() if r["success"])
            failures = sum(1 for r in results.values() if not r["success"])

            if on_log:
                on_log(f"✅ {successes} etapas OK, ❌ {failures} falhas", "system")

            if failures == 0:
                summary = self._summarize_results(task, results)
                if self.episodic:
                    self.episodic.add_episode(
                        "agent_complete",
                        f"Tarefa concluída: {task}",
                        details=json.dumps(results, ensure_ascii=False)[:500],
                        importance=0.7
                    )
                return {"success": True, "results": results, "summary": summary}

            failed_steps = [
                s for s in plan
                if s["step"] in results and not results[s["step"]]["success"]
            ]
            corrections = self._generate_corrections(task, failed_steps, results, attempt)
            plan = self.planner.plan(
                task,
                context=f"Tentativa {attempt + 1} falhou. Correções necessárias: {corrections}"
            )

        if on_log:
            on_log(f"❌ Falha após {self.max_retries} tentativas", "error")
        return {"success": False, "results": results, "summary": "Falha após múltiplas tentativas"}

    def _generate_corrections(self, task, failed_steps, results, attempt):
        errors = []
        for s in failed_steps:
            result = results.get(s["step"], {})
            errors.append(f"Etapa {s['step']}: {result.get('result', 'erro desconhecido')}")
        prompt = (
            f"A tarefa '{task}' falhou na tentativa {attempt + 1}.\n"
            f"Erros:\n" + "\n".join(errors) + "\n"
            "Sugira correções específicas para cada erro."
        )
        try:
            response = self.llm.chat([{"role": "user", "content": prompt}])
            if isinstance(response, dict):
                response = response.get("message", {}).get("content", "")
            return str(response)[:500]
        except Exception:
            return "Tentar abordagem alternativa simplificada"

    def _summarize_results(self, task, results):
        lines = [f"Tarefa: {task}"]
        for step_num, r in sorted(results.items()):
            status = "✅" if r["success"] else "❌"
            result_str = str(r["result"])[:100]
            lines.append(f"{status} Etapa {step_num}: {result_str}")
        return "\n".join(lines)
