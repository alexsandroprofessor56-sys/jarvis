import os
import subprocess
import platform
import hashlib
import secrets
import shutil
import json
import time
import socket
import sqlite3
import requests
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from agent.credential_vault import credential_save as _vault_save, credential_get as _vault_get, credential_list as _vault_list, credential_delete as _vault_delete
from agent.app_builder import AppBuilder


class ExtraTools:
    def __init__(self):
        self._http_server = None
        self._http_thread = None
        self.telegram_listener = None
        self._app_builder = AppBuilder()

    def system_monitor(self):
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            net = psutil.net_io_counters()
            return (
                f"CPU: {cpu}%\nRAM: {mem.used//1024//1024}MB/{mem.total//1024//1024}MB "
                f"({mem.percent}%)\nDisco: {disk.used//1024//1024//1024}GB/{disk.total//1024//1024//1024}GB "
                f"({disk.percent}%)\nRede RX: {net.bytes_recv//1024//1024}MB TX: {net.bytes_sent//1024//1024}MB"
            )
        except ImportError:
            return self._sh("top -bn1 | head -5")

    def process_list(self):
        result = self._sh("ps aux --sort=-%mem | head -30")
        return result or "ps aux falhou"

    def process_kill(self, pid=None, name=None):
        if pid:
            out = self._sh(f"kill {pid}")
        elif name:
            out = self._sh(f"pkill -f {name}")
        else:
            return "Forneça pid ou name"
        return f"Processo finalizado" if out is None else out

    def service_control(self, action="status", service=None):
        if not service:
            return "Nome do serviço necessário"
        out = self._sh(f"systemctl {action} {service} 2>&1")
        return out[:1000] if out else f"Serviço {service}: {action}"

    def file_search(self, pattern=None, path=None):
        path = path or os.path.expanduser("~")
        if not pattern:
            return "Padrão de busca necessário"
        out = self._sh(f"grep -rl '{pattern}' {path} --include='*.py' --include='*.txt' --include='*.json' --include='*.md' 2>/dev/null | head -30")
        return out or "Nada encontrado"

    def file_read(self, path=None):
        if not path:
            return "Caminho necessário"
        path = os.path.expanduser(path)
        try:
            with open(path) as f:
                return f.read()[:5000]
        except Exception as e:
            return f"Erro: {e}"

    def file_write(self, path=None, content=None):
        if not path or content is None:
            return "Caminho e conteúdo necessários"
        path = os.path.expanduser(path)
        try:
            with open(path, "w") as f:
                f.write(content)
            return f"Arquivo salvo: {path}"
        except Exception as e:
            return f"Erro: {e}"

    def file_delete(self, path=None):
        if not path:
            return "Caminho necessário"
        path = os.path.expanduser(path)
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            return f"Removido: {path}"
        except Exception as e:
            return f"Erro: {e}"

    def file_copy_move(self, source=None, dest=None, action="copy"):
        if not source or not dest:
            return "source e dest necessários"
        source, dest = os.path.expanduser(source), os.path.expanduser(dest)
        try:
            if action == "copy":
                shutil.copytree(source, dest) if os.path.isdir(source) else shutil.copy2(source, dest)
            else:
                shutil.move(source, dest)
            return f"{action.capitalize()} {source} → {dest}"
        except Exception as e:
            return f"Erro: {e}"

    def bluetooth_control(self, action="status", device=None):
        if action == "status":
            return self._sh("bluetoothctl show 2>&1 | head -10") or "Bluetooth não disponível"
        elif action == "scan":
            return self._sh("bluetoothctl scan on 2>&1 | head -20 && sleep 3 && bluetoothctl devices") or "Scan falhou"
        elif action == "connect" and device:
            return self._sh(f"bluetoothctl connect {device} 2>&1") or f"Conectado a {device}"
        return "Comando bluetooth inválido"

    def power_control(self, action="status"):
        if action == "shutdown":
            return self._sh("shutdown -h now") or "Desligando..."
        elif action == "reboot":
            return self._sh("reboot") or "Reiniciando..."
        elif action == "suspend":
            return self._sh("systemctl suspend") or "Suspenso"
        return "Comando de energia inválido"

    def package_search_install(self, action="search", package=None):
        if not package:
            return "Nome do pacote necessário"
        if action == "search":
            out = self._sh(f"apt-cache search {package} 2>&1 | head -15")
            return out or f"Nada encontrado para {package}"
        elif action == "install":
            return "Para instalar: sudo apt install -y {package}"
        return "use search ou install"

    def clipboard_set(self, text=None):
        if text is None:
            return "Texto necessário"
        try:
            import pyperclip
            pyperclip.copy(text)
            return "Texto copiado para área de transferência"
        except Exception as e:
            return f"Erro: {e}"

    def download_file(self, url=None, dest=None):
        if not url:
            return "URL necessária"
        dest = os.path.expanduser(dest or os.path.basename(url))
        try:
            r = requests.get(url, stream=True, timeout=60)
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            size = os.path.getsize(dest)
            return f"Download salvo em {dest} ({size} bytes)"
        except Exception as e:
            return f"Erro: {e}"

    def network_info(self):
        out = self._sh("ip -brief addr 2>/dev/null || ifconfig 2>/dev/null | head -40")
        return out or "Info de rede indisponível"

    def port_scan(self, target="127.0.0.1", port_range="1-1024"):
        out = self._sh(f"nmap -p {port_range} --open -T4 {target} 2>&1 | tail -20")
        return out or "nmap não disponível ou scan falhou"

    def wifi_scan(self):
        out = self._sh("nmcli dev wifi list 2>/dev/null | head -30")
        if not out:
            out = self._sh("iwlist wlan0 scanning 2>/dev/null | grep -E 'ESSID|Signal' | head -30")
        return out or "WiFi scan indisponível"

    def hash_file(self, path=None, algorithm="sha256"):
        if not path:
            return "Caminho necessário"
        path = os.path.expanduser(path)
        try:
            h = hashlib.new(algorithm)
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return f"{algorithm.upper()}: {h.hexdigest()}"
        except Exception as e:
            return f"Erro: {e}"

    def password_generate(self, length=20, use_symbols=True):
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        if use_symbols:
            chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"
        pw = "".join(secrets.choice(chars) for _ in range(length))
        return f"Senha gerada ({length} caracteres): {pw}"

    def vpn_control(self, action="status", config=None):
        if action == "status":
            out = self._sh("wg show 2>/dev/null || ip link show | grep -i tun")
            return out or "Nenhuma VPN ativa"
        elif action == "up" and config:
            return self._sh(f"wg-quick up {config} 2>&1") or f"VPN {config} ativada"
        elif action == "down":
            return self._sh(f"wg-quick down {config} 2>&1") if config else self._sh("killall wireguard 2>&1")
        return "Comando VPN inválido"

    def camera_capture(self, output=None):
        output = output or os.path.expanduser(f"~/Pictures/jarvis_cam_{int(time.time())}.jpg")
        os.makedirs(os.path.dirname(output), exist_ok=True)
        out = self._sh(f"fswebcam -r 640x480 --jpeg 90 {output} 2>&1")
        if os.path.exists(output):
            return f"Foto salva: {output}"
        out2 = self._sh(f"ffmpeg -f v4l2 -i /dev/video0 -vframes 1 {output} 2>&1")
        return f"Foto salva: {output}" if os.path.exists(output) else self._sh("ls /dev/video* 2>&1") or "Câmera não encontrada"

    def record_audio(self, duration=5, output=None):
        output = output or os.path.expanduser(f"~/Pictures/jarvis_audio_{int(time.time())}.wav")
        os.makedirs(os.path.dirname(output), exist_ok=True)
        out = self._sh(f"arecord -d {duration} -f cd {output} 2>&1")
        if os.path.exists(output):
            return f"Áudio salvo: {output}"
        return "Gravação falhou (arecord não disponível?)"

    def play_audio(self, path=None):
        if not path:
            return "Caminho necessário"
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return "Arquivo não encontrado"
        self._sh(f"aplay {path} 2>&1 &")
        return f"Tocando: {path}"

    def image_manipulate(self, action=None, path=None, **kwargs):
        if not action or not path:
            return "action e path necessários"
        path = os.path.expanduser(path)
        try:
            from PIL import Image
            img = Image.open(path)
            if action == "resize":
                w, h = int(kwargs.get("width", 800)), int(kwargs.get("height", 600))
                img = img.resize((w, h))
            elif action == "convert":
                fmt = kwargs.get("format", "png")
                new_path = os.path.splitext(path)[0] + f".{fmt}"
                img.save(new_path, format=fmt.upper())
                return f"Convertido: {new_path}"
            elif action == "rotate":
                deg = int(kwargs.get("degrees", 90))
                img = img.rotate(deg)
            elif action == "info":
                return f"Dimensões: {img.size}, Formato: {img.format}, Modo: {img.mode}"
            else:
                return f"Ação '{action}' não suportada"
            img.save(path)
            return f"Imagem {action} aplicado em {path}"
        except ImportError:
            return "Pillow não instalado (pip install pillow)"
        except Exception as e:
            return f"Erro: {e}"

    def pdf_generate(self, content=None, output=None):
        if not content or not output:
            return "content e output necessários"
        output = os.path.expanduser(output)
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_font("DejaVu", "", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", uni=True)
            pdf.set_font("DejaVu", "", 12)
            for line in content.split("\n"):
                pdf.multi_cell(0, 10, line)
            pdf.output(output)
            return f"PDF salvo: {output}"
        except ImportError:
            return "fpdf2 não instalado (pip install fpdf2)"
        except Exception as e:
            return f"Erro: {e}"

    def ocr_file(self, path=None):
        if not path:
            return "Caminho necessário"
        path = os.path.expanduser(path)
        try:
            import pytesseract
            from PIL import Image
            text = pytesseract.image_to_string(Image.open(path), lang="por+eng")
            return text[:3000] if text.strip() else "Nenhum texto encontrado"
        except ImportError:
            return "pytesseract ou PIL não instalado"
        except Exception as e:
            return f"Erro: {e}"

    def docker_ps(self):
        out = self._sh("docker ps -a --format 'table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Image}}' 2>&1")
        return out or "Docker não disponível"

    def docker_exec(self, container=None, command=None):
        if not container or not command:
            return "container e command necessários"
        out = self._sh(f"docker exec {container} {command} 2>&1")
        return out or "Comando executado sem saída"

    def git_status(self, path=None):
        path = path or os.path.expanduser("~/jarvis")
        out = self._sh(f"git -C {path} status --short 2>&1")
        branch = self._sh(f"git -C {path} rev-parse --abbrev-ref HEAD 2>&1")
        return f"Branch: {branch}\n{out[:1500]}" if out.strip() else f"Branch: {branch}\nNada modificado"

    def git_commit(self, path=None, message=None):
        if not message:
            return "Mensagem de commit necessária"
        path = path or os.path.expanduser("~/jarvis")
        add = self._sh(f"git -C {path} add -A 2>&1")
        out = self._sh(f"git -C {path} commit -m '{message}' 2>&1")
        return out or "Commit realizado"

    def api_request(self, method="GET", url=None, headers=None, body=None):
        if not url:
            return "URL necessária"
        try:
            hdrs = json.loads(headers) if isinstance(headers, str) else (headers or {})
            if method.upper() == "GET":
                r = requests.get(url, headers=hdrs, timeout=30)
            elif method.upper() == "POST":
                r = requests.post(url, headers=hdrs, data=body, timeout=30)
            elif method.upper() == "PUT":
                r = requests.put(url, headers=hdrs, data=body, timeout=30)
            elif method.upper() == "DELETE":
                r = requests.delete(url, headers=hdrs, timeout=30)
            else:
                return f"Método {method} não suportado"
            return f"{r.status_code}\n{r.text[:2000]}"
        except Exception as e:
            return f"Erro: {e}"

    def sql_query(self, db_path=None, query=None):
        if not db_path or not query:
            return "db_path e query necessários"
        db_path = os.path.expanduser(db_path)
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(query)
            if query.strip().upper().startswith("SELECT"):
                rows = cur.fetchmany(20)
                cols = [d[0] for d in cur.description]
                result = "\t".join(cols) + "\n"
                for r in rows:
                    result += "\t".join(str(c) for c in r) + "\n"
                return result
            else:
                conn.commit()
                return f"Query executada. Linhas afetadas: {cur.rowcount}"
        except Exception as e:
            return f"Erro SQL: {e}"
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def model_switch(self, model=None):
        if not model:
            return "Nome do modelo necessário (ex: llama3.2:3b)"
        try:
            import config.settings as settings
            cfg = settings.load()
            cfg["llm"]["model"] = model
            settings.save(cfg)
            return f"Modelo alterado para {model}. Reinicie o Jarvis para aplicar."
        except Exception as e:
            return f"Erro: {e}"

    def send_email(self, to=None, subject=None, body=None, smtp_server=None, smtp_port=587, user=None, password=None):
        if not to or not subject or not body:
            return "to, subject e body necessários"
        try:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["To"] = to
            if user and password:
                msg["From"] = user
                with smtplib.SMTP(smtp_server, smtp_port) as s:
                    s.starttls()
                    s.login(user, password)
                    s.send_message(msg)
            else:
                import config.settings as settings
                cfg = settings.load().get("email", {})
                if not cfg.get("server"):
                    return "Configuração de email não encontrada. Configure ~/.jarvis/config.json email.server"
                msg["From"] = cfg["user"]
                with smtplib.SMTP(cfg["server"], cfg.get("port", 587)) as s:
                    s.starttls()
                    s.login(cfg["user"], cfg.get("password", ""))
                    s.send_message(msg)
            return f"Email enviado para {to}"
        except Exception as e:
            return f"Erro email: {e}"

    def send_notification(self, title="Jarvis", message=None):
        if not message:
            return "Mensagem necessária"
        self._sh(f'notify-send "{title}" "{message}" 2>&1 || echo "notify-send não disponível"')
        return f"Notificação: {title} - {message}"

    def http_server(self, port=8080, directory=None):
        if self._http_server:
            return "Servidor HTTP já rodando"
        directory = os.path.expanduser(directory or ".")
        os.chdir(directory)

        class Handler(SimpleHTTPRequestHandler):
            def log_message(self, *a):
                pass

        self._http_server = HTTPServer(("0.0.0.0", port), Handler)
        self._http_thread = threading.Thread(target=self._http_server.serve_forever, daemon=True)
        self._http_thread.start()
        return f"Servidor HTTP rodando em http://0.0.0.0:{port} (diretório: {directory})"

    def http_server_stop(self):
        if self._http_server:
            self._http_server.shutdown()
            self._http_server = None
            return "Servidor HTTP parado"
        return "Nenhum servidor rodando"

    def telegram_listener_start(self):
        if not self.telegram_listener:
            return "Telegram listener não configurado"
        return self.telegram_listener.start()

    def telegram_listener_stop(self):
        if not self.telegram_listener:
            return "Nenhum listener ativo"
        return self.telegram_listener.stop()

    def telegram_send(self, token=None, chat_id=None, text=None):
        if not text:
            return "text necessário"
        if not token or not chat_id:
            try:
                import config.settings as settings
                cfg = settings.get("telegram", {})
                token = token or cfg.get("token", "")
                chat_id = chat_id or cfg.get("chat_id", "")
            except Exception:
                pass
        if not token or not chat_id:
            return "Configure telegram.token e telegram.chat_id no config.json"
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
                timeout=15,
            )
            return f"Telegram: {r.json().get('ok', False)}" if r.ok else f"Erro: {r.text[:200]}"
        except Exception as e:
            return f"Erro: {e}"

    def _sh(self, cmd):
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            return r.stdout[:2000] or r.stderr[:500]
        except subprocess.TimeoutExpired:
            return "Comando excedeu o tempo limite"
        except Exception as e:
            return str(e)

    # === CREDENTIAL VAULT ===
    def credential_save(self, service=None, username=None, password=None, notes=""):
        if not service or not username or not password:
            return "Parâmetros necessários: service, username, password"
        return _vault_save(service, username, password, notes)

    def credential_get(self, service=None):
        if not service:
            return "Parâmetro 'service' necessário"
        return json.dumps(_vault_get(service), indent=2)

    def credential_list(self):
        return "\n".join(_vault_list()) if _vault_list() else "Nenhuma credencial salva."

    def credential_delete(self, service=None):
        if not service:
            return "Parâmetro 'service' necessário"
        return _vault_delete(service)

    # === APP BUILDER ===
    def app_builder(self, descricao=None):
        if not descricao:
            return "Descreva o app/site que quer criar. Ex: 'cria um app de tarefas'"
        plan = self._app_builder.analyze(descricao)
        name = descricao.lower().replace(" ", "-")[:30]
        path = self._app_builder.scaffold(name, plan)
        self._app_builder.generate(name, plan)
        self._app_builder.build(name)
        url = self._app_builder.deploy(name, target="local")
        result = self._app_builder.deliver(name)
        return json.dumps(result, indent=2)

    def app_status(self, nome=None):
        if not nome:
            return "Use: app_status <nome-do-projeto>"
        meta = self._app_builder.get_project(nome)
        if not meta:
            return "Projeto nao encontrado."
        return json.dumps(meta, indent=2)

    def app_list(self):
        projects = self._app_builder.list_projects()
        if not projects:
            return "Nenhum projeto criado ainda."
        lines = [f"• {p['name']} ({p['type']}) - {p['status']}" for p in projects]
        return "\n".join(lines)

    def app_deploy(self, nome=None, target="github"):
        if not nome:
            return "Use: app_deploy <nome-do-projeto> [target=github|local]"
        url = self._app_builder.deploy(nome, target)
        return f"Deploy de '{nome}' em: {url}"


