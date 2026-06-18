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

    # ── NOVAS FERRAMENTAS ──────────────────────────────────

    def volume_control(self, action="get", value=None):
        try:
            if action == "get":
                out = self._sh("pactl get-sink-volume @DEFAULT_SINK@ 2>&1")
                mute = self._sh("pactl get-sink-mute @DEFAULT_SINK@ 2>&1")
                return f"Volume: {out.strip() or 'N/A'} | Mudo: {mute.strip() or 'N/A'}"
            elif action == "set" and value is not None:
                return self._sh(f"pactl set-sink-volume @DEFAULT_SINK@ {value}% 2>&1") or f"Volume ajustado para {value}%"
            elif action == "up":
                return self._sh("pactl set-sink-volume @DEFAULT_SINK@ +5% 2>&1") or "Volume +5%"
            elif action == "down":
                return self._sh("pactl set-sink-volume @DEFAULT_SINK@ -5% 2>&1") or "Volume -5%"
            elif action == "mute":
                return self._sh("pactl set-sink-mute @DEFAULT_SINK@ 1 2>&1") or "Áudio mutado"
            elif action == "unmute":
                return self._sh("pactl set-sink-mute @DEFAULT_SINK@ 0 2>&1") or "Áudio ativado"
            return f"Ação '{action}' inválida (use: get/set/up/down/mute/unmute)"
        except Exception as e:
            return f"Erro volume: {e}"

    def brightness_control(self, action="get", value=None):
        try:
            if action == "get":
                out = self._sh("brightnessctl g 2>&1")
                maxb = self._sh("brightnessctl m 2>&1")
                return f"Brilho: {out.strip()}/{maxb.strip()}" if maxb else f"Brilho: {out.strip()}"
            elif action == "set" and value is not None:
                return self._sh(f"brightnessctl s {value}% 2>&1") or f"Brilho ajustado para {value}%"
            elif action == "up":
                return self._sh("brightnessctl s +5% 2>&1") or "Brilho +5%"
            elif action == "down":
                return self._sh("brightnessctl s 5%- 2>&1") or "Brilho -5%"
            return f"Ação '{action}' inválida (use: get/set/up/down)"
        except Exception as e:
            return f"Erro brilho: {e}"

    def media_control(self, action="play_pause"):
        try:
            valid = {"play_pause", "next", "previous", "stop", "get", "play", "pause"}
            if action not in valid:
                return f"Ação inválida: {action} (use: {', '.join(sorted(valid))})"
            if action == "get":
                out = self._sh("playerctl metadata --format '{{artist}} - {{title}} ({{status}})' 2>&1")
                return out or "Nenhuma mídia tocando"
            out = self._sh(f"playerctl {action} 2>&1")
            return out or f"Media {action}"
        except Exception as e:
            return f"Erro media: {e}"

    def calendar_query(self, month=None, year=None):
        try:
            import calendar as cal_mod
            now = __import__('datetime').datetime.now()
            m = int(month) if month else now.month
            y = int(year) if year else now.year
            return cal_mod.TextCalendar().formatmonth(y, m)
        except Exception as e:
            return f"Erro calendário: {e}"

    def weather(self, location=None):
        try:
            loc = location or ""
            import urllib.request
            url = f"https://wttr.in/{urllib.parse.quote(loc)}?format=%C+%t+%h+%w&lang=pt"
            with urllib.request.urlopen(url, timeout=10) as r:
                return f"Clima {location or 'local'}: {r.read().decode().strip()}"
        except Exception as e:
            return f"Erro clima: {e}"

    def calculator(self, expression=None):
        if not expression:
            return "Expressão necessária (ex: '2 + 2')"
        import ast, math, operator as op_mod
        safe_ops = {
            ast.Add: op_mod.add, ast.Sub: op_mod.sub, ast.Mult: op_mod.mul,
            ast.Div: op_mod.truediv, ast.Pow: op_mod.pow, ast.Mod: op_mod.mod,
            ast.FloorDiv: op_mod.floordiv, ast.UAdd: op_mod.pos, ast.USub: op_mod.neg,
        }
        def _eval(node):
            if isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.BinOp):
                return safe_ops[type(node.op)](_eval(node.left), _eval(node.right))
            elif isinstance(node, ast.UnaryOp):
                return safe_ops[type(node.op)](_eval(node.operand))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ('abs', 'int', 'float', 'round', 'min', 'max', 'sum'):
                    args = [_eval(a) for a in node.args]
                    return getattr(__builtins__, node.func.id)(*args)
            raise ValueError("Expressão não permitida")
        try:
            tree = ast.parse(expression.strip(), mode='eval')
            result = _eval(tree.body)
            return str(result)
        except Exception as e:
            return f"Erro cálculo: {e}"

    def notes_save(self, title=None, content=None):
        if not title or content is None:
            return "title e content são necessários"
        notes_dir = os.path.expanduser("~/.jarvis/notes")
        os.makedirs(notes_dir, exist_ok=True)
        path = os.path.join(notes_dir, title.replace(" ", "_") + ".md")
        try:
            with open(path, "w") as f:
                f.write(content)
            return f"Nota salva: {path}"
        except Exception as e:
            return f"Erro: {e}"

    def notes_read(self, title=None):
        if not title:
            return "title é necessário"
        notes_dir = os.path.expanduser("~/.jarvis/notes")
        path = os.path.join(notes_dir, title.replace(" ", "_") + ".md")
        if not os.path.exists(path):
            return f"Nota '{title}' não encontrada"
        try:
            with open(path) as f:
                return f.read()[:3000]
        except Exception as e:
            return f"Erro: {e}"

    def notes_list(self):
        notes_dir = os.path.expanduser("~/.jarvis/notes")
        if not os.path.isdir(notes_dir):
            return "Nenhuma nota salva ainda."
        try:
            notes = sorted(os.listdir(notes_dir))
            if not notes:
                return "Nenhuma nota salva ainda."
            lines = []
            for n in notes:
                path = os.path.join(notes_dir, n)
                size = os.path.getsize(path)
                lines.append(f"• {n.replace('.md','')} ({size}B)")
            return "\n".join(lines)
        except Exception as e:
            return f"Erro: {e}"

    def translate(self, text=None, target_lang="pt", source_lang="auto"):
        if not text:
            return "text é necessário"
        try:
            from deep_translator import GoogleTranslator
            result = GoogleTranslator(source=source_lang, target=target_lang).translate(text)
            return result or "Tradução falhou"
        except ImportError:
            return "deep_translator não instalado (pip install deep-translator)"
        except Exception as e:
            return f"Erro tradução: {e}"

    def qrcode_generate(self, data=None, output=None):
        if not data:
            return "data é necessário (texto ou URL para codificar)"
        output = output or os.path.expanduser(f"~/Pictures/qrcode_{int(time.time())}.png")
        os.makedirs(os.path.dirname(output), exist_ok=True)
        try:
            import qrcode
            img = qrcode.make(data)
            img.save(output)
            return f"QR Code salvo: {output}"
        except ImportError:
            return "qrcode não instalado (pip install qrcode[pil])"
        except Exception as e:
            return f"Erro: {e}"

    def timer(self, duration=None, message="Tempo esgotou!"):
        if not duration:
            return "duration é necessário (em segundos)"
        try:
            secs = int(duration)
            threading.Thread(target=self._timer_thread, args=(secs, message), daemon=True).start()
            return f"Timer de {secs}s iniciado: '{message}'"
        except Exception as e:
            return f"Erro: {e}"

    def _timer_thread(self, secs, message):
        time.sleep(secs)
        self.send_notification("Jarvis Timer", message)

    def screenshot_region(self, x=0, y=0, width=800, height=600, output=None):
        output = output or os.path.expanduser(f"~/Pictures/region_{int(time.time())}.png")
        os.makedirs(os.path.dirname(output), exist_ok=True)
        try:
            import pyautogui
            img = pyautogui.screenshot(region=(x, y, width, height))
            img.save(output)
            return f"Screenshot da região salvo: {output}"
        except Exception as e:
            return f"Erro: {e}"

    def window_list(self):
        try:
            out = self._sh("wmctrl -l 2>&1 | head -50")
            if out and "comando" not in out.lower():
                return out
            out = self._sh("xdotool search . 2>&1 | head -50 && xdotool getactivewindow getwindowname 2>&1")
            return out or "Lista de janelas indisponível"
        except Exception as e:
            return f"Erro: {e}"

    def window_focus(self, title=None):
        if not title:
            return "title é necessário (nome ou parte da janela)"
        try:
            out = self._sh(f"wmctrl -a '{title}' 2>&1")
            if not out or "Failed" not in out:
                return f"Janela '{title}' focada"
            out = self._sh(f"xdotool search --name '{title}' windowactivate 2>&1")
            return out or f"Janela '{title}' focada"
        except Exception as e:
            return f"Erro: {e}"

    def clipboard_history(self, limit=10):
        try:
            import pyperclip
            current = pyperclip.paste()
            hist_dir = os.path.expanduser("~/.jarvis/clipboard")
            os.makedirs(hist_dir, exist_ok=True)
            hist_file = os.path.join(hist_dir, "history.txt")
            entries = []
            if os.path.exists(hist_file):
                with open(hist_file) as f:
                    entries = [l.rstrip("\n") for l in f.readlines() if l.strip()]
            if current and (not entries or entries[0] != current):
                entries.insert(0, current)
                with open(hist_file, "w") as f:
                    f.write("\n".join(entries[:50]))
            shown = entries[:limit]
            if not shown:
                return "Histório vazio"
            lines = [f"{i+1}. {e[:100]}" for i, e in enumerate(shown)]
            return "\n".join(lines)
        except Exception as e:
            return f"Erro: {e}"

    def ssh_exec(self, host=None, command=None, user=None, password=None, port=22):
        if not host or not command:
            return "host e command são necessários"
        try:
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if password:
                client.connect(host, port=int(port), username=user or "root", password=password, timeout=15)
            else:
                client.connect(host, port=int(port), username=user or "root", timeout=15)
            _, stdout, stderr = client.exec_command(command, timeout=30)
            out = stdout.read().decode()[:2000]
            err = stderr.read().decode()[:500]
            client.close()
            if out:
                return out
            return err or "Comando executado sem saída"
        except ImportError:
            return "paramiko não instalado (pip install paramiko)"
        except Exception as e:
            return f"Erro SSH: {e}"

    def compress_file(self, source=None, output=None, format="zip"):
        if not source:
            return "source é necessário (arquivo ou diretório)"
        source = os.path.expanduser(source)
        if not os.path.exists(source):
            return f"Arquivo/diretório não encontrado: {source}"
        if not output:
            base = os.path.basename(source.rstrip("/"))
            ext = ".tar.gz" if format in ("tar.gz", "tgz") else ".tar.bz2" if format == "tar.bz2" else ".zip"
            output = os.path.join(os.path.dirname(source) or ".", base + ext)
        output = os.path.expanduser(output)
        try:
            if format == "zip":
                import zipfile
                with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
                    if os.path.isfile(source):
                        zf.write(source, os.path.basename(source))
                    else:
                        for root, dirs, files in os.walk(source):
                            for fn in files:
                                fp = os.path.join(root, fn)
                                zf.write(fp, os.path.relpath(fp, os.path.dirname(source)))
            else:
                import tarfile
                mode = "w:gz" if "gz" in format else "w:bz2" if "bz2" in format else "w"
                with tarfile.open(output, mode) as tf:
                    tf.add(source, arcname=os.path.basename(source.rstrip("/")))
            return f"Compactado: {output}"
        except Exception as e:
            return f"Erro compressão: {e}"

    def location_info(self, ip=None):
        try:
            import urllib.request, json
            if ip:
                url = f"http://ip-api.com/json/{ip}"
            else:
                url = "http://ip-api.com/json"
            with urllib.request.urlopen(url, timeout=10) as r:
                data = json.loads(r.read())
            if data.get("status") == "fail":
                return f"Localização não encontrada para {ip or 'seu IP'}"
            parts = [
                f"IP: {data.get('query', '?')}",
                f"Cidade: {data.get('city', '?')}",
                f"Região: {data.get('regionName', '?')}",
                f"País: {data.get('country', '?')}",
                f"ISP: {data.get('isp', '?')}",
                f"Lat/Lon: {data.get('lat', '?')}, {data.get('lon', '?')}",
            ]
            return "\n".join(parts)
        except Exception as e:
            return f"Erro localização: {e}"

    def currency_convert(self, amount=1, from_currency="USD", to_currency="BRL"):
        try:
            import urllib.request, json
            url = f"https://api.frankfurter.dev/latest?from={from_currency.upper()}&to={to_currency.upper()}"
            with urllib.request.urlopen(url, timeout=10) as r:
                data = json.loads(r.read())
            rate = data["rates"][to_currency.upper()]
            result = float(amount) * rate
            return f"{amount} {from_currency.upper()} = {result:.2f} {to_currency.upper()} (taxa: {rate})"
        except Exception as e:
            return f"Erro conversão: {e}"

    def text_to_speech(self, text=None, lang="pt"):
        if not text:
            return "text é necessário"
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 150)
            engine.setProperty("volume", 1.0)
            voices = engine.getProperty("voices")
            for v in voices:
                if "portuguese" in v.name.lower() or "brazil" in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break
            engine.say(text)
            engine.runAndWait()
            return f"Falado: {text[:50]}..."
        except ImportError:
            return "pyttsx3 não instalado (pip install pyttsx3)"
        except Exception as e:
            return f"Erro TTS: {e}"

    def audio_transcribe(self, path=None):
        if not path:
            return "path é necessário (caminho do arquivo de áudio)"
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return f"Arquivo não encontrado: {path}"
        try:
            import whisper
            model = whisper.load_model("base")
            result = model.transcribe(path, language="pt")
            return result.get("text", "").strip() or "Nada transcrito"
        except ImportError:
            return "whisper não instalado (pip install openai-whisper)"
        except Exception as e:
            return f"Erro transcrição: {e}"

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

    # === VOLUME CONTROL ===
    def volume_control(self, action="get", value=None):
        if action == "get":
            out = self._sh("pactl get-sink-volume @DEFAULT_SINK@ 2>&1")
            return out or self._sh("amixer get Master 2>&1 | grep -o '[0-9]*%' | head -1") or "Volume não disponível"
        if action == "mute":
            self._sh("pactl set-sink-mute @DEFAULT_SINK@ 1 2>&1")
            return "Volume mutado."
        if action == "unmute":
            self._sh("pactl set-sink-mute @DEFAULT_SINK@ 0 2>&1")
            return "Volume ativado."
        if action == "toggle":
            self._sh("pactl set-sink-mute @DEFAULT_SINK@ toggle 2>&1")
            return "Volume alternado."
        if action in ("up", "down"):
            pct = value or 5
            self._sh(f"pactl set-sink-volume @DEFAULT_SINK@ {'+%d%%' % pct if action == 'up' else '-%d%%' % pct} 2>&1")
            return f"Volume {'aumentado' if action == 'up' else 'diminuido'} {pct}%."
        if action == "set" and value is not None:
            self._sh(f"pactl set-sink-volume @DEFAULT_SINK@ {value}% 2>&1")
            return f"Volume ajustado para {value}%."
        return "Use action=get|up|down|set|mute|unmute|toggle [value=N]"

    # === BRIGHTNESS CONTROL ===
    def brightness_control(self, action="get", value=None):
        if action == "get":
            out = self._sh("brightnessctl g 2>&1")
            if out and out.strip().isdigit():
                max_b = self._sh("brightnessctl m 2>&1").strip()
                pct = int(out.strip()) * 100 // int(max_b) if max_b.isdigit() else 0
                return f"Brilho: {pct}%"
            return "brightnessctl não disponível"
        if action == "set" and value is not None:
            self._sh(f"brightnessctl s {value}% 2>&1")
            return f"Brilho ajustado para {value}%."
        if action == "up":
            self._sh(f"brightnessctl s +{value or 5}% 2>&1")
            return "Brilho aumentado."
        if action == "down":
            self._sh(f"brightnessctl s {value or 5}-% 2>&1")
            return "Brilho diminuído."
        return "Use action=get|up|down|set [value=N]"

    # === MEDIA CONTROL ===
    def media_control(self, action="play-pause"):
        valid = ("play", "pause", "next", "previous", "stop", "play-pause")
        if action not in valid:
            return f"Ação inválida. Use: {', '.join(valid)}"
        out = self._sh(f"playerctl {action} 2>&1")
        if "No players" in out or "Could not" in out:
            return "Nenhum player de mídia encontrado."
        return f"Mídia: {action}."

    # === CALENDAR ===
    def calendar_query(self, date=None):
        import calendar as cal_mod
        from datetime import datetime
        if date:
            try:
                dt = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                return "Formato inválido. Use YYYY-MM-DD"
        else:
            dt = datetime.now()
        cal_text = cal_mod.TextCalendar().formatmonth(dt.year, dt.month)
        return cal_text

    # === WEATHER ===
    def weather(self, city=None):
        try:
            import requests
            if city:
                url = f"https://wttr.in/{city}?format=%C+%t+%h+%w&lang=pt"
            else:
                url = "https://wttr.in?format=%C+%t+%h+%w&lang=pt"
            r = requests.get(url, timeout=10, headers={"User-Agent": "curl/7.68"})
            if r.status_code == 200:
                return f"Clima: {r.text.strip()}"
            return f"Erro ao obter clima: {r.status_code}"
        except ImportError:
            return "requests não instalado"
        except Exception as e:
            return f"Erro: {e}"

    # === CALCULATOR ===
    def calculator(self, expression=None):
        if not expression:
            return "Expressão necessária (ex: '2 + 2 * 3')"
        import ast, math, operator as op_mod
        allowed = {
            ast.Add: op_mod.add, ast.Sub: op_mod.sub, ast.Mult: op_mod.mul,
            ast.Div: op_mod.truediv, ast.Pow: op_mod.pow, ast.USub: op_mod.neg,
            ast.FloorDiv: op_mod.floordiv, ast.Mod: op_mod.mod,
        }
        def _eval(node):
            if isinstance(node, ast.Expression):
                return _eval(node.body)
            if isinstance(node, ast.Constant):
                return node.n if isinstance(node.n, (int, float)) else node.value
            if isinstance(node, ast.BinOp):
                return allowed[type(node.op)](_eval(node.left), _eval(node.right))
            if isinstance(node, ast.UnaryOp):
                return allowed[type(node.op)](_eval(node.operand))
            raise ValueError(f"Expressão inválida: {type(node).__name__}")
        try:
            tree = ast.parse(expression.strip(), mode="eval")
            result = _eval(tree)
            return f"{expression} = {result}"
        except Exception as e:
            return f"Erro ao calcular: {e}"

    # === NOTES ===
    def notes_save(self, title=None, content=None):
        if not title or content is None:
            return "title e content necessários"
        notes_dir = os.path.expanduser("~/.jarvis/notes")
        os.makedirs(notes_dir, exist_ok=True)
        path = os.path.join(notes_dir, title.replace(" ", "_") + ".txt")
        with open(path, "w") as f:
            f.write(content)
        return f"Nota '{title}' salva."

    def notes_read(self, title=None):
        if not title:
            return "title necessário"
        path = os.path.expanduser(f"~/.jarvis/notes/{title.replace(' ', '_')}.txt")
        try:
            with open(path) as f:
                return f.read()[:3000]
        except FileNotFoundError:
            return f"Nota '{title}' não encontrada."

    def notes_list(self):
        notes_dir = os.path.expanduser("~/.jarvis/notes")
        if not os.path.isdir(notes_dir):
            return "Nenhuma nota salva."
        notes = sorted(os.listdir(notes_dir))
        if not notes:
            return "Nenhuma nota salva."
        return "\n".join(f"• {n.replace('.txt', '')}" for n in notes)

    # === TRANSLATE ===
    def translate(self, text=None, to_lang="pt", from_lang="auto"):
        if not text:
            return "text necessário"
        try:
            from deep_translator import GoogleTranslator
            result = GoogleTranslator(source=from_lang, target=to_lang).translate(text)
            return f"[{from_lang}→{to_lang}] {result}"
        except ImportError:
            try:
                import requests
                url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={from_lang}&tl={to_lang}&dt=t&q={text[:5000]}"
                r = requests.get(url, timeout=10)
                parts = json.loads(r.text)
                result = "".join(p[0] for p in parts[0] if p[0])
                return f"[{from_lang}→{to_lang}] {result}"
            except Exception as e:
                return f"Erro: {e}"
        except Exception as e:
            return f"Erro: {e}"

    # === QR CODE ===
    def qrcode_generate(self, data=None, output=None):
        if not data:
            return "data necessário (texto ou URL para codificar)"
        output = os.path.expanduser(output or f"~/Pictures/jarvis_qrcode_{int(time.time())}.png")
        os.makedirs(os.path.dirname(output), exist_ok=True)
        try:
            import qrcode
            img = qrcode.make(data)
            img.save(output)
            return f"QR Code salvo: {output}"
        except ImportError:
            try:
                import requests
                url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={data[:2000]}"
                r = requests.get(url, timeout=15)
                with open(output, "wb") as f:
                    f.write(r.content)
                return f"QR Code salvo: {output}"
            except Exception as e:
                return f"Erro: {e}"
        except Exception as e:
            return f"Erro: {e}"

    # === TIMER ===
    def timer(self, seconds=None, message="Alarme!"):
        if not seconds or seconds < 1:
            return "seconds necessário (>= 1)"
        import threading as thr
        def _alarm():
            time.sleep(seconds)
            self.send_notification("Jarvis Timer", message)
        thr.Thread(target=_alarm, daemon=True).start()
        return f"Timer de {seconds}s agendado: {message}"

    # === SCREENSHOT REGION ===
    def screenshot_region(self, x=0, y=0, width=800, height=600, output=None):
        output = output or os.path.expanduser(f"~/Pictures/jarvis_region_{int(time.time())}.png")
        os.makedirs(os.path.dirname(output), exist_ok=True)
        try:
            import pyautogui
            img = pyautogui.screenshot(region=(x, y, width, height))
            img.save(output)
            return f"Screenshot da região ({x},{y},{width}x{height}) salvo: {output}"
        except ImportError:
            return "pyautogui não instalado"
        except Exception as e:
            return f"Erro: {e}"

    # === WINDOW LIST / FOCUS ===
    def window_list(self):
        out = self._sh("wmctrl -l 2>&1")
        if out and "command not found" not in out:
            return out[:2000]
        out2 = self._sh("xdotool getactivewindow getwindowname 2>&1 && xdotool search '' 2>&1 | head -30")
        return out2 or "wmctrl/xdotool não disponíveis"
    
    def window_focus(self, title=None):
        if not title:
            return "title necessário (parte do título da janela)"
        out = self._sh(f"wmctrl -a '{title}' 2>&1")
        if "command not found" in out:
            out2 = self._sh(f"xdotool search --name '{title}' windowactivate 2>&1")
            return out2 or f"Focado: {title}"
        return f"Janela '{title}' focada."

    # === CLIPBOARD HISTORY ===
    def clipboard_history(self, action="list"):
        hist_file = os.path.expanduser("~/.jarvis/clipboard_history.jsonl")
        if action == "clear":
            try:
                os.remove(hist_file)
                return "Histórico da área de transferência limpo."
            except FileNotFoundError:
                return "Histórico vazio."
        if not os.path.exists(hist_file):
            return "Nenhum histórico ainda."
        with open(hist_file) as f:
            lines = f.readlines()
        entries = [json.loads(l)["text"][:80] for l in lines[-10:]]
        return "\n".join(f"{i+1}. {e}" for i, e in enumerate(entries))

    # === SSH EXEC ===
    def ssh_exec(self, host=None, command=None, user=None, port=22):
        if not host or not command:
            return "host e command necessários"
        ssh_cmd = f"ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -p {port}"
        if user:
            ssh_cmd += f" {user}@{host}"
        else:
            ssh_cmd += f" {host}"
        ssh_cmd += f" {command}"
        out = self._sh(ssh_cmd)
        if "Permission denied" in out:
            return "Acesso SSH negado. Verifique credenciais."
        return out or "Comando executado sem saída."

    # === COMPRESS FILE ===
    def compress_file(self, source=None, output=None, format="zip"):
        if not source:
            return "source necessário (arquivo ou diretório)"
        source = os.path.expanduser(source)
        output = os.path.expanduser(output or f"{source}.{format}")
        try:
            import shutil
            root, base = os.path.split(source)
            if format == "zip":
                return shutil.make_archive(output.replace(".zip", ""), "zip", root, base)
            elif format == "tar":
                return shutil.make_archive(output.replace(".tar.gz", ""), "gztar", root, base)
            elif format == "tar.gz":
                return shutil.make_archive(output.replace(".tar.gz", ""), "gztar", root, base)
            else:
                return f"Formato não suportado: {format} (use zip, tar, tar.gz)"
        except Exception as e:
            return f"Erro: {e}"

    # === LOCATION ===
    def location_info(self):
        try:
            import requests
            r = requests.get("http://ip-api.com/json/", timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "success":
                    return (f"IP: {data.get('query')}\n"
                            f"País: {data.get('country')}\n"
                            f"Região: {data.get('regionName')}\n"
                            f"Cidade: {data.get('city')}\n"
                            f"ISP: {data.get('isp')}")
                return json.dumps(data, indent=2)
            return f"Erro HTTP {r.status_code}"
        except ImportError:
            return "requests não instalado"
        except Exception as e:
            return f"Erro: {e}"

    # === CURRENCY CONVERT ===
    def currency_convert(self, value=1.0, from_currency="USD", to_currency="BRL"):
        try:
            import requests
            url = f"https://api.frankfurter.app/latest?from={from_currency.upper()}&to={to_currency.upper()}"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                rate = data["rates"][to_currency.upper()]
                converted = round(value * rate, 2)
                return f"{value} {from_currency.upper()} = {converted} {to_currency.upper()} (taxa: {rate})"
            return f"Erro API: {r.status_code}"
        except ImportError:
            return "requests não instalado"
        except Exception as e:
            return f"Erro: {e}"

    # === TEXT TO SPEECH ===
    def text_to_speech(self, text=None, output=None):
        if not text:
            return "text necessário"
        output = output or os.path.expanduser(f"~/Pictures/jarvis_tts_{int(time.time())}.wav")
        os.makedirs(os.path.dirname(output), exist_ok=True)
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.save_to_file(text, output)
            engine.runAndWait()
            return f"Áudio salvo: {output}"
        except ImportError:
            out = self._sh(f'espeak-ng "{text}" -w {output} 2>&1 || espeak "{text}" -w {output} 2>&1')
            if os.path.exists(output):
                return f"Áudio salvo: {output}"
            return "TTS não disponível (instale pyttsx3 ou espeak-ng)"

    # === AUDIO TRANSCRIBE ===
    def audio_transcribe(self, path=None):
        if not path:
            return "path necessário (caminho do arquivo de áudio)"
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return "Arquivo não encontrado."
        try:
            import whisper
            model = whisper.load_model("base")
            result = model.transcribe(path, language="pt")
            return result["text"][:3000]
        except ImportError:
            try:
                from faster_whisper import WhisperModel
                model = WhisperModel("base", device="cpu", compute_type="int8")
                segments, _ = model.transcribe(path, language="pt")
                return " ".join(s.text for s in segments)[:3000]
            except ImportError:
                return "Nenhum motor de transcrição (pip install faster-whisper)"
        except Exception as e:
            return f"Erro: {e}"

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

    # === DATABASE: PostgreSQL ===
    def pg_query(self, conn_string=None, query=None):
        if not conn_string or not query:
            return "conn_string e query necessários. Ex: postgresql://user:pass@localhost:5432/db"
        try:
            import psycopg2
            conn = psycopg2.connect(conn_string)
            cur = conn.cursor()
            cur.execute(query)
            if query.strip().upper().startswith("SELECT"):
                rows = cur.fetchmany(50)
                cols = [d[0] for d in cur.description]
                result = "\t".join(cols) + "\n" + "\n".join("\t".join(str(c) for c in r) for r in rows)
            else:
                conn.commit()
                result = f"Query executada. Linhas afetadas: {cur.rowcount}"
            cur.close()
            conn.close()
            return result
        except ImportError:
            return "psycopg2 não instalado (pip install psycopg2-binary)"
        except Exception as e:
            return f"Erro PostgreSQL: {e}"

    # === DATABASE: MySQL ===
    def mysql_query(self, conn_string=None, query=None):
        if not conn_string or not query:
            return "conn_string e query necessários. Ex: mysql+pymysql://user:pass@localhost:3306/db"
        try:
            import pymysql
            import re
            m = re.match(r"mysql\+pymysql://(.+?):(.+?)@(.+?):(\d+)/(.+)", conn_string)
            if not m:
                m = re.match(r"mysql://(.+?):(.+?)@(.+?):(\d+)/(.+)", conn_string)
            if not m:
                return "Formato: mysql://user:pass@host:port/db ou mysql+pymysql://..."
            user, pw, host, port, db = m.group(1), m.group(2), m.group(3), int(m.group(4)), m.group(5)
            conn = pymysql.connect(host=host, port=port, user=user, password=pw, database=db)
            cur = conn.cursor()
            cur.execute(query)
            if query.strip().upper().startswith("SELECT"):
                rows = cur.fetchmany(50)
                cols = [d[0] for d in cur.description]
                result = "\t".join(cols) + "\n" + "\n".join("\t".join(str(c) for c in r) for r in rows)
            else:
                conn.commit()
                result = f"Query executada. Linhas afetadas: {cur.rowcount}"
            cur.close()
            conn.close()
            return result
        except ImportError:
            return "pymysql não instalado (pip install pymysql)"
        except Exception as e:
            return f"Erro MySQL: {e}"

    # === DATABASE: MongoDB ===
    def mongo_find(self, conn_string=None, collection=None, filter_query=None, limit=10):
        if not conn_string or not collection:
            return "conn_string e collection necessários. Ex: mongodb://localhost:27017/mydb"
        try:
            from pymongo import MongoClient
            client = MongoClient(conn_string, serverSelectionTimeoutMS=5000)
            db_name = conn_string.split("/")[-1].split("?")[0]
            db = client.get_default_database()
            if db.name == "admin" and db_name and "admin" not in db_name:
                db = client[db_name]
            filt = json.loads(filter_query) if filter_query and isinstance(filter_query, str) else (filter_query or {})
            docs = list(db[collection].find(filt).limit(limit))
            client.close()
            if not docs:
                return "Nenhum documento encontrado."
            return json.dumps([{k: str(v) for k, v in d.items()} for d in docs], indent=2, ensure_ascii=False)
        except ImportError:
            return "pymongo não instalado (pip install pymongo)"
        except Exception as e:
            return f"Erro MongoDB: {e}"

    def mongo_insert(self, conn_string=None, collection=None, document=None):
        if not conn_string or not collection or not document:
            return "conn_string, collection e document necessários"
        try:
            from pymongo import MongoClient
            client = MongoClient(conn_string, serverSelectionTimeoutMS=5000)
            db = client.get_default_database()
            doc = json.loads(document) if isinstance(document, str) else document
            result = db[collection].insert_one(doc)
            client.close()
            return f"Documento inserido em '{collection}': _id={result.inserted_id}"
        except ImportError:
            return "pymongo não instalado (pip install pymongo)"
        except Exception as e:
            return f"Erro MongoDB insert: {e}"

    # === DATABASE: Redis ===
    def redis_get(self, key=None, conn_string="redis://localhost:6379/0"):
        if not key:
            return "key necessária"
        try:
            import redis as _redis
            r = _redis.from_url(conn_string)
            val = r.get(key)
            r.close()
            if val is None:
                return f"Chave '{key}' não encontrada"
            return val.decode() if isinstance(val, bytes) else str(val)
        except ImportError:
            return "redis não instalado (pip install redis)"
        except Exception as e:
            return f"Erro Redis: {e}"

    def redis_set(self, key=None, value=None, conn_string="redis://localhost:6379/0", ttl=None):
        if key is None or value is None:
            return "key e value necessários"
        try:
            import redis as _redis
            r = _redis.from_url(conn_string)
            r.set(key, value, ex=ttl)
            r.close()
            return f"Redis: {key} = {str(value)[:50]}"
        except ImportError:
            return "redis não instalado (pip install redis)"
        except Exception as e:
            return f"Erro Redis: {e}"

    def redis_publish(self, channel=None, message=None, conn_string="redis://localhost:6379/0"):
        if not channel or message is None:
            return "channel e message necessários"
        try:
            import redis as _redis
            r = _redis.from_url(conn_string)
            count = r.publish(channel, message)
            r.close()
            return f"Mensagem publicada no canal '{channel}': {count} subscribers"
        except ImportError:
            return "redis não instalado (pip install redis)"
        except Exception as e:
            return f"Erro Redis publish: {e}"

    # === DATABASE: Backup ===
    def db_backup(self, db_type=None, conn_string=None, output=None):
        if not db_type or not conn_string:
            return "db_type (postgres|mysql|sqlite|mongodb) e conn_string necessários"
        output = output or os.path.expanduser(f"~/backup_{db_type}_{int(time.time())}")
        try:
            if db_type == "postgres":
                import re
                m = re.match(r"postgresql://(.+?):(.+?)@(.+?):(\d+)/(.+)", conn_string)
                if not m:
                    return "Formato: postgresql://user:pass@host:port/db"
                user, pw, host, port, db = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
                out = self._sh(f"PGPASSWORD='{pw}' pg_dump -U {user} -h {host} -p {port} -d {db} -F c -f {output}.dump 2>&1")
                if os.path.exists(f"{output}.dump"):
                    return f"Backup PostgreSQL salvo: {output}.dump"
                return out or "pg_dump falhou (instale postgresql-client)"
            elif db_type == "mysql":
                import re
                m = re.match(r"mysql(?:\+pymysql)?://(.+?):(.+?)@(.+?):(\d+)/(.+)", conn_string)
                if not m:
                    return "Formato: mysql://user:pass@host:port/db"
                user, pw, host, port, db = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
                out = self._sh(f"MYSQL_PWD='{pw}' mysqldump -u {user} -h {host} -P {port} {db} > {output}.sql 2>&1")
                if os.path.exists(f"{output}.sql"):
                    return f"Backup MySQL salvo: {output}.sql"
                return out or "mysqldump falhou (instale mysql-client)"
            elif db_type == "sqlite":
                db_path = conn_string.replace("sqlite:///", "")
                import shutil
                shutil.copy2(db_path, f"{output}.sqlite")
                return f"Backup SQLite salvo: {output}.sqlite"
            elif db_type == "mongodb":
                out = self._sh(f"mongodump --uri='{conn_string}' --out={output} 2>&1")
                if os.path.isdir(output):
                    return f"Backup MongoDB salvo em: {output}"
                return out or "mongodump falhou (instale mongodb-database-tools)"
            return f"Tipo '{db_type}' não suportado (postgres|mysql|sqlite|mongodb)"
        except Exception as e:
            return f"Erro backup: {e}"

    # === DATABASE: Migrations ===
    def db_migrate(self, db_type=None, conn_string=None, migrations_dir=None):
        if not db_type or not conn_string:
            return "db_type e conn_string necessários"
        migrations_dir = migrations_dir or os.path.expanduser("~/jarvis/migrations")
        if not os.path.isdir(migrations_dir):
            return f"Diretório de migrations não encontrado: {migrations_dir}"
        try:
            import sqlite3
            applied = set()
            meta_db = os.path.join(migrations_dir, "_migrations.db")
            conn = sqlite3.connect(meta_db)
            conn.execute("CREATE TABLE IF NOT EXISTS migrations (name TEXT PRIMARY KEY, applied_at TEXT)")
            applied = {r[0] for r in conn.execute("SELECT name FROM migrations").fetchall()}
            files = sorted(f for f in os.listdir(migrations_dir) if f.endswith(".sql") and f not in applied)
            if not files:
                conn.close()
                return "Nenhuma migration pendente."
            count = 0
            for fname in files:
                path = os.path.join(migrations_dir, fname)
                with open(path) as f:
                    sql = f.read()
                if db_type == "sqlite":
                    db_path = conn_string.replace("sqlite:///", "")
                    db_conn = sqlite3.connect(db_path)
                    db_conn.executescript(sql)
                    db_conn.commit()
                    db_conn.close()
                else:
                    conn.execute("INSERT OR IGNORE INTO migrations (name, applied_at) VALUES (?, ?)",
                                 (fname, __import__('datetime').datetime.now().isoformat()))
                    conn.commit()
                    return f"Migrations para {db_type} precisam de cliente nativo. Use pg_query/mysql_query para aplicar manualmente."
                conn.execute("INSERT INTO migrations (name, applied_at) VALUES (?, ?)",
                             (fname, __import__('datetime').datetime.now().isoformat()))
                conn.commit()
                count += 1
            conn.close()
            return f"{count} migrations aplicadas: {', '.join(files)}"
        except Exception as e:
            return f"Erro migrations: {e}"

    # === DEVOPS: Docker Compose ===
    def docker_compose_up(self, path=None, services=None):
        path = path or os.path.expanduser("~")
        cmd = f"docker-compose -f {path}/docker-compose.yml up -d"
        if services:
            cmd += f" {services}"
        return self._sh(cmd) or f"Compose up em {path}"

    def docker_compose_down(self, path=None):
        path = path or os.path.expanduser("~")
        return self._sh(f"docker-compose -f {path}/docker-compose.yml down") or "Compose down"

    def docker_compose_logs(self, path=None, tail=50):
        path = path or os.path.expanduser("~")
        return self._sh(f"docker-compose -f {path}/docker-compose.yml logs --tail={tail}") or "Sem logs"

    # === DEVOPS: Kubernetes ===
    def kubectl_exec(self, action=None, resource=None, namespace=None, args=None):
        if not action or not resource:
            return "action (get|describe|logs|apply|delete) e resource (pod|deployment|service|...) necessários"
        cmd = f"kubectl {action} {resource}"
        if namespace:
            cmd += f" -n {namespace}"
        if args:
            cmd += f" {args}"
        return self._sh(f"{cmd} 2>&1 | head -100") or f"kubectl {action} {resource} executado"

    # === DEVOPS: Terraform ===
    def terraform_plan(self, path=None):
        path = path or os.path.expanduser("~")
        return self._sh(f"cd {path} && terraform plan -no-color 2>&1 | tail -50") or "Terraform plan executado"

    def terraform_apply(self, path=None, auto_approve=False):
        path = path or os.path.expanduser("~")
        flag = " -auto-approve" if auto_approve else ""
        return self._sh(f"cd {path} && terraform apply{flag} -no-color 2>&1 | tail -50") or "Terraform apply executado"

    # === DEVOPS: Ansible ===
    def ansible_playbook(self, playbook=None, inventory=None, extra_vars=None):
        if not playbook:
            return "playbook (.yml) necessário"
        playbook = os.path.expanduser(playbook)
        cmd = f"ansible-playbook {playbook}"
        if inventory:
            cmd += f" -i {inventory}"
        if extra_vars:
            cmd += f" --extra-vars '{extra_vars}'"
        return self._sh(f"{cmd} 2>&1 | tail -50") or f"Playbook {playbook} executado"

    # === DEVOPS: AWS S3 ===
    def aws_s3_ls(self, path=None, recursive=False):
        if not path:
            return "path necessário (ex: s3://bucket/path)"
        cmd = f"aws s3 ls {path}"
        if recursive:
            cmd += " --recursive"
        return self._sh(f"{cmd} 2>&1 | head -100") or "aws-cli não configurado"

    def aws_s3_cp(self, source=None, dest=None, recursive=False):
        if not source or not dest:
            return "source e dest necessários"
        cmd = f"aws s3 cp {source} {dest}"
        if recursive:
            cmd += " --recursive"
        return self._sh(f"{cmd} 2>&1") or f"Copiado {source} → {dest}"

    # === DEV: GitHub PR ===
    def github_pr_create(self, title=None, body=None, base=None, head=None):
        if not title:
            return "title necessário"
        cmd = f"gh pr create --title '{title}'"
        if body:
            cmd += f" --body '{body}'"
        if base:
            cmd += f" --base {base}"
        if head:
            cmd += f" --head {head}"
        return self._sh(f"{cmd} 2>&1") or "gh CLI não configurado"

    def github_pr_list(self, repo=None, state="open"):
        cmd = "gh pr list" + (f" -R {repo}" if repo else "") + f" --state {state}"
        return self._sh(f"{cmd} 2>&1 | head -50") or "Nenhum PR encontrado"

    def github_issue_search(self, query=None, repo=None):
        if not query:
            return "query necessária"
        cmd = f"gh issue list --search '{query}'"
        if repo:
            cmd += f" -R {repo}"
        return self._sh(f"{cmd} 2>&1 | head -30") or "Nenhum issue encontrado"

    # === DEV: Code Quality ===
    def code_lint(self, path=None, tool="auto"):
        path = path or os.path.expanduser(".")
        if tool == "auto":
            if os.path.exists(os.path.join(path, "pyproject.toml")):
                return self._sh(f"cd {path} && ruff check . 2>&1 | head -50") or "Sem erros"
            return self._sh(f"cd {path} && python3 -m py_compile *.py 2>&1 | head -30") or "Sem erros"
        if tool == "ruff":
            return self._sh(f"cd {path} && ruff check . 2>&1 | head -50") or "Sem erros"
        if tool == "pylint":
            return self._sh(f"cd {path} && pylint *.py 2>&1 | tail -30") or "Sem erros"
        return f"Ferramenta '{tool}' não suportada (ruff, pylint, auto)"

    def code_format(self, path=None, tool="auto"):
        path = path or os.path.expanduser(".")
        if tool == "auto":
            if os.path.exists(os.path.join(path, "pyproject.toml")):
                return self._sh(f"cd {path} && ruff format . 2>&1") or "Código formatado"
            return self._sh(f"cd {path} && black --quiet . 2>&1") or "Código formatado"
        if tool == "ruff":
            return self._sh(f"cd {path} && ruff format . 2>&1") or "Código formatado"
        if tool == "black":
            return self._sh(f"cd {path} && black --quiet . 2>&1") or "Código formatado"
        return f"Ferramenta '{tool}' não suportada (ruff, black, auto)"

    # === DEV: Docs & API ===
    def docs_generate(self, path=None, output=None):
        path = path or os.path.expanduser(".")
        output = output or os.path.join(path, "docs")
        try:
            import pydoc
            os.makedirs(output, exist_ok=True)
            modules = [f.replace(".py", "") for f in os.listdir(path) if f.endswith(".py") and not f.startswith("_")]
            for m in modules[:20]:
                self._sh(f"python3 -c \"import pydoc; pydoc.writedoc('{m}')\" 2>&1")
            return f"Documentação gerada em {output}"
        except Exception as e:
            return f"Erro: {e}"

    def api_test(self, method="GET", url=None, headers=None, body=None, expected_status=None):
        if not url:
            return "URL necessária"
        try:
            import requests
            hdrs = json.loads(headers) if isinstance(headers, str) else (headers or {})
            start = time.time()
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
            elapsed = time.time() - start
            result = f"{method} {url} → {r.status_code} ({elapsed:.2f}s)\n"
            if expected_status:
                passed = r.status_code == int(expected_status)
                result += f"Status esperado: {expected_status} → {'✅ PASS' if passed else '❌ FAIL'}\n"
            result += r.text[:1000]
            return result
        except ImportError:
            return "requests não instalado"
        except Exception as e:
            return f"Erro: {e}"

    # === MULTIMÍDIA: Vídeo ===
    def video_download(self, url=None, output=None, format="mp4"):
        if not url:
            return "URL necessária (YouTube, Vimeo, etc)"
        output = output or os.path.expanduser(f"~/Videos/%(title)s.%(ext)s")
        return self._sh(f"yt-dlp -f 'bestvideo[ext={format}]+bestaudio[ext=m4a]/best[ext={format}]' -o '{output}' '{url}' 2>&1 | tail -10") or "Download iniciado"

    def video_convert(self, input_path=None, output_path=None, codec="h264"):
        if not input_path or not output_path:
            return "input_path e output_path necessários"
        input_path, output_path = os.path.expanduser(input_path), os.path.expanduser(output_path)
        codec_map = {"h264": "libx264", "h265": "libx265", "vp9": "libvpx-vp9", "av1": "libaom-av1"}
        c = codec_map.get(codec, codec)
        return self._sh(f"ffmpeg -i '{input_path}' -c:v {c} -preset medium '{output_path}' 2>&1 | tail -5") or f"Convertido: {output_path}"

    def video_edit_trim(self, input_path=None, output_path=None, start=None, duration=None):
        if not input_path or not output_path:
            return "input_path e output_path necessários"
        input_path, output_path = os.path.expanduser(input_path), os.path.expanduser(output_path)
        cmd = f"ffmpeg -i '{input_path}'"
        if start:
            cmd += f" -ss {start}"
        if duration:
            cmd += f" -t {duration}"
        cmd += f" -c copy '{output_path}' 2>&1 | tail -5"
        return self._sh(cmd) or f"Vídeo cortado: {output_path}"

    # === MULTIMÍDIA: Áudio ===
    def audio_separate(self, input_path=None, output_dir=None):
        if not input_path:
            return "input_path necessário"
        input_path = os.path.expanduser(input_path)
        output_dir = output_dir or os.path.expanduser(f"~/Audio/separated/{os.path.splitext(os.path.basename(input_path))[0]}")
        os.makedirs(output_dir, exist_ok=True)
        try:
            from demucs import separate
            return f"demucs separando em {output_dir}... (pip install demucs)"
        except ImportError:
            return self._sh(f"spleeter separate -p spleeter:2stems -o '{output_dir}' '{input_path}' 2>&1 | tail -5") or "spleeter não instalado (pip install spleeter)"

    def audio_to_text_batch(self, directory=None, recursive=True):
        directory = directory or os.path.expanduser("~")
        pattern = "**/*" if recursive else "*"
        results = []
        try:
            import glob as _glob
            for f in sorted(_glob.glob(os.path.join(directory, pattern))):
                ext = os.path.splitext(f)[1].lower()
                if ext in (".wav", ".mp3", ".m4a", ".ogg", ".flac"):
                    text = self.audio_transcribe(path=f)
                    results.append(f"{os.path.basename(f)}: {text[:100]}")
            return "\n".join(results[:20]) if results else "Nenhum áudio encontrado"
        except Exception as e:
            return f"Erro: {e}"

    # === MULTIMÍDIA: Imagem ===
    def image_generate(self, prompt=None, output=None, model=None):
        if not prompt:
            return "prompt necessário (descrição da imagem)"
        output = output or os.path.expanduser(f"~/Pictures/jarvis_img_{int(time.time())}.png")
        os.makedirs(os.path.dirname(output), exist_ok=True)
        if model:
            return self._sh(f"python3 -c \"from diffusers import DiffusionPipeline; import torch; pipe = DiffusionPipeline.from_pretrained('{model}', torch_dtype=torch.float16); pipe.to('cuda'); image = pipe('{prompt}').images[0]; image.save('{output}')\" 2>&1 | tail -5") or f"Imagem gerada: {output}"
        try:
            import requests
            r = requests.post("http://127.0.0.1:7860/sdapi/v1/txt2img",
                              json={"prompt": prompt, "steps": 20}, timeout=120)
            if r.ok:
                import base64
                data = r.json()
                with open(output, "wb") as f:
                    f.write(base64.b64decode(data["images"][0]))
                return f"Imagem gerada via API SD: {output}"
            return f"SD API error: {r.status_code}"
        except ImportError:
            return "requests não instalado"
        except requests.ConnectionError:
            return "Stable Diffusion WebUI não está rodando em http://127.0.0.1:7860. Inicie com: python3 launch.py --api"
        except Exception as e:
            return f"Erro: {e}"

    def gif_generate(self, input_dir=None, output=None, delay=100):
        if not input_dir:
            return "input_dir necessário (diretório com frames .png)"
        input_dir = os.path.expanduser(input_dir)
        output = output or os.path.expanduser(f"~/Pictures/jarvis_{int(time.time())}.gif")
        try:
            from PIL import Image
            frames = sorted([f for f in os.listdir(input_dir) if f.endswith(('.png', '.jpg', '.jpeg'))])
            if not frames:
                return "Nenhuma imagem encontrada no diretório"
            images = [Image.open(os.path.join(input_dir, f)) for f in frames]
            images[0].save(output, save_all=True, append_images=images[1:], duration=delay, loop=0)
            return f"GIF salvo: {output} ({len(frames)} frames)"
        except ImportError:
            return "Pillow não instalado"
        except Exception as e:
            return f"Erro: {e}"

    # === SEGURANÇA: Kali ===
    def exploit_search(self, query=None):
        if not query:
            return "query necessária (ex: 'apache 2.4.49')"
        return self._sh(f"searchsploit {query} 2>&1 | head -30") or "searchsploit não encontrado (apt install exploitdb)"

    def vuln_scan(self, target=None, profile="quick"):
        if not target:
            return "target necessário (IP ou hostname)"
        if profile == "quick":
            return self._sh(f"nmap -sV --script vuln --script-timeout=30s {target} 2>&1 | head -80") or "nmap não disponível"
        elif profile == "full":
            return self._sh(f"nmap -sS -sV -p- --script vuln -T4 {target} 2>&1 | head -100") or "nmap não disponível"
        return f"Profile '{profile}' não suportado (quick, full)"

    def network_capture(self, interface=None, filter_expr=None, count=10, output=None):
        interface = interface or "eth0"
        output = output or os.path.expanduser(f"~/capture_{int(time.time())}.pcap")
        cmd = f"tcpdump -i {interface} -c {count} -w {output}"
        if filter_expr:
            cmd += f" {filter_expr}"
        return self._sh(f"{cmd} 2>&1") or f"Captura salva: {output} ({count} pacotes)"

    def log_analyzer(self, log_path=None, patterns=None, hours=24):
        if not log_path:
            return "log_path necessário (ex: /var/log/auth.log)"
        log_path = os.path.expanduser(log_path)
        if not os.path.exists(log_path):
            return f"Arquivo não encontrado: {log_path}"
        cmd = f"grep -E '{patterns or 'Failed|Error|denied'}' {log_path}"
        if hours:
            cmd = f"grep -E '{patterns or 'Failed|Error|denied'}' {log_path} | tail -100"
        return self._sh(cmd) or "Nenhum padrão encontrado"

    def dns_recon(self, domain=None, record_type="ANY"):
        if not domain:
            return "domain necessário"
        return self._sh(f"dig {domain} {record_type} +short 2>&1 | head -30") or f"dns recon para {domain}"

    def hash_verify(self, path=None, expected_hash=None, algorithm="sha256"):
        if not path or not expected_hash:
            return "path e expected_hash necessários"
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return "Arquivo não encontrado"
        try:
            import hashlib
            h = hashlib.new(algorithm)
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            actual = h.hexdigest()
            match = actual == expected_hash.lower()
            return f"{'✅ MATCH' if match else '❌ MISMATCH'}\nEsperado: {expected_hash}\n  Atual: {actual}"
        except Exception as e:
            return f"Erro: {e}"

    # === SISTEMA: Usuários e Pacotes ===
    def user_manage(self, action=None, username=None, groups=None):
        if not action or not username:
            return "action (create|delete|lock|unlock|info) e username necessários"
        if action == "create":
            cmd = f"sudo useradd -m {username}"
            if groups:
                cmd += f" -G {groups}"
            return self._sh(f"{cmd} 2>&1") or f"Usuário {username} criado"
        elif action == "delete":
            return self._sh(f"sudo userdel -r {username} 2>&1") or f"Usuário {username} removido"
        elif action == "lock":
            return self._sh(f"sudo passwd -l {username} 2>&1") or f"Usuário {username} bloqueado"
        elif action == "unlock":
            return self._sh(f"sudo passwd -u {username} 2>&1") or f"Usuário {username} desbloqueado"
        elif action == "info":
            return self._sh(f"id {username} 2>&1 && groups {username} 2>&1") or f"Usuário {username} não encontrado"
        return "action inválida (create|delete|lock|unlock|info)"

    def package_manage(self, action=None, packages=None):
        if not action or not packages:
            return "action (install|remove|search|info|update) e packages necessários"
        if action == "install":
            return self._sh(f"sudo apt install -y {packages} 2>&1 | tail -10") or f"Pacotes instalados: {packages}"
        elif action == "remove":
            return self._sh(f"sudo apt remove -y {packages} 2>&1 | tail -10") or f"Pacotes removidos: {packages}"
        elif action == "search":
            return self._sh(f"apt-cache search {packages} 2>&1 | head -20") or f"Nada encontrado para {packages}"
        elif action == "info":
            return self._sh(f"apt-cache show {packages} 2>&1 | head -20") or f"Pacote {packages} não encontrado"
        elif action == "update":
            return self._sh("sudo apt update 2>&1 | tail -5") or "Update realizado"
        return "action inválida (install|remove|search|info|update)"

    # === SISTEMA: Cron ===
    def cron_edit(self, action=None, schedule=None, command=None, comment=None):
        if action == "list":
            return self._sh("crontab -l 2>&1") or "Nenhum cron configurado"
        if action == "add":
            if not schedule or not command:
                return "schedule (ex: '0 * * * *') e command necessários"
            entry = f"{schedule} {command}"
            if comment:
                entry = f"# {comment}\n{entry}"
            result = self._sh(f'(crontab -l 2>/dev/null; echo "{entry}") | crontab - 2>&1')
            return result or f"Cron adicionado: {entry}"
        if action == "clear":
            return self._sh("crontab -r 2>&1") or "Cron removido"
        return "action inválida (list|add|clear)"

    # === SISTEMA: Serviços ===
    def service_manage(self, action=None, service=None):
        if not action or not service:
            return "action (start|stop|restart|enable|disable|status) e service necessários"
        return self._sh(f"sudo systemctl {action} {service} 2>&1") or f"Service {service}: {action}"

    # === SISTEMA: Disco ===
    def disk_analyzer(self, path=None, depth=2, min_size_mb=10):
        path = path or "/"
        return self._sh(f"du -h --max-depth={depth} {path} 2>/dev/null | sort -rh | head -30 | awk '$1 ~ /M|G/ && $1+0 > {min_size_mb}'") or "Análise de disco concluída"

    # === SISTEMA: File Watch ===
    def file_watch(self, path=None, event="modified", timeout=30):
        if not path:
            return "path necessário"
        path = os.path.expanduser(path)
        import threading as _t, time as _time
        events = []
        def _watch():
            try:
                from watchdog.observers import Observer
                from watchdog.events import FileSystemEventHandler
                class H(FileSystemEventHandler):
                    def on_modified(self, e): events.append(f"modified: {e.src_path}")
                    def on_created(self, e): events.append(f"created: {e.src_path}")
                    def on_deleted(self, e): events.append(f"deleted: {e.src_path}")
                obs = Observer()
                obs.schedule(H(), path, recursive=True)
                obs.start()
                _time.sleep(timeout)
                obs.stop()
                obs.join()
            except ImportError:
                events.append("watchdog não instalado (pip install watchdog)")
        _t.Thread(target=_watch, daemon=True).start()
        _time.sleep(timeout + 0.5)
        return "\n".join(events[-20:]) if events else f"Nenhum evento em {timeout}s"

    # === PRODUTIVIDADE: Pomodoro ===
    def pomodoro_start(self, work_minutes=25, break_minutes=5):
        import threading as _t, time as _time
        def _run():
            self.send_notification("Pomodoro", f"Foco por {work_minutes}min")
            _time.sleep(work_minutes * 60)
            self.send_notification("Pomodoro", "Hora da pausa!")
            _time.sleep(break_minutes * 60)
            self.send_notification("Pomodoro", "Pomodoro completo! ✅")
        _t.Thread(target=_run, daemon=True).start()
        return f"Pomodoro iniciado: {work_minutes}min foco + {break_minutes}min pausa"

    def habit_track(self, action=None, habit=None):
        db = os.path.expanduser("~/.jarvis/habits.db")
        try:
            import sqlite3
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE IF NOT EXISTS habits (name TEXT, date TEXT, UNIQUE(name, date))")
            conn.commit()
            if action == "checkin":
                from datetime import date
                conn.execute("INSERT OR IGNORE INTO habits (name, date) VALUES (?, ?)", (habit, str(date.today())))
                conn.commit()
                conn.close()
                return f"Hábito '{habit}' registrado hoje ✅"
            elif action == "report":
                rows = conn.execute("SELECT name, COUNT(*) as streak FROM habits GROUP BY name ORDER BY streak DESC").fetchall()
                conn.close()
                if not rows:
                    return "Nenhum hábito registrado ainda"
                return "\n".join(f"  {r[0]}: {r[1]} dias" for r in rows)
            elif action == "list":
                rows = conn.execute("SELECT DISTINCT name FROM habits ORDER BY name").fetchall()
                conn.close()
                return "\n".join(f"  • {r[0]}" for r in rows) if rows else "Nenhum hábito"
            conn.close()
            return "action: checkin|list|report"
        except Exception as e:
            return f"Erro: {e}"

    # === CONHECIMENTO: Pesquisa ===
    def web_scrape(self, url=None, selector=None, format="text"):
        if not url:
            return "URL necessária"
        try:
            import requests
            from bs4 import BeautifulSoup
            r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, "html.parser")
            if selector:
                elements = soup.select(selector)
                if format == "text":
                    return "\n".join(e.get_text(strip=True) for e in elements[:20]) or "Seletor não encontrou elementos"
                elif format == "html":
                    return "\n".join(str(e) for e in elements[:10])[:3000]
                elif format == "links":
                    return "\n".join(f"{e.get('href', '')}" for e in elements[:30] if e.name == 'a')
            return soup.get_text(separator="\n", strip=True)[:3000]
        except ImportError:
            return "requests/beautifulsoup4 não instalados"
        except Exception as e:
            return f"Erro: {e}"

    def wikipedia_search(self, query=None, lang="pt", sentences=3):
        if not query:
            return "query necessária"
        try:
            import wikipedia
            wikipedia.set_lang(lang)
            summary = wikipedia.summary(query, sentences=sentences)
            page = wikipedia.page(query)
            return f"{page.title}\n\n{summary}\n\nFonte: {page.url}"
        except ImportError:
            return "wikipedia não instalado (pip install wikipedia)"
        except wikipedia.exceptions.DisambiguationError as e:
            return f"Ambíguo: {', '.join(e.options[:10])}"
        except wikipedia.exceptions.PageError:
            return f"Página '{query}' não encontrada"
        except Exception as e:
            return f"Erro: {e}"

    def dictionary_lookup(self, word=None, lang="pt"):
        if not word:
            return "word necessária"
        if lang == "pt":
            try:
                import requests
                r = requests.get(f"https://api.dicionario-aberto.net/word/{word}", timeout=10)
                if r.ok and r.json():
                    entries = r.json()[:3]
                    return "\n".join(f"• {e.get('xml', e.get('text', ''))[:200]}" for e in entries)
                return f"Palavra '{word}' não encontrada"
            except Exception as e:
                return f"Erro: {e}"
        else:
            try:
                import requests
                r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=10)
                if r.ok:
                    data = r.json()[0]
                    meanings = data.get("meanings", [])
                    lines = [f"{data['word']} ({data.get('phonetic', '')})"]
                    for m in meanings[:3]:
                        for d in m.get("definitions", [])[:2]:
                            lines.append(f"  [{m['partOfSpeech']}] {d['definition']}")
                    return "\n".join(lines)
                return f"Palavra '{word}' não encontrada"
            except Exception as e:
                return f"Erro: {e}"

    # === CONHECIMENTO: Documentos ===
    def pdf_merge(self, files=None, output=None):
        if not files or not output:
            return "files (separados por vírgula) e output necessários"
        files = [os.path.expanduser(f.strip()) for f in files.split(",")]
        output = os.path.expanduser(output)
        try:
            from PyPDF2 import PdfMerger
            merger = PdfMerger()
            for f in files:
                merger.append(f)
            merger.write(output)
            merger.close()
            return f"PDFs mesclados: {output} ({len(files)} arquivos)"
        except ImportError:
            return "PyPDF2 não instalado"
        except Exception as e:
            return f"Erro: {e}"

    def pdf_split(self, input_path=None, output_dir=None, pages_per_file=1):
        if not input_path:
            return "input_path necessário"
        input_path = os.path.expanduser(input_path)
        output_dir = output_dir or os.path.expanduser(f"~/Documents/{os.path.splitext(os.path.basename(input_path))[0]}_split")
        os.makedirs(output_dir, exist_ok=True)
        try:
            from PyPDF2 import PdfReader, PdfWriter
            reader = PdfReader(input_path)
            total = len(reader.pages)
            count = 0
            for i in range(0, total, pages_per_file):
                writer = PdfWriter()
                for j in range(i, min(i + pages_per_file, total)):
                    writer.add_page(reader.pages[j])
                out_path = os.path.join(output_dir, f"page_{i+1:03d}.pdf")
                with open(out_path, "wb") as f:
                    writer.write(f)
                count += 1
            return f"PDF dividido: {count} arquivos em {output_dir}"
        except ImportError:
            return "PyPDF2 não instalado"
        except Exception as e:
            return f"Erro: {e}"

    def document_compare(self, file_a=None, file_b=None, output=None):
        if not file_a or not file_b:
            return "file_a e file_b necessários"
        file_a, file_b = os.path.expanduser(file_a), os.path.expanduser(file_b)
        output = output or os.path.expanduser(f"~/diff_{int(time.time())}.html")
        try:
            import difflib
            with open(file_a) as f: a_lines = f.readlines()
            with open(file_b) as f: b_lines = f.readlines()
            diff = difflib.HtmlDiff().make_file(a_lines, b_lines, os.path.basename(file_a), os.path.basename(file_b))
            with open(output, "w") as f:
                f.write(diff)
            return f"Diff salvo: {output}"
        except Exception as e:
            return f"Erro: {e}"

    # === IoT: MQTT ===
    def mqtt_publish(self, broker=None, topic=None, message=None, port=1883):
        if not broker or not topic or message is None:
            return "broker, topic e message necessários"
        try:
            import paho.mqtt.client as mqtt
            client = mqtt.Client()
            client.connect(broker, int(port), 60)
            client.publish(topic, message)
            client.disconnect()
            return f"MQTT publicado em {broker}:{port}/{topic}"
        except ImportError:
            return "paho-mqtt não instalado (pip install paho-mqtt)"
        except Exception as e:
            return f"Erro MQTT: {e}"

    def mqtt_subscribe(self, broker=None, topic=None, port=1883, timeout=10):
        if not broker or not topic:
            return "broker e topic necessários"
        messages = []
        try:
            import paho.mqtt.client as mqtt
            import threading as _t, time as _time
            def on_msg(client, userdata, msg):
                messages.append(f"{msg.topic}: {msg.payload.decode()}")
            client = mqtt.Client()
            client.on_message = on_msg
            client.connect(broker, int(port), 60)
            client.subscribe(topic)
            client.loop_start()
            _time.sleep(timeout)
            client.loop_stop()
            client.disconnect()
            return "\n".join(messages[-20:]) if messages else f"Nenhuma mensagem em {timeout}s em '{topic}'"
        except ImportError:
            return "paho-mqtt não instalado (pip install paho-mqtt)"
        except Exception as e:
            return f"Erro MQTT: {e}"

    # === COMUNICAÇÃO: Email (completo) ===
    def email_fetch(self, server=None, user=None, password=None, limit=10, mailbox="INBOX"):
        if not server or not user or not password:
            return "server, user e password necessários (IMAP)"
        try:
            import imaplib
            import email
            mail = imaplib.IMAP4_SSL(server)
            mail.login(user, password)
            mail.select(mailbox)
            _, data = mail.search(None, "ALL")
            ids = data[0].split()[-limit:]
            messages = []
            for i in reversed(ids):
                _, msg_data = mail.fetch(i, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])
                subject = msg["subject"] or "(sem assunto)"
                fr = msg["from"] or "(desconhecido)"
                messages.append(f"  {fr}: {subject[:80]}")
            mail.logout()
            return "\n".join(messages) if messages else "Nenhum email encontrado"
        except ImportError:
            return "imaplib (stdlib) não disponível"
        except Exception as e:
            return f"Erro: {e}"

    # === FINANÇAS ===
    def budget_track(self, action=None, category=None, amount=None, description=None):
        db = os.path.expanduser("~/.jarvis/budget.db")
        try:
            import sqlite3
            from datetime import datetime
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY, date TEXT, category TEXT, amount REAL, description TEXT)")
            conn.commit()
            if action == "add":
                if not category or amount is None:
                    return "category e amount necessários"
                conn.execute("INSERT INTO transactions (date, category, amount, description) VALUES (?, ?, ?, ?)",
                             (str(datetime.now().date()), category, float(amount), description or ""))
                conn.commit()
                conn.close()
                return f"Gasto registrado: {category} R${float(amount):.2f}"
            elif action == "report":
                rows = conn.execute("SELECT category, SUM(amount) FROM transactions GROUP BY category ORDER BY SUM(amount) DESC").fetchall()
                total = conn.execute("SELECT SUM(amount) FROM transactions").fetchone()[0] or 0
                conn.close()
                if not rows:
                    return "Nenhum gasto registrado"
                lines = [f"  {r[0]}: R${r[1]:.2f}" for r in rows]
                lines.append(f"  TOTAL: R${total:.2f}")
                return "\n".join(lines)
            elif action == "list":
                rows = conn.execute("SELECT date, category, amount, description FROM transactions ORDER BY id DESC LIMIT 20").fetchall()
                conn.close()
                return "\n".join(f"  {r[0]} | {r[1]} | R${r[2]:.2f} | {r[3] or ''}" for r in rows) if rows else "Nenhuma transação"
            conn.close()
            return "action: add|list|report"
        except Exception as e:
            return f"Erro: {e}"

    def currency_alert(self, from_currency="USD", to_currency="BRL", target_rate=None):
        if not target_rate:
            return "target_rate necessário (ex: 5.50)"
        import threading as _t, time as _time
        def _monitor():
            for i in range(60):
                rate = None
                try:
                    import requests
                    r = requests.get(f"https://api.frankfurter.app/latest?from={from_currency}&to={to_currency}", timeout=10)
                    if r.ok:
                        rate = r.json()["rates"][to_currency]
                except Exception:
                    pass
                if rate and ((rate >= float(target_rate)) if ">" in str(target_rate) else abs(rate - float(target_rate)) / float(target_rate) < 0.01):
                    self.send_notification("Câmbio", f"{from_currency}→{to_currency}: {rate:.4f} (alvo: {target_rate})")
                    return
                _time.sleep(60)
            return "Alerta de câmbio finalizado (timeout 60min)"
        _t.Thread(target=_monitor, daemon=True).start()
        return f"Monitorando {from_currency}→{to_currency} (alvo: {target_rate}) por 60min"

    # === ML/AI: LLM Tools ===
    def llm_benchmark(self, models=None, prompt="Explique o que é Python em 1 parágrafo"):
        models = [m.strip() for m in (models or "qwen2.5:3b,llama3.2:3b").split(",")]
        try:
            import ollama
            results = []
            for model in models:
                try:
                    start = time.time()
                    r = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}],
                                    options={"num_predict": 100})
                    elapsed = time.time() - start
                    content = r.get("message", {}).get("content", "")
                    results.append(f"  {model}: {elapsed:.1f}s | {len(content)} chars | {content[:100]}...")
                except Exception as e:
                    results.append(f"  {model}: ERRO - {e}")
            return "\n".join(results)
        except ImportError:
            return "ollama não instalado"
        except Exception as e:
            return f"Erro: {e}"


