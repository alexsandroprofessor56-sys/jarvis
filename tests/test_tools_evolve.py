from core.tools import ToolRegistry

class _MockOrch:
    def __init__(self):
        self._llm = None
    @property
    def llm(self): return None
    @llm.setter
    def llm(self, v): pass
    def __getattr__(self, name): return None
    def log(self, msg, tag): pass

def test_self_evolve_tool_registered():
    tr = ToolRegistry(_MockOrch())
    assert "self_evolve" in tr.tools
    assert tr.tools["self_evolve"]["description"]
