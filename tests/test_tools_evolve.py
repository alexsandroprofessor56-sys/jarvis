from core.tools import ToolRegistry

def test_self_evolve_tool_registered():
    tr = ToolRegistry()
    assert "self_evolve" in tr.tools
    assert tr.tools["self_evolve"]["description"]