EXTRA_TOOLS = [
    ("system_monitor", ExtraTools.system_monitor,
     "Monitorar CPU/RAM/disco/rede em tempo real", {}),
    ("process_list", ExtraTools.process_list,
     "Listar processos do sistema", {}),
    ("process_kill", ExtraTools.process_kill,
     "Finalizar processo por PID ou nome",
     {"pid": {"type": "integer"}, "name": {"type": "string"}}),
    ("service_control", ExtraTools.service_control,
     "Controlar serviço systemd (start/stop/restart/status)",
     {"action": {"type": "string"}, "service": {"type": "string"}}),
    ("file_search", ExtraTools.file_search,
     "Buscar texto em arquivos (.py/.txt/.json/.md)",
     {"pattern": {"type": "string"}, "path": {"type": "string"}}),
    ("file_read", ExtraTools.file_read,
     "Ler conteúdo de arquivo texto",
     {"path": {"type": "string"}}),
    ("file_write", ExtraTools.file_write,
     "Escrever conteúdo em arquivo",
     {"path": {"type": "string"}, "content": {"type": "string"}}),
    ("file_delete", ExtraTools.file_delete,
     "Deletar arquivo ou diretório",
     {"path": {"type": "string"}}),
    ("file_copy_move", ExtraTools.file_copy_move,
     "Copiar ou mover arquivo/diretório",
     {"source": {"type": "string"}, "dest": {"type": "string"}, "action": {"type": "string"}}),
    ("bluetooth_control", ExtraTools.bluetooth_control,
     "Controlar Bluetooth (status/scan/connect)",
     {"action": {"type": "string"}, "device": {"type": "string"}}),
    ("power_control", ExtraTools.power_control,
     "Desligar/reiniciar/suspender sistema",
     {"action": {"type": "string"}}),
    ("package_search_install", ExtraTools.package_search_install,
     "Buscar ou instalar pacotes apt",
     {"action": {"type": "string"}, "package": {"type": "string"}}),
    ("clipboard_set", ExtraTools.clipboard_set,
     "Copiar texto para área de transferência",
     {"text": {"type": "string"}}),
    ("download_file", ExtraTools.download_file,
     "Baixar arquivo da internet",
     {"url": {"type": "string"}, "dest": {"type": "string"}}),
    ("network_info", ExtraTools.network_info,
     "Informações de rede (interfaces, IPs)", {}),
    ("port_scan", ExtraTools.port_scan,
     "Escanear portas abertas com nmap",
     {"target": {"type": "string"}, "port_range": {"type": "string"}}),
    ("wifi_scan", ExtraTools.wifi_scan,
     "Escanear redes WiFi disponíveis", {}),
    ("hash_file", ExtraTools.hash_file,
     "Calcular hash de arquivo (md5/sha256/sha1)",
     {"path": {"type": "string"}, "algorithm": {"type": "string"}}),
    ("password_generate", ExtraTools.password_generate,
     "Gerar senha segura aleatória",
     {"length": {"type": "integer"}, "use_symbols": {"type": "boolean"}}),
    ("vpn_control", ExtraTools.vpn_control,
     "Controlar VPN WireGuard (status/up/down)",
     {"action": {"type": "string"}, "config": {"type": "string"}}),
    ("camera_capture", ExtraTools.camera_capture,
     "Capturar foto da webcam",
     {"output": {"type": "string"}}),
    ("record_audio", ExtraTools.record_audio,
     "Gravar áudio do microfone",
     {"duration": {"type": "integer"}, "output": {"type": "string"}}),
    ("play_audio", ExtraTools.play_audio,
     "Tocar arquivo de áudio",
     {"path": {"type": "string"}}),
    ("image_manipulate", ExtraTools.image_manipulate,
     "Manipular imagem (resize/convert/rotate/info)",
     {"action": {"type": "string"}, "path": {"type": "string"}}),
    ("pdf_generate", ExtraTools.pdf_generate,
     "Gerar PDF a partir de texto",
     {"content": {"type": "string"}, "output": {"type": "string"}}),
    ("ocr_file", ExtraTools.ocr_file,
     "Extrair texto de imagem/PDF via OCR",
     {"path": {"type": "string"}}),
    ("docker_ps", ExtraTools.docker_ps,
     "Listar containers Docker", {}),
    ("docker_exec", ExtraTools.docker_exec,
     "Executar comando em container Docker",
     {"container": {"type": "string"}, "command": {"type": "string"}}),
    ("git_status", ExtraTools.git_status,
     "Status do repositório git",
     {"path": {"type": "string"}}),
    ("git_commit", ExtraTools.git_commit,
     "Git add + commit",
     {"path": {"type": "string"}, "message": {"type": "string"}}),
    ("api_request", ExtraTools.api_request,
     "Requisição HTTP genérica (GET/POST/PUT/DELETE)",
     {"method": {"type": "string"}, "url": {"type": "string"}, "headers": {"type": "string"}, "body": {"type": "string"}}),
    ("sql_query", ExtraTools.sql_query,
     "Executar query SQL em arquivo SQLite",
     {"db_path": {"type": "string"}, "query": {"type": "string"}}),
    ("model_switch", ExtraTools.model_switch,
     "Trocar modelo Ollama em tempo real",
     {"model": {"type": "string"}}),
    ("send_email", ExtraTools.send_email,
     "Enviar email via SMTP",
     {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}),
    ("send_notification", ExtraTools.send_notification,
     "Enviar notificação desktop",
     {"title": {"type": "string"}, "message": {"type": "string"}}),
    ("http_server", ExtraTools.http_server,
     "Iniciar servidor HTTP local para compartilhar arquivos",
     {"port": {"type": "integer"}, "directory": {"type": "string"}}),
    ("http_server_stop", ExtraTools.http_server_stop,
     "Parar servidor HTTP", {}),
    ("telegram_send", ExtraTools.telegram_send,
     "Enviar mensagem Telegram via bot (token/chat_id da config ou parâmetros)",
     {"text": {"type": "string"}, "token": {"type": "string"}, "chat_id": {"type": "string"}}),
    ("telegram_listener_start", ExtraTools.telegram_listener_start,
     "Iniciar listener Telegram para receber comandos via chat", {}),
    ("telegram_listener_stop", ExtraTools.telegram_listener_stop,
     "Parar listener Telegram", {}),
    ("credential_save", ExtraTools.credential_save,
     "Salvar credencial criptografada (service, username, password)",
     {"service": {"type": "string"}, "username": {"type": "string"}, "password": {"type": "string"}, "notes": {"type": "string"}}),
    ("credential_get", ExtraTools.credential_get,
     "Recuperar credencial descriptografada pelo nome do serviço",
     {"service": {"type": "string"}}),
    ("credential_list", ExtraTools.credential_list,
     "Listar nomes de todas as credenciais salvas", {}),
    ("credential_delete", ExtraTools.credential_delete,
     "Remover credencial do cofre",
     {"service": {"type": "string"}}),
    ("app_builder", ExtraTools.app_builder,
     "Criar app/site completo a partir de descricao. Ex: 'cria um app de tarefas'",
     {"descricao": {"type": "string"}}),
    ("app_status", ExtraTools.app_status,
     "Ver status de um projeto",
     {"nome": {"type": "string"}}),
    ("app_list", ExtraTools.app_list,
     "Listar todos os projetos criados", {}),
    ("app_deploy", ExtraTools.app_deploy,
     "Fazer deploy de um projeto",
     {"nome": {"type": "string"}, "target": {"type": "string"}}),
]
