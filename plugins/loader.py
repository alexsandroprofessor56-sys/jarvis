import os
import sys
import json
import importlib.util
import inspect


PLUGIN_DIR = os.path.expanduser("~/.jarvis/plugins")


class Plugin:
    def __init__(self, name, module, instance):
        self.name = name
        self.module = module
        self.instance = instance
        self.tools = {}
        self.commands = {}

    def get_info(self):
        return {
            "name": self.name,
            "tools": list(self.tools.keys()),
            "commands": list(self.commands.keys()),
            "doc": (self.instance.__doc__ or "").strip()
        }


class PluginLoader:
    def __init__(self):
        os.makedirs(PLUGIN_DIR, exist_ok=True)
        self.plugins = {}

    def discover(self):
        self.plugins = {}
        sys.path.insert(0, PLUGIN_DIR)
        for item in os.listdir(PLUGIN_DIR):
            if item.endswith(".py") and not item.startswith("_"):
                name = item[:-3]
                self._load_plugin(name, os.path.join(PLUGIN_DIR, item))
            elif os.path.isdir(os.path.join(PLUGIN_DIR, item)):
                init_file = os.path.join(PLUGIN_DIR, item, "__init__.py")
                if os.path.exists(init_file):
                    self._load_plugin(item, init_file)
        return self.plugins

    def _load_plugin(self, name, path):
        try:
            spec = importlib.util.spec_from_file_location(f"jarvis_plugin_{name}", path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if inspect.isclass(attr) and hasattr(attr, "jarvis_plugin"):
                        instance = attr()
                        plugin = Plugin(name, module, instance)
                        self._extract_tools(plugin, instance)
                        self._extract_commands(plugin, instance)
                        self.plugins[name] = plugin
                        return
        except Exception as e:
            pass

    def _extract_tools(self, plugin, instance):
        for method_name in dir(instance):
            method = getattr(instance, method_name)
            if hasattr(method, "_jarvis_tool"):
                plugin.tools[method_name] = method

    def _extract_commands(self, plugin, instance):
        for method_name in dir(instance):
            method = getattr(instance, method_name)
            if hasattr(method, "_jarvis_command"):
                plugin.commands[getattr(method, "_jarvis_command")] = method

    def execute_tool(self, plugin_name, tool_name, **kwargs):
        plugin = self.plugins.get(plugin_name)
        if not plugin:
            return f"Plugin '{plugin_name}' não encontrado"
        tool = plugin.tools.get(tool_name)
        if not tool:
            return f"Tool '{tool_name}' não encontrada no plugin '{plugin_name}'"
        try:
            return tool(**kwargs)
        except Exception as e:
            return f"[ERRO PLUGIN] {e}"

    def handle_command(self, text):
        for pname, plugin in self.plugins.items():
            for pattern, handler in plugin.commands.items():
                import re
                if re.match(pattern, text.lower().strip()):
                    try:
                        return handler(text)
                    except Exception as e:
                        return f"[ERRO] {e}"
        return None

    def list_plugins(self):
        return [p.get_info() for p in self.plugins.values()]


def tool(func):
    func._jarvis_tool = True
    return func


def command(pattern):
    def decorator(func):
        func._jarvis_command = pattern
        return func
    return decorator
