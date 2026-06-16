import time
import threading
import requests
import config.settings as settings


class TelegramListener:
    def __init__(self, on_message=None):
        self._on_message = on_message
        self._running = False
        self._thread = None
        self._last_update_id = 0
        self._token = ""
        self._chat_id = ""

    def _load_config(self):
        cfg = settings.get("telegram", {})
        self._token = cfg.get("token", "")
        self._chat_id = cfg.get("chat_id", "")
        self._poll_interval = cfg.get("poll_interval", 2)

    @property
    def configured(self):
        self._load_config()
        return bool(self._token and self._chat_id)

    def start(self, on_message=None):
        if on_message:
            self._on_message = on_message
        if not self.configured:
            return "Telegram não configurado"
        if self._running:
            return "Listener já rodando"
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        return "Listener Telegram iniciado"

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        return "Listener Telegram parado"

    def _poll_loop(self):
        while self._running:
            try:
                url = f"https://api.telegram.org/bot{self._token}/getUpdates"
                params = {
                    "offset": self._last_update_id + 1,
                    "timeout": 10,
                    "allowed_updates": ["message"],
                }
                r = requests.get(url, params=params, timeout=15)
                if r.ok:
                    data = r.json()
                    if data.get("ok"):
                        for update in data.get("result", []):
                            self._last_update_id = update["update_id"]
                            self._handle_update(update)
            except requests.Timeout:
                pass
            except Exception as e:
                time.sleep(5)
            time.sleep(self._poll_interval)

    def _handle_update(self, update):
        msg = update.get("message", {})
        chat_id = str(msg.get("chat", {}).get("id", ""))
        text = msg.get("text", "").strip()
        if not text or chat_id != self._chat_id:
            return
        if text.startswith("/"):
            self._handle_command(text, chat_id)
        elif self._on_message:
            self._on_message(text)

    def _handle_command(self, text, chat_id):
        cmd = text.lower().split()[0]
        args = text[len(cmd):].strip()
        if cmd == "/start":
            self._reply("Jarvis online. Envie mensagens para falar comigo.")
        elif cmd == "/status":
            info = f"Jarvis ativo\nComandos processados nesta sessão\nTelegram conectado"
            self._reply(info)
        elif cmd == "/help":
            self._reply(
                "Comandos:\n"
                "/status - Status do sistema\n"
                "/help - Esta mensagem\n"
                "/shell <comando> - Executar comando shell\n"
                "Ou apenas envie qualquer mensagem"
            )
        elif cmd == "/shell" and args:
            try:
                import subprocess
                r = subprocess.run(args, shell=True, capture_output=True, text=True, timeout=30)
                out = (r.stdout or r.stderr)[:2000]
                self._reply(out[:2000] if out else "Sem saída")
            except Exception as e:
                self._reply(f"Erro: {e}")
        else:
            self._reply(f"Comando desconhecido: {cmd}. Use /help")

    def _reply(self, text):
        try:
            url = f"https://api.telegram.org/bot{self._token}/sendMessage"
            requests.post(url, json={"chat_id": self._chat_id, "text": text}, timeout=10)
        except Exception:
            pass


TOOLS_TELEGRAM = [
    ("telegram_listener_start", TelegramListener.start,
     "Iniciar listener Telegram para receber comandos", {}),
    ("telegram_listener_stop", TelegramListener.stop,
     "Parar listener Telegram", {}),
]
