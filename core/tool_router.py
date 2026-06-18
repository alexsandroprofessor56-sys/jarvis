"""core/tool_router.py — Seleção de ferramentas por palavra-chave (rápido)"""
import re
import unicodedata

ESSENTIAL_TOOLS = frozenset({
    "search_web", "run_command", "open_app", "remember", "recall",
    "list_files", "get_system_info", "screenshot", "web_fetch",
    "knowledge_query", "get_clipboard", "sandbox_python", "sandbox_bash",
    "type_text", "keyboard_hotkey", "mouse_move", "mouse_click", "mouse_scroll",
    "computer_use", "computer_stop",
    "gui_find_click_image", "gui_find_click_text",
    "analyze_screen", "screen_ocr", "screen_ask", "screen_capture",
    "system_run", "app_launch", "file_list", "file_create", "file_delete",
    "hermes_tool", "hermes_delegate",
})


class ToolRouter:
    def __init__(self, tools_dict):
        self.tools = tools_dict

    @staticmethod
    def _normalize(s: str) -> str:
        return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()

    def _keyword_score(self, query, name, desc):
        q_words = set(re.findall(r"[a-z]+", self._normalize(query)))
        text = self._normalize(f"{name} {desc}")
        if not q_words:
            return 0
        matches = 0
        for qw in q_words:
            if qw in text:
                matches += 2
            elif any(qw in dw or dw.startswith(qw) or qw.startswith(dw) for dw in text.split()):
                matches += 1
        return matches / len(q_words)

    def route(self, query, top_n=12):
        scored = [(self._keyword_score(query, n, self.tools[n].get("description", "")), n)
                  for n in self.tools]
        scored.sort(key=lambda x: -x[0])
        selected = []
        seen = set()
        for _, name in scored:
            if name not in seen and (len(selected) < top_n or name in ESSENTIAL_TOOLS):
                selected.append(name)
                seen.add(name)
        for name in ESSENTIAL_TOOLS:
            if name in self.tools and name not in seen:
                selected.append(name)
                seen.add(name)
        return selected[:top_n * 2]

    def get_relevant_schemas(self, query, top_n=12):
        names = self.route(query, top_n)
        schemas = []
        for name in names:
            info = self.tools.get(name)
            if info:
                schemas.append(self._make_schema(name, info))
        return schemas

    def _make_schema(self, name, info):
        params = {"type": "object", "properties": {}, "required": []}
        if info.get("schema") is not None:
            params["properties"] = info["schema"]
            params["required"] = list(info["schema"].keys())
            return {"type": "function", "function": {
                "name": name, "description": info["description"], "parameters": params
            }}
        return {"type": "function", "function": {
            "name": name, "description": info["description"],
            "parameters": {"type": "object", "properties": {}, "required": []}
        }}
