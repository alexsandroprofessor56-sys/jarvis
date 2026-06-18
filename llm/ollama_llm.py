import json
import ollama


class OllamaLLM:
    def __init__(self, model=None, url=None, keep_alive=-1, num_ctx=8192):
        self.model = model or "qwen2.5:3b"
        self.url = url or "http://127.0.0.1:11434"
        self.keep_alive = keep_alive
        self.num_ctx = num_ctx
        self.client = ollama.Client(host=self.url)
        self._chat_cache = {}

    def set_model(self, model):
        self.model = model

    def _options(self):
        return {"num_ctx": self.num_ctx}

    def chat(self, messages, tools=None, stream=False):
        kwargs = dict(
            model=self.model, messages=messages, stream=stream,
            keep_alive=self.keep_alive, options=self._options()
        )
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
        kwargs = dict(
            model=self.model, messages=messages, tools=tools,
            keep_alive=self.keep_alive, options=self._options()
        )
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

    def warmup(self):
        try:
            self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                keep_alive=self.keep_alive,
                options={"num_predict": 1},
            )
            return True
        except Exception:
            return False

    def cache_response(self, key, response):
        self._chat_cache[key] = response

    def get_cached(self, key):
        return self._chat_cache.get(key)

    def clear_cache(self):
        self._chat_cache.clear()