EXTRA_TOOLS = [
    # ── DEVOPS & CLOUD ──────────────────────────────────
    ("docker_compose_up", ExtraTools.docker_compose_up,
     "Iniciar serviços com docker-compose em background",
     {"path": {"type": "string"}, "services": {"type": "string"}}),
    ("docker_compose_down", ExtraTools.docker_compose_down,
     "Parar serviços docker-compose",
     {"path": {"type": "string"}}),
    ("docker_compose_logs", ExtraTools.docker_compose_logs,
     "Ver logs do docker-compose",
     {"path": {"type": "string"}, "tail": {"type": "integer"}}),
    ("kubectl_exec", ExtraTools.kubectl_exec,
     "Executar comando kubectl (get/describe/logs/apply/delete)",
     {"action": {"type": "string"}, "resource": {"type": "string"}, "namespace": {"type": "string"}, "args": {"type": "string"}}),
    ("terraform_plan", ExtraTools.terraform_plan,
     "Mostrar plano Terraform",
     {"path": {"type": "string"}}),
    ("terraform_apply", ExtraTools.terraform_apply,
     "Aplicar Terraform (auto-approve opcional)",
     {"path": {"type": "string"}, "auto_approve": {"type": "boolean"}}),
    ("ansible_playbook", ExtraTools.ansible_playbook,
     "Executar playbook Ansible",
     {"playbook": {"type": "string"}, "inventory": {"type": "string"}, "extra_vars": {"type": "string"}}),
    ("aws_s3_ls", ExtraTools.aws_s3_ls,
     "Listar arquivos no S3",
     {"path": {"type": "string"}, "recursive": {"type": "boolean"}}),
    ("aws_s3_cp", ExtraTools.aws_s3_cp,
     "Copiar arquivos para/de S3",
     {"source": {"type": "string"}, "dest": {"type": "string"}, "recursive": {"type": "boolean"}}),

    # ── DEV: GITHUB ──────────────────────────────────────
    ("github_pr_create", ExtraTools.github_pr_create,
     "Criar Pull Request no GitHub via gh CLI",
     {"title": {"type": "string"}, "body": {"type": "string"}, "base": {"type": "string"}, "head": {"type": "string"}}),
    ("github_pr_list", ExtraTools.github_pr_list,
     "Listar Pull Requests abertos",
     {"repo": {"type": "string"}, "state": {"type": "string"}}),
    ("github_issue_search", ExtraTools.github_issue_search,
     "Buscar issues no GitHub",
     {"query": {"type": "string"}, "repo": {"type": "string"}}),

    # ── DEV: CODE QUALITY ────────────────────────────────
    ("code_lint", ExtraTools.code_lint,
     "Analisar código com linter (ruff/pylint)",
     {"path": {"type": "string"}, "tool": {"type": "string"}}),
    ("code_format", ExtraTools.code_format,
     "Formatar código automaticamente (ruff/black)",
     {"path": {"type": "string"}, "tool": {"type": "string"}}),
    ("docs_generate", ExtraTools.docs_generate,
     "Gerar documentação de código automaticamente",
     {"path": {"type": "string"}, "output": {"type": "string"}}),
    ("api_test", ExtraTools.api_test,
     "Testar endpoint HTTP (GET/POST/PUT/DELETE) com validação",
     {"method": {"type": "string"}, "url": {"type": "string"}, "headers": {"type": "string"}, "body": {"type": "string"}, "expected_status": {"type": "integer"}}),

    # ── MULTIMÍDIA ────────────────────────────────────────
    ("video_download", ExtraTools.video_download,
     "Baixar vídeo de URL (YouTube, etc) via yt-dlp",
     {"url": {"type": "string"}, "output": {"type": "string"}, "format": {"type": "string"}}),
    ("video_convert", ExtraTools.video_convert,
     "Converter vídeo entre formatos/codecs via ffmpeg",
     {"input_path": {"type": "string"}, "output_path": {"type": "string"}, "codec": {"type": "string"}}),
    ("video_edit_trim", ExtraTools.video_edit_trim,
     "Cortar vídeo (start + duration) via ffmpeg",
     {"input_path": {"type": "string"}, "output_path": {"type": "string"}, "start": {"type": "string"}, "duration": {"type": "string"}}),
    ("audio_separate", ExtraTools.audio_separate,
     "Separar áudio em vozes/instrumentos (spleeter/demucs)",
     {"input_path": {"type": "string"}, "output_dir": {"type": "string"}}),
    ("audio_to_text_batch", ExtraTools.audio_to_text_batch,
     "Transcrever lote de áudios para texto",
     {"directory": {"type": "string"}, "recursive": {"type": "boolean"}}),
    ("image_generate", ExtraTools.image_generate,
     "Gerar imagem por IA (Stable Diffusion API local ou diffusers)",
     {"prompt": {"type": "string"}, "output": {"type": "string"}, "model": {"type": "string"}}),
    ("gif_generate", ExtraTools.gif_generate,
     "Criar GIF animado a partir de frames",
     {"input_dir": {"type": "string"}, "output": {"type": "string"}, "delay": {"type": "integer"}}),

    # ── SEGURANÇA (KALI) ─────────────────────────────────
    ("exploit_search", ExtraTools.exploit_search,
     "Buscar exploits no Searchsploit/ExploitDB",
     {"query": {"type": "string"}}),
    ("vuln_scan", ExtraTools.vuln_scan,
     "Escaneamento de vulnerabilidades via nmap NSE",
     {"target": {"type": "string"}, "profile": {"type": "string"}}),
    ("network_capture", ExtraTools.network_capture,
     "Capturar pacotes de rede com tcpdump",
     {"interface": {"type": "string"}, "filter_expr": {"type": "string"}, "count": {"type": "integer"}, "output": {"type": "string"}}),
    ("log_analyzer", ExtraTools.log_analyzer,
     "Analisar logs do sistema por padrões (Failed/Error)",
     {"log_path": {"type": "string"}, "patterns": {"type": "string"}, "hours": {"type": "integer"}}),
    ("dns_recon", ExtraTools.dns_recon,
     "Consultar registros DNS de um domínio (dig)",
     {"domain": {"type": "string"}, "record_type": {"type": "string"}}),
    ("hash_verify", ExtraTools.hash_verify,
     "Verificar hash de arquivo (sha256/md5/etc)",
     {"path": {"type": "string"}, "expected_hash": {"type": "string"}, "algorithm": {"type": "string"}}),

    # ── SISTEMA ───────────────────────────────────────────
    ("user_manage", ExtraTools.user_manage,
     "Gerenciar usuários do sistema (create/delete/lock/unlock/info)",
     {"action": {"type": "string"}, "username": {"type": "string"}, "groups": {"type": "string"}}),
    ("package_manage", ExtraTools.package_manage,
     "Gerenciar pacotes apt (install/remove/search/info/update)",
     {"action": {"type": "string"}, "packages": {"type": "string"}}),
    ("service_manage", ExtraTools.service_manage,
     "Gerenciar serviços systemd (start/stop/restart/enable/disable/status)",
     {"action": {"type": "string"}, "service": {"type": "string"}}),
    ("cron_edit", ExtraTools.cron_edit,
     "Editar crontab (list/add/clear)",
     {"action": {"type": "string"}, "schedule": {"type": "string"}, "command": {"type": "string"}, "comment": {"type": "string"}}),
    ("disk_analyzer", ExtraTools.disk_analyzer,
     "Analisar uso de disco (diretórios maiores)",
     {"path": {"type": "string"}, "depth": {"type": "integer"}, "min_size_mb": {"type": "integer"}}),
    ("file_watch", ExtraTools.file_watch,
     "Observar mudanças em arquivos/diretórios",
     {"path": {"type": "string"}, "event": {"type": "string"}, "timeout": {"type": "integer"}}),

    # ── PRODUTIVIDADE ─────────────────────────────────────
    ("pomodoro_start", ExtraTools.pomodoro_start,
     "Iniciar timer Pomodoro (foco + pausa)",
     {"work_minutes": {"type": "integer"}, "break_minutes": {"type": "integer"}}),
    ("habit_track", ExtraTools.habit_track,
     "Rastrear hábitos diários (checkin/list/report)",
     {"action": {"type": "string"}, "habit": {"type": "string"}}),

    # ── CONHECIMENTO & PESQUISA ──────────────────────────
    ("web_scrape", ExtraTools.web_scrape,
     "Extrair conteúdo estruturado de site (com seletor CSS)",
     {"url": {"type": "string"}, "selector": {"type": "string"}, "format": {"type": "string"}}),
    ("wikipedia_search", ExtraTools.wikipedia_search,
     "Buscar resumo na Wikipedia",
     {"query": {"type": "string"}, "lang": {"type": "string"}, "sentences": {"type": "integer"}}),
    ("dictionary_lookup", ExtraTools.dictionary_lookup,
     "Consultar dicionário/significado de palavra",
     {"word": {"type": "string"}, "lang": {"type": "string"}}),
    ("pdf_merge", ExtraTools.pdf_merge,
     "Mesclar múltiplos PDFs em um só",
     {"files": {"type": "string"}, "output": {"type": "string"}}),
    ("pdf_split", ExtraTools.pdf_split,
     "Dividir PDF em páginas separadas",
     {"input_path": {"type": "string"}, "output_dir": {"type": "string"}, "pages_per_file": {"type": "integer"}}),
    ("document_compare", ExtraTools.document_compare,
     "Comparar dois arquivos e gerar diff HTML",
     {"file_a": {"type": "string"}, "file_b": {"type": "string"}, "output": {"type": "string"}}),

    # ── IoT ───────────────────────────────────────────────
    ("mqtt_publish", ExtraTools.mqtt_publish,
     "Publicar mensagem em broker MQTT",
     {"broker": {"type": "string"}, "topic": {"type": "string"}, "message": {"type": "string"}, "port": {"type": "integer"}}),
    ("mqtt_subscribe", ExtraTools.mqtt_subscribe,
     "Assinar tópico MQTT e aguardar mensagens",
     {"broker": {"type": "string"}, "topic": {"type": "string"}, "port": {"type": "integer"}, "timeout": {"type": "integer"}}),

    # ── COMUNICAÇÃO ───────────────────────────────────────
    ("email_fetch", ExtraTools.email_fetch,
     "Ler emails da caixa de entrada via IMAP",
     {"server": {"type": "string"}, "user": {"type": "string"}, "password": {"type": "string"}, "limit": {"type": "integer"}, "mailbox": {"type": "string"}}),

    # ── FINANÇAS ──────────────────────────────────────────
    ("budget_track", ExtraTools.budget_track,
     "Controlar gastos pessoais (add/list/report)",
     {"action": {"type": "string"}, "category": {"type": "string"}, "amount": {"type": "number"}, "description": {"type": "string"}}),
    ("currency_alert", ExtraTools.currency_alert,
     "Monitorar taxa de câmbio e alertar quando atingir alvo",
     {"from_currency": {"type": "string"}, "to_currency": {"type": "string"}, "target_rate": {"type": "number"}}),

    # ── ML/AI ─────────────────────────────────────────────
    ("llm_benchmark", ExtraTools.llm_benchmark,
     "Comparar performance entre modelos Ollama",
     {"models": {"type": "string"}, "prompt": {"type": "string"}}),

    # ── DATABASE ─────────────────────────────────────────
    ("pg_query", ExtraTools.pg_query,
     "Executar query SQL em PostgreSQL",
     {"conn_string": {"type": "string"}, "query": {"type": "string"}}),
    ("mysql_query", ExtraTools.mysql_query,
     "Executar query SQL em MySQL/MariaDB",
     {"conn_string": {"type": "string"}, "query": {"type": "string"}}),
    ("mongo_find", ExtraTools.mongo_find,
     "Buscar documentos no MongoDB por filtro",
     {"conn_string": {"type": "string"}, "collection": {"type": "string"}, "filter_query": {"type": "string"}, "limit": {"type": "integer"}}),
    ("mongo_insert", ExtraTools.mongo_insert,
     "Inserir documento no MongoDB",
     {"conn_string": {"type": "string"}, "collection": {"type": "string"}, "document": {"type": "string"}}),
    ("redis_get", ExtraTools.redis_get,
     "Obter valor de chave no Redis",
     {"key": {"type": "string"}, "conn_string": {"type": "string"}}),
    ("redis_set", ExtraTools.redis_set,
     "Definir valor de chave no Redis",
     {"key": {"type": "string"}, "value": {"type": "string"}, "conn_string": {"type": "string"}, "ttl": {"type": "integer"}}),
    ("redis_publish", ExtraTools.redis_publish,
     "Publicar mensagem em canal Redis",
     {"channel": {"type": "string"}, "message": {"type": "string"}, "conn_string": {"type": "string"}}),
    ("db_backup", ExtraTools.db_backup,
     "Fazer backup de banco de dados (postgres|mysql|sqlite|mongodb)",
     {"db_type": {"type": "string"}, "conn_string": {"type": "string"}, "output": {"type": "string"}}),
    ("db_migrate", ExtraTools.db_migrate,
     "Aplicar migrations SQL em lote",
     {"db_type": {"type": "string"}, "conn_string": {"type": "string"}, "migrations_dir": {"type": "string"}}),

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
    ("clipboard_set", ExtraTools.clipboard_set,
     "Copiar texto para área de transferência",
     {"text": {"type": "string"}}),
    ("download_file", ExtraTools.download_file,
     "Baixar arquivo da internet",
     {"url": {"type": "string"}, "dest": {"type": "string"}}),
    ("network_info", ExtraTools.network_info,
     "Informações de rede (interfaces, IPs)", {}),
    ("camera_capture", ExtraTools.camera_capture,
     "Capturar foto da webcam",
     {"output": {"type": "string"}}),
    ("git_status", ExtraTools.git_status,
     "Status do repositório git",
     {"path": {"type": "string"}}),
    ("send_notification", ExtraTools.send_notification,
     "Enviar notificação desktop",
     {"title": {"type": "string"}, "message": {"type": "string"}}),
    ("telegram_send", ExtraTools.telegram_send,
     "Enviar mensagem Telegram via bot (token/chat_id da config ou parâmetros)",
     {"text": {"type": "string"}, "token": {"type": "string"}, "chat_id": {"type": "string"}}),
    ("sql_query", ExtraTools.sql_query,
     "Executar query SQL em arquivo SQLite",
     {"db_path": {"type": "string"}, "query": {"type": "string"}}),
    ("power_control", ExtraTools.power_control,
     "Desligar/reiniciar/suspender sistema",
     {"action": {"type": "string"}}),
    ("process_kill", ExtraTools.process_kill,
     "Finalizar processo por PID ou nome",
     {"pid": {"type": "integer"}, "name": {"type": "string"}}),
    ("docker_exec", ExtraTools.docker_exec,
     "Executar comando em container Docker",
     {"container": {"type": "string"}, "command": {"type": "string"}}),
    ("git_commit", ExtraTools.git_commit,
     "Git add + commit",
     {"path": {"type": "string"}, "message": {"type": "string"}}),
    ("http_server", ExtraTools.http_server,
     "Iniciar servidor HTTP local para compartilhar arquivos",
     {"port": {"type": "integer"}, "directory": {"type": "string"}}),
    ("http_server_stop", ExtraTools.http_server_stop,
     "Parar servidor HTTP", {}),
    ("send_email", ExtraTools.send_email,
     "Enviar email via SMTP",
     {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}),
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

    # ── NOVAS FERRAMENTAS ────────────────────────────────
    ("volume_control", ExtraTools.volume_control,
     "Controlar volume do sistema (get/set/up/down/mute/unmute)",
     {"action": {"type": "string"}, "value": {"type": "integer"}}),
    ("brightness_control", ExtraTools.brightness_control,
     "Controlar brilho da tela (get/set/up/down)",
     {"action": {"type": "string"}, "value": {"type": "integer"}}),
    ("media_control", ExtraTools.media_control,
     "Controlar reprodução de mídia (play_pause/next/previous/stop/get)",
     {"action": {"type": "string"}}),
    ("calendar_query", ExtraTools.calendar_query,
     "Mostrar calendário de um mês/ano",
     {"month": {"type": "integer"}, "year": {"type": "integer"}}),
    ("weather", ExtraTools.weather,
     "Obter clima/temperatura de uma localidade",
     {"location": {"type": "string"}}),
    ("calculator", ExtraTools.calculator,
     "Calcular expressão matemática (ex: '2 + 2 * 5')",
     {"expression": {"type": "string"}}),
    ("notes_save", ExtraTools.notes_save,
     "Salvar uma nota de texto com título",
     {"title": {"type": "string"}, "content": {"type": "string"}}),
    ("notes_read", ExtraTools.notes_read,
     "Ler uma nota salva pelo título",
     {"title": {"type": "string"}}),
    ("notes_list", ExtraTools.notes_list,
     "Listar todas as notas salvas", {}),
    ("translate", ExtraTools.translate,
     "Traduzir texto para outro idioma (padrão: pt)",
     {"text": {"type": "string"}, "target_lang": {"type": "string"}, "source_lang": {"type": "string"}}),
    ("qrcode_generate", ExtraTools.qrcode_generate,
     "Gerar imagem QR Code a partir de texto ou URL",
     {"data": {"type": "string"}, "output": {"type": "string"}}),
    ("timer", ExtraTools.timer,
     "Iniciar timer/contagem regressiva (duração em segundos)",
     {"duration": {"type": "integer"}, "message": {"type": "string"}}),
    ("screenshot_region", ExtraTools.screenshot_region,
     "Capturar screenshot de uma região específica da tela",
     {"x": {"type": "integer"}, "y": {"type": "integer"}, "width": {"type": "integer"}, "height": {"type": "integer"}, "output": {"type": "string"}}),
    ("window_list", ExtraTools.window_list,
     "Listar janelas abertas no sistema", {}),
    ("window_focus", ExtraTools.window_focus,
     "Focar/trazer janela para frente por nome/título",
     {"title": {"type": "string"}}),
    ("clipboard_history", ExtraTools.clipboard_history,
     "Mostrar histórico da área de transferência",
     {"limit": {"type": "integer"}}),
    ("ssh_exec", ExtraTools.ssh_exec,
     "Executar comando em servidor remoto via SSH",
     {"host": {"type": "string"}, "command": {"type": "string"}, "user": {"type": "string"}, "password": {"type": "string"}, "port": {"type": "integer"}}),
    ("compress_file", ExtraTools.compress_file,
     "Compactar arquivo/diretório em zip ou tar.gz",
     {"source": {"type": "string"}, "output": {"type": "string"}, "format": {"type": "string"}}),
    ("location_info", ExtraTools.location_info,
     "Obter localização geográfica por IP (cidade, país, ISP)",
     {"ip": {"type": "string"}}),
    ("currency_convert", ExtraTools.currency_convert,
     "Converter valor entre moedas (ex: USD para BRL)",
     {"amount": {"type": "number"}, "from_currency": {"type": "string"}, "to_currency": {"type": "string"}}),
    ("text_to_speech", ExtraTools.text_to_speech,
     "Falar texto em voz alta (TTS)",
     {"text": {"type": "string"}, "lang": {"type": "string"}}),
    ("audio_transcribe", ExtraTools.audio_transcribe,
     "Transcrever arquivo de áudio para texto usando whisper",
     {"path": {"type": "string"}}),
]
