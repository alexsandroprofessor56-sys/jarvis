import json
import os
from datetime import datetime, timedelta

MEMORY_DIR = os.path.expanduser("~/.jarvis/memory")


class Learner:
    def __init__(self):
        self._stats_file = os.path.join(MEMORY_DIR, "learning_stats.json")
        self._feedback_file = os.path.join(MEMORY_DIR, "feedback.json")
        self._corrections = []
        self._stats = {"total_commands": 0, "success_rate": 1.0, "tool_usage": {}}
        self._load()

    def record_command(self, command, tool_used=None, success=True):
        self._stats["total_commands"] = self._stats.get("total_commands", 0) + 1
        if tool_used:
            usage = self._stats.setdefault("tool_usage", {})
            usage[tool_used] = usage.get(tool_used, 0) + 1
        total = self._stats["total_commands"]
        successes = self._stats.get("successes", 0) + (1 if success else 0)
        self._stats["successes"] = successes
        self._stats["success_rate"] = successes / total if total > 0 else 1.0
        self._save()

    def record_feedback(self, command, was_correct, correction=None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "was_correct": was_correct,
            "correction": correction
        }
        self._corrections.append(entry)
        if not was_correct and correction:
            self._append_feedback(entry)
        if not was_correct:
            self.record_command(command, success=False)

    def _append_feedback(self, entry):
        try:
            feedback = []
            if os.path.exists(self._feedback_file):
                with open(self._feedback_file) as f:
                    feedback = json.load(f)
            feedback.append(entry)
            with open(self._feedback_file, "w") as f:
                json.dump(feedback[-500:], f, indent=2)
        except Exception:
            pass

    def get_suggestions(self):
        suggestions = []

        usage = self._stats.get("tool_usage", {})
        if usage:
            least_used = min(usage, key=usage.get)
            suggestions.append(f"Considere explorar mais a ferramenta '{least_used}'")

        if self._stats.get("success_rate", 1.0) < 0.7:
            suggestions.append("Taxa de sucesso baixa. Deseja revisar comandos recentes?")

        total = self._stats.get("total_commands", 0)
        if total > 50:
            suggestions.append(f"Você já usou o Jarvis {total} vezes! Deseja otimizar fluxos comuns?")
        elif total < 5:
            suggestions.append("Experimente comandos como 'pesquise sobre...', 'analise a tela', ou 'execute...'")

        recent_failures = [c for c in self._corrections[-10:] if not c.get("was_correct")]
        if recent_failures:
            topics = set(c["command"][:30] for c in recent_failures)
            suggestions.append(f"Comandos que precisam de ajuste: {', '.join(topics)}")

        return suggestions

    def get_stats(self):
        return {
            **self._stats,
            "recent_corrections": len(self._corrections[-20:]),
            "total_corrections": len(self._corrections)
        }

    def _load(self):
        try:
            if os.path.exists(self._stats_file):
                with open(self._stats_file) as f:
                    self._stats = json.load(f)
        except Exception:
            pass
        try:
            if os.path.exists(self._feedback_file):
                with open(self._feedback_file) as f:
                    self._feedback = json.load(f)
        except Exception:
            pass

    def _save(self):
        try:
            with open(self._stats_file, "w") as f:
                json.dump(self._stats, f, indent=2)
        except Exception:
            pass
