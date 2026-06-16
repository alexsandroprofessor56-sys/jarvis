import json
import ollama


class OllamaLLM:
    def __init__(self, model=None, url=None):
        self.model = model or "qwen2.5:3b"
        self.url = url or "http://127.0.0.1:11434"
        self.client = ollama.Client(host=self.url)

    def set_model(self, model):
        self.model = model

    def chat(self, messages, tools=None, stream=False):
        kwargs = dict(model=self.model, messages=messages, stream=stream)
        if tools:
            kwargs["tools"] = tools
        try:
            response = self.client.chat(**kwargs)
            if stream:
                return response
            return response["message"]["content"]
        except Exception as e:
            return f"[ERRO LLM] {e}"

    def chat_with_tools(self, messages, tools):
        kwargs = dict(model=self.model, messages=messages, tools=tools)
        try:
            return self.client.chat(**kwargs)
        except Exception as e:
            msg = {"role": "assistant", "content": f"[ERRO LLM] {e}"}
            return {"message": msg}

    @property
    def available(self):
        try:
            self.client.list()
            return True
        except Exception:
            return False
