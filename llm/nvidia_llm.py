import os
import json
import requests
from typing import Optional, List, Dict, Any


class NvidiaLLM:
    def __init__(
        self,
        api_key: str = None,
        model: str = "nvidia/nemotron-3-ultra",
        base_url: str = "https://integrate.api.nvidia.com/v1",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 30
    ):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY não configurada. Defina NVIDIA_API_KEY ou passe api_key no construtor.")

        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _prepare_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                formatted.append({"role": "system", "content": content})
            elif role == "user":
                formatted.append({"role": "user", "content": content})
            elif role == "assistant":
                formatted.append({"role": "assistant", "content": content})
            elif role == "tool":
                formatted.append({"role": "tool", "content": content, "tool_call_id": msg.get("tool_call_id", "")})
        return formatted

    def chat(self, messages: List[Dict[str, str]], tools: List[Dict] = None, stream: bool = False) -> str:
        payload = {
            "model": self.model,
            "messages": self._prepare_messages(messages),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": stream
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json=payload,
            timeout=self.timeout,
            stream=stream
        )
        response.raise_for_status()
        
        if stream:
            return response.iter_lines()
        
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def chat_with_tools(self, messages: List[Dict[str, str]], tools: List[Dict]) -> Dict:
        payload = {
            "model": self.model,
            "messages": self._prepare_messages(messages),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "tools": tools,
            "tool_choice": "auto"
        }
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        message = data["choices"][0]["message"]
        return {"message": message}

    @property
    def available(self) -> bool:
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self.headers,
                timeout=10
            )
            return response.ok
        except Exception:
            return False

    def warmup(self) -> bool:
        try:
            self.chat([{"role": "user", "content": "ping"}], max_tokens=1)
            return True
        except Exception:
            return False