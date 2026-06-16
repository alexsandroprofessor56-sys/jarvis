"""Todas as features do Jarvis em um módulo"""
import os
import re
import time
import json
import glob
import shutil
import hashlib
import sqlite3
import threading
import subprocess
from datetime import datetime


class JarvisFeatures:
    def __init__(self):
        self._clipboard_history = []
        self._clipboard_thread = None
        self._clipboard_running = False
        self._network_monitor_thread = None
        self._network_monitor_running = False
        self._ambient_process = None
        self._session_recording = False
        self._session_events = []
        self._notes_db = os.path.expanduser("~/.jarvis/notes.db")
        self._contacts_db = os.path.expanduser("~/.jarvis/contacts.db")
        self._init_dbs()

    def _init_dbs(self):
        for db in [self._notes_db, self._contacts_db]:
            os.makedirs(os.path.dirname(db), exist_ok=True)
        conn = sqlite3.connect(self._notes_db)
        conn.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, title TEXT, body TEXT, created TEXT, updated TEXT, category TEXT)")
        conn.commit()
        conn.close()
        conn = sqlite3.connect(self._contacts_db)
        conn.execute("CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, email TEXT, address TEXT, notes TEXT)")
        conn.commit()
        conn.close()

    def _sh(self, cmd):
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return r.stdout[:2000] or r.stderr[:500]
        except Exception as e:
            return str(e)

    # === FILE ORGANIZER ===
    def file_organizer(self, directory=None, mode="type"):
        directory = os.path.expanduser(directory or "~/Downloads")
        rules = {
            "type": {
                "Imagens": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
                "Documentos": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".md"],
                "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv"],
                "Musica": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
                "Arquivos": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
                "Scripts": [".py", ".js", ".sh", ".bat", ".rb", ".pl"],
                "Outros": [],
            }
        }
        moved = 0
        for f in os.listdir(directory):
            fpath = os.path.join(directory, f)
            if os.path.isfile(fpath):
                ext = os.path.splitext(f)[1].lower()
                dest_dir = "Outros"
                for cat, exts in rules["type"].items():
                    if ext in exts:
                        dest_dir = cat
                        break
                dest_path = os.path.join(directory, dest_dir, f)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.move(fpath, dest_path)
                moved += 1
        return f"{moved} arquivos organizados em {directory}"

    # === NLP FILE SEARCH ===
    def nlp_file_search(self, query=None, path=None):
        if not query:
            return "Query necessária"
        path = os.path.expanduser(path or "~")
        terms = query.lower().split()
        results = []
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", ".git", "node_modules")]
            for f in files:
                fpath = os.path.join(root, f)
                if all(t in f.lower() for t in terms):
                    results.append(fpath)
                elif len(results) < 10:
                    for t in terms:
                        if t in f.lower():
                            results.append(fpath)
                            break
            if len(results) >= 20:
                break
        if not results:
            return "Nada encontrado"
        return "\n".join(results[:20])

    # === CLIPBOARD HISTORY ===
    def clipboard_history_start(self):
        if self._clipboard_running:
            return "Clipboard history já rodando"
        self._clipboard_running = True

        def poll():
            import pyperclip
            last = ""
            while self._clipboard_running:
                try:
                    current = pyperclip.paste()
                    if current and current != last:
                        self._clipboard_history.append({"time": datetime.now().isoformat(), "text": current[:200]})
                        if len(self._clipboard_history) > 100:
                            self._clipboard_history.pop(0)
                        last = current
                except Exception:
                    pass
                time.sleep(1)

        self._clipboard_thread = threading.Thread(target=poll, daemon=True)
        self._clipboard_thread.start()
        return "Histórico de clipboard iniciado"

    def clipboard_history_stop(self):
        self._clipboard_running = False
        return "Histórico parado"

    def clipboard_history_get(self, n=10):
        if not self._clipboard_history:
            return "Histórico vazio"
        return "\n---\n".join(f"[{e['time'][:19]}] {e['text']}" for e in self._clipboard_history[-n:])

    def clipboard_history_clear(self):
        self._clipboard_history.clear()
        return "Histórico limpo"

    # === CONVERSATION HISTORY SEARCH ===
    def conversation_search(self, query=None):
        if not query:
            return "Query necessária"
        hist_file = os.path.expanduser("~/.jarvis/history.json")
        if not os.path.exists(hist_file):
            return "Nenhum histórico encontrado"
        try:
            with open(hist_file) as f:
                data = json.load(f) if f.read().strip() else []
        except Exception:
            data = []
        if isinstance(data, dict):
            data = data.get("messages", data.get("history", []))
        results = []
        for msg in data:
            content = msg.get("content", msg.get("message", ""))
            if isinstance(content, str) and query.lower() in content.lower():
                role = msg.get("role", "?")
                results.append(f"[{role}] {content[:200]}")
        return "\n---\n".join(results[:10]) if results else "Nada encontrado"

    # === AUTO-INDEXAÇÃO ===
    def auto_index_start(self, directory=None):
        directory = os.path.expanduser(directory or "~/Documents")
        from brain.knowledge import KnowledgeBase
        kb = KnowledgeBase()
        return kb.learn_directory(directory, recursive=True)

    # === LOG ANALYZER ===
    def log_analyzer(self, service=None, lines=50):
        if service:
            return self._sh(f"journalctl -u {service} --no-pager -n {lines} 2>&1")
        return self._sh(f"journalctl -n {lines} --no-pager 2>&1")

    # === BACKUP ===
    def backup_create(self, source=None, dest=None):
        source = os.path.expanduser(source or "~/Documents")
        dest = os.path.expanduser(dest or f"~/Backups/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(dest, exist_ok=True)
        cmd = f'rsync -av --progress "{source}/" "{dest}/" 2>&1 | tail -5'
        return self._sh(cmd) or f"Backup salvo em {dest}"

    def backup_list(self, path=None):
        path = os.path.expanduser(path or "~/Backups")
        if not os.path.exists(path):
            return "Nenhum backup encontrado"
        backups = []
        for f in sorted(os.listdir(path))[-10:]:
            fpath = os.path.join(path, f)
            size = os.path.getsize(fpath) if os.path.isfile(fpath) else sum(os.path.getsize(os.path.join(dp, fn)) for dp, dn, fns in os.walk(fpath) for fn in fns) if os.path.isdir(fpath) else 0
            backups.append(f"{'DIR' if os.path.isdir(fpath) else 'FILE'} {f} ({size//1024//1024}MB)")
        return "\n".join(backups) if backups else "Nenhum backup"

    # === DEPENDENCY MONITOR ===
    def dependency_monitor(self):
        req = os.path.expanduser("~/jarvis/requirements.txt")
        if not os.path.exists(req):
            return "requirements.txt não encontrado"
        outdated = self._sh("pip list --user --outdated --format=columns 2>&1 | head -20")
        return f"Dependências desatualizadas:\n{outdated}" if outdated else "Tudo atualizado"

    # === NOTES ===
    def notes_add(self, title=None, body=None, category="general"):
        if not title or not body:
            return "Título e corpo necessários"
        conn = sqlite3.connect(self._notes_db)
        conn.execute("INSERT INTO notes (title, body, created, updated, category) VALUES (?, ?, ?, ?, ?)",
                     (title, body, datetime.now().isoformat(), datetime.now().isoformat(), category))
        conn.commit()
        conn.close()
        return f"Nota '{title}' salva"

    def notes_list(self, category=None):
        conn = sqlite3.connect(self._notes_db)
        if category:
            cur = conn.execute("SELECT id, title, created, category FROM notes WHERE category=? ORDER BY created DESC", (category,))
        else:
            cur = conn.execute("SELECT id, title, created, category FROM notes ORDER BY created DESC")
        notes = cur.fetchall()
        conn.close()
        return "\n".join(f"#{n[0]} [{n[3]}] {n[1]} ({n[2][:10]})" for n in notes[:20]) if notes else "Nenhuma nota"

    def notes_get(self, note_id=None):
        if not note_id:
            return "ID necessário"
        conn = sqlite3.connect(self._notes_db)
        cur = conn.execute("SELECT * FROM notes WHERE id=?", (note_id,))
        n = cur.fetchone()
        conn.close()
        return f"#{n[0]} {n[1]}\n{n[2]}\nCriado: {n[3]}" if n else "Nota não encontrada"

    def notes_delete(self, note_id=None):
        if not note_id:
            return "ID necessário"
        conn = sqlite3.connect(self._notes_db)
        conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
        conn.commit()
        conn.close()
        return f"Nota #{note_id} removida"

    # === CONTACTS ===
    def contacts_add(self, name=None, phone=None, email=None):
        if not name:
            return "Nome necessário"
        conn = sqlite3.connect(self._contacts_db)
        conn.execute("INSERT INTO contacts (name, phone, email) VALUES (?, ?, ?)", (name, phone or "", email or ""))
        conn.commit()
        conn.close()
        return f"Contato '{name}' salvo"

    def contacts_list(self, search=None):
        conn = sqlite3.connect(self._contacts_db)
        if search:
            cur = conn.execute("SELECT id, name, phone, email FROM contacts WHERE name LIKE ? OR phone LIKE ?", (f"%{search}%", f"%{search}%"))
        else:
            cur = conn.execute("SELECT id, name, phone, email FROM contacts ORDER BY name")
        contacts = cur.fetchall()
        conn.close()
        return "\n".join(f"#{c[0]} {c[1]} | {c[2]} | {c[3]}" for c in contacts[:20]) if contacts else "Nenhum contato"

    def contacts_delete(self, contact_id=None):
        if not contact_id:
            return "ID necessário"
        conn = sqlite3.connect(self._contacts_db)
        conn.execute("DELETE FROM contacts WHERE id=?", (contact_id,))
        conn.commit()
        conn.close()
        return f"Contato #{contact_id} removido"

    # === CALENDAR ===
    def calendar_add(self, title=None, date=None, time_str="12:00", duration=60):
        if not title or not date:
            return "Título e data necessários (formato YYYY-MM-DD)"
        cal_file = os.path.expanduser("~/.jarvis/calendar.json")
        events = []
        if os.path.exists(cal_file):
            try:
                with open(cal_file) as f:
                    events = json.load(f)
            except Exception:
                events = []
        events.append({"title": title, "date": date, "time": time_str, "duration": duration, "created": datetime.now().isoformat()})
        with open(cal_file, "w") as f:
            json.dump(events[-200:], f, indent=2)
        return f"Evento '{title}' em {date} às {time_str}"

    def calendar_list(self, date=None):
        cal_file = os.path.expanduser("~/.jarvis/calendar.json")
        if not os.path.exists(cal_file):
            return "Nenhum evento"
        try:
            with open(cal_file) as f:
                events = json.load(f)
        except Exception:
            return "Erro ao ler calendário"
        if date:
            events = [e for e in events if e.get("date") == date]
        return "\n".join(f"{e['date']} {e.get('time','')} - {e['title']}" for e in events[-20:]) if events else "Nenhum evento"

    # === GITHUB ===
    def github_issues(self, repo=None, state="open"):
        if not repo:
            return "Repo necessário (formato: usuario/repo)"
        return self._sh(f"gh issue list --repo {repo} --state {state} --limit 15 2>&1")

    def github_prs(self, repo=None, state="open"):
        if not repo:
            return "Repo necessário"
        return self._sh(f"gh pr list --repo {repo} --state {state} --limit 15 2>&1")

    def github_search(self, query=None):
        if not query:
            return "Query necessária"
        return self._sh(f"gh search repos {query} --limit 10 2>&1")

    # === JUPYTER ===
    def jupyter_execute(self, notebook=None, cell=None):
        if not notebook:
            return "Caminho do notebook necessário"
        notebook = os.path.expanduser(notebook)
        if not os.path.exists(notebook):
            return "Notebook não encontrado"
        return self._sh(f"jupyter nbconvert --to script {notebook} --stdout 2>&1 | head -50")

    # === INTRUSION DETECTION ===
    def intrusion_scan(self):
        failed = self._sh("journalctl -u ssh --no-pager -n 100 2>&1 | grep 'Failed password' | wc -l")
        listening = self._sh("ss -tlnp 2>&1 | head -20")
        return f"Tentativas SSH falhas: {failed.strip()}\n\nPortas abertas:\n{listening}"

    # === FIREWALL ===
    def firewall_rule_add(self, action="allow", port=None, protocol="tcp"):
        if not port:
            return "Porta necessária"
        action_map = {"allow": "ACCEPT", "deny": "DROP", "reject": "REJECT"}
        cmd = f"sudo iptables -A INPUT -p {protocol} --dport {port} -j {action_map.get(action, 'ACCEPT')}"
        return self._sh(cmd) or f"Regra adicionada: {action} {protocol}:{port}"

    def firewall_rule_list(self):
        return self._sh("sudo iptables -L INPUT -n --line-numbers 2>&1 | head -30")

    # === CERTIFICATE ===
    def certificate_check(self, domain=None):
        if not domain:
            return "Domínio necessário"
        return self._sh(f"echo | openssl s_client -connect {domain}:443 -servername {domain} 2>&1 | openssl x509 -noout -dates 2>&1")

    def certificate_generate(self, domain=None):
        if not domain:
            return "Domínio necessário"
        key = os.path.expanduser(f"~/{domain}.key")
        cert = os.path.expanduser(f"~/{domain}.crt")
        self._sh(f"openssl req -x509 -newkey rsa:2048 -keyout {key} -out {cert} -days 365 -nodes -subj '/CN={domain}' 2>&1")
        return f"Certificado auto-assinado: {cert}"

    # === SESSION RECORDER ===
    def session_record_start(self):
        self._session_recording = True
        self._session_events = []
        return "Gravação de sessão iniciada"

    def session_record_stop(self):
        self._session_recording = False
        count = len(self._session_events)
        path = os.path.expanduser(f"~/.jarvis/session_{int(time.time())}.json")
        with open(path, "w") as f:
            json.dump(self._session_events, f)
        return f"Sessão salva ({count} eventos): {path}"

    def session_replay(self, path=None):
        if not path:
            return "Caminho do arquivo de sessão necessário"
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return "Arquivo não encontrado"
        try:
            import pyautogui
            with open(path) as f:
                events = json.load(f)
            for ev in events:
                if ev["type"] == "click":
                    pyautogui.click(ev["x"], ev["y"])
                elif ev["type"] == "type":
                    pyautogui.write(ev["text"])
                time.sleep(0.3)
            return f"Sessão reproduzida ({len(events)} eventos)"
        except Exception as e:
            return f"Erro: {e}"

    # === GPU INFO ===
    def gpu_info(self):
        nvidia = self._sh("nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu --format=csv,noheader 2>&1")
        if "not found" not in nvidia.lower():
            return f"GPU NVIDIA:\n{nvidia}"
        amd = self._sh("rocm-smi 2>&1 | head -10")
        if "not found" not in amd.lower():
            return f"GPU AMD:\n{amd}"
        return "Nenhuma GPU dedicada encontrada ou drivers não instalados"

    # === WAKE WORD ===
    def wake_word_set(self, word=None):
        if not word:
            return "Palavra necessária (ex: 'Jarvis', 'Computador', 'Eva')"
        import config.settings as settings
        settings.set_key("stt.wake_word", word)
        return f"Wake word alterada para '{word}'. Reinicie para aplicar."

    # === EMBEDDING MODEL ===
    def embedding_model_set(self, model=None):
        if not model:
            return "Modelo necessário (ex: 'all-MiniLM-L6-v2', 'paraphrase-multilingual-MiniLM-L12-v2')"
        import config.settings as settings
        settings.set_key("memory.embedding_model", model)
        return f"Modelo de embedding alterado para '{model}'. Na próxima inicialização."

    # === AMBIENT MUSIC ===
    def ambient_music_play(self, file=None):
        if not file:
            file = "/usr/share/sounds/freedesktop/stereo/bell.oga"
            if not os.path.exists(file):
                return "Arquivo de música não especificado"
        file = os.path.expanduser(file)
        if not os.path.exists(file):
            return "Arquivo não encontrado"
        self.ambient_music_stop()
        self._ambient_process = subprocess.Popen(["ffplay", "-nodisp", "-loop", "0", file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Tocando: {file}"

    def ambient_music_stop(self):
        if self._ambient_process:
            self._ambient_process.terminate()
            self._ambient_process = None
            return "Música parada"
        return "Nada tocando"

    # === THEME ===
    def theme_set(self, theme=None):
        themes = {
            "dark": "QWidget { background-color: #1a1a2e; color: #eee; } QPushButton { background: #16213e; }",
            "light": "QWidget { background-color: #f5f5f5; color: #222; } QPushButton { background: #ddd; }",
            "hacker": "QWidget { background-color: #000; color: #0f0; font-family: monospace; } QPushButton { background: #030; border: 1px solid #0f0; }",
            "ironman": "QWidget { background-color: #1a0000; color: #ffd700; } QPushButton { background: #8b0000; border: 1px solid #ffd700; }",
        }
        if theme not in themes:
            return f"Temas disponíveis: {', '.join(themes.keys())}"
        import config.settings as settings
        settings.set_key("ui.theme_css", themes[theme])
        return f"Tema '{theme}' aplicado. Reinicie o Jarvis GUI para ver."

    # === NOTIFICATION ===
    def notification_send(self, title=None, message=None, urgency="normal"):
        if not message:
            return "Mensagem necessária"
        icons = {"low": "dialog-information", "normal": "dialog-information", "critical": "dialog-error"}
        return self._sh(f'notify-send -u {urgency} -i {icons.get(urgency, "dialog-information")} "{title or "Jarvis"}" "{message}"')

    # === EMAIL FETCH ===
    def email_fetch(self, limit=10):
        import config.settings as settings
        cfg = settings.get("email", {})
        if not cfg.get("server") or not cfg.get("user") or not cfg.get("password"):
            return "Configure email no config.json (server, user, password, imap_port=993)"
        try:
            import imaplib
            import email
            m = imaplib.IMAP4_SSL(cfg["server"], cfg.get("imap_port", 993))
            m.login(cfg["user"], cfg["password"])
            m.select("INBOX")
            _, data = m.search(None, "ALL")
            ids = data[0].split()[-limit:]
            results = []
            for i in ids:
                _, msg_data = m.fetch(i, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
                for part in msg_data:
                    if isinstance(part, tuple):
                        msg = email.message_from_bytes(part[1])
                        results.append(f"{msg['Date'][:25]} | {msg['From']} | {msg['Subject']}")
            m.logout()
            return "\n".join(results) if results else "Nenhum email"
        except ImportError:
            return "imaplib não está disponível"
        except Exception as e:
            return f"Erro: {e}"

    # === DISCORD ===
    def discord_send(self, webhook_url=None, message=None):
        if not webhook_url or not message:
            return "webhook_url e message necessários"
        try:
            import requests
            r = requests.post(webhook_url, json={"content": message}, timeout=15)
            return f"Discord: {r.status_code}" if r.ok else f"Erro: {r.text[:200]}"
        except Exception as e:
            return f"Erro: {e}"

    # === WHATSAPP ===
    def whatsapp_send(self, number=None, message=None):
        if not number or not message:
            return "number e message necessários"
        import urllib.parse
        url = f"https://wa.me/{number}?text={urllib.parse.quote(message)}"
        import webbrowser
        webbrowser.open(url)
        return f"WhatsApp Web aberto para {number}. Envie a mensagem manualmente se necessário."

    # === SMS ===
    def sms_send(self, number=None, message=None):
        if not number or not message:
            return "number e message necessários"
        if os.path.exists("/usr/bin/gnokii"):
            return self._sh(f'echo "{message}" | gnokii --sendsms {number} 2>&1')
        return "SMS não disponível (gnokii não instalado). Use whatsapp_send como alternativa."

    # === HOME ASSISTANT ===
    def home_assistant_query(self, entity=None):
        import config.settings as settings
        cfg = settings.get("homeassistant", {})
        if not cfg.get("url") or not cfg.get("token"):
            return "Configure homeassistant.url e homeassistant.token no config.json"
        try:
            import requests
            headers = {"Authorization": f"Bearer {cfg['token']}", "Content-Type": "application/json"}
            if entity:
                r = requests.get(f"{cfg['url']}/api/states/{entity}", headers=headers, timeout=15)
            else:
                r = requests.get(f"{cfg['url']}/api/states", headers=headers, timeout=15)
            return json.dumps(r.json()[:5], indent=2) if r.ok else f"Erro: {r.text[:200]}"
        except Exception as e:
            return f"Erro: {e}"

    def home_assistant_control(self, entity=None, service=None):
        import config.settings as settings
        cfg = settings.get("homeassistant", {})
        if not cfg.get("url") or not cfg.get("token") or not entity or not service:
            return "Configure url/token e forneça entity + service"
        try:
            import requests
            domain, svc = service.split(".", 1)
            headers = {"Authorization": f"Bearer {cfg['token']}", "Content-Type": "application/json"}
            r = requests.post(f"{cfg['url']}/api/services/{domain}/{svc}",
                            json={"entity_id": entity}, headers=headers, timeout=15)
            return f"OK: {r.status_code}" if r.ok else f"Erro: {r.text[:200]}"
        except Exception as e:
            return f"Erro: {e}"

    # === VOICE EMOTION ===
    def voice_emotion_set(self, emotion=None):
        emotions = {
            "normal": "pt-BR-AntonioNeural",
            "calmo": "pt-BR-AntonioNeural",
            "animado": "pt-BR-AntonioNeural",
            "serio": "pt-BR-AntonioNeural",
        }
        if emotion not in emotions:
            return f"Emoções: {', '.join(emotions.keys())}"
        import config.settings as settings
        settings.set_key("tts.emotion", emotion)
        return f"Emoção '{emotion}' configurada"

    # === NETWORK MONITOR ===
    def network_monitor_start(self):
        if self._network_monitor_running:
            return "Monitor já rodando"
        self._network_monitor_running = True

        def monitor():
            while self._network_monitor_running:
                try:
                    import psutil
                    net = psutil.net_io_counters()
                    log = os.path.expanduser("~/.jarvis/network_log.csv")
                    with open(log, "a") as f:
                        f.write(f"{time.time()},{net.bytes_sent},{net.bytes_recv}\n")
                except Exception:
                    pass
                time.sleep(60)

        self._network_monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._network_monitor_thread.start()
        return "Monitor de rede iniciado (log a cada 60s em ~/.jarvis/network_log.csv)"

    def network_monitor_stop(self):
        self._network_monitor_running = False
        return "Monitor de rede parado"

    # === CODE REVIEW ===
    def code_review(self, path=None):
        if not path:
            return "Caminho do arquivo/diretório necessário"
        path = os.path.expanduser(path)
        if os.path.isfile(path) and path.endswith(".py"):
            with open(path) as f:
                code = f.read()
        elif os.path.isdir(path):
            py_files = [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".py")]
            if not py_files:
                return "Nenhum arquivo .py encontrado"
            with open(py_files[0]) as f:
                code = f.read()
        else:
            return "Arquivo não encontrado ou não suportado"
        import ast
        issues = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and len(node.body) > 50:
                    issues.append(f"Função '{node.name}' muito longa ({len(node.body)} linhas)")
                if isinstance(node, ast.Try) and not node.handlers and not node.finalbody:
                    issues.append("Try sem except/finally")
        except SyntaxError as e:
            issues.append(f"Erro de sintaxe: {e}")
        if not issues:
            issues.append("Nenhum problema encontrado")
        return "\n".join(issues)


ALL_FEATURES = [
    # File & System
    ("file_organizer", JarvisFeatures.file_organizer,
     "Organizar arquivos em pastas por tipo (Imagens, Documentos, etc)", {"directory": {"type": "string"}, "mode": {"type": "string"}}),
    ("nlp_file_search", JarvisFeatures.nlp_file_search,
     "Buscar arquivos por descrição em linguagem natural", {"query": {"type": "string"}, "path": {"type": "string"}}),
    ("auto_index_start", JarvisFeatures.auto_index_start,
     "Indexar diretório na base de conhecimento automaticamente", {"directory": {"type": "string"}}),
    ("log_analyzer", JarvisFeatures.log_analyzer,
     "Analisar logs do sistema (journalctl)", {"service": {"type": "string"}, "lines": {"type": "integer"}}),
    ("dependency_monitor", JarvisFeatures.dependency_monitor,
     "Verificar dependências pip desatualizadas", {}),
    ("backup_create", JarvisFeatures.backup_create,
     "Criar backup de diretório via rsync", {"source": {"type": "string"}, "dest": {"type": "string"}}),
    ("backup_list", JarvisFeatures.backup_list,
     "Listar backups disponíveis", {"path": {"type": "string"}}),

    # Clipboard History
    ("clipboard_history_start", JarvisFeatures.clipboard_history_start,
     "Iniciar monitoramento do histórico de clipboard", {}),
    ("clipboard_history_stop", JarvisFeatures.clipboard_history_stop,
     "Parar monitoramento do clipboard", {}),
    ("clipboard_history_get", JarvisFeatures.clipboard_history_get,
     "Ver histórico do clipboard", {"n": {"type": "integer"}}),
    ("clipboard_history_clear", JarvisFeatures.clipboard_history_clear,
     "Limpar histórico do clipboard", {}),

    # Conversation
    ("conversation_search", JarvisFeatures.conversation_search,
     "Buscar em conversas antigas por assunto", {"query": {"type": "string"}}),

    # Notes
    ("notes_add", JarvisFeatures.notes_add,
     "Adicionar nota", {"title": {"type": "string"}, "body": {"type": "string"}, "category": {"type": "string"}}),
    ("notes_list", JarvisFeatures.notes_list,
     "Listar notas", {"category": {"type": "string"}}),
    ("notes_get", JarvisFeatures.notes_get,
     "Ler nota por ID", {"note_id": {"type": "string"}}),
    ("notes_delete", JarvisFeatures.notes_delete,
     "Remover nota", {"note_id": {"type": "string"}}),

    # Contacts
    ("contacts_add", JarvisFeatures.contacts_add,
     "Adicionar contato", {"name": {"type": "string"}, "phone": {"type": "string"}, "email": {"type": "string"}}),
    ("contacts_list", JarvisFeatures.contacts_list,
     "Listar/buscar contatos", {"search": {"type": "string"}}),
    ("contacts_delete", JarvisFeatures.contacts_delete,
     "Remover contato", {"contact_id": {"type": "string"}}),

    # Calendar
    ("calendar_add", JarvisFeatures.calendar_add,
     "Adicionar evento no calendário", {"title": {"type": "string"}, "date": {"type": "string"}, "time": {"type": "string"}, "duration": {"type": "integer"}}),
    ("calendar_list", JarvisFeatures.calendar_list,
     "Listar eventos do calendário", {"date": {"type": "string"}}),

    # GitHub
    ("github_issues", JarvisFeatures.github_issues,
     "Listar issues do GitHub (precisa gh CLI configurado)", {"repo": {"type": "string"}, "state": {"type": "string"}}),
    ("github_prs", JarvisFeatures.github_prs,
     "Listar PRs do GitHub", {"repo": {"type": "string"}, "state": {"type": "string"}}),
    ("github_search", JarvisFeatures.github_search,
     "Buscar repositórios no GitHub", {"query": {"type": "string"}}),

    # Security
    ("intrusion_scan", JarvisFeatures.intrusion_scan,
     "Escanear tentativas de invasão e portas abertas", {}),
    ("firewall_rule_add", JarvisFeatures.firewall_rule_add,
     "Adicionar regra no firewall (iptables)", {"action": {"type": "string"}, "port": {"type": "integer"}, "protocol": {"type": "string"}}),
    ("firewall_rule_list", JarvisFeatures.firewall_rule_list,
     "Listar regras do firewall", {}),
    ("certificate_check", JarvisFeatures.certificate_check,
     "Verificar validade de certificado SSL de um domínio", {"domain": {"type": "string"}}),
    ("certificate_generate", JarvisFeatures.certificate_generate,
     "Gerar certificado SSL auto-assinado", {"domain": {"type": "string"}}),

    # Session
    ("session_record_start", JarvisFeatures.session_record_start,
     "Iniciar gravação de sessão (cliques e teclas)", {}),
    ("session_record_stop", JarvisFeatures.session_record_stop,
     "Parar gravação e salvar sessão", {}),
    ("session_replay", JarvisFeatures.session_replay,
     "Reproduzir sessão gravada", {"path": {"type": "string"}}),

    # System
    ("gpu_info", JarvisFeatures.gpu_info,
     "Informações da GPU (NVIDIA/AMD)", {}),
    ("wake_word_set", JarvisFeatures.wake_word_set,
     "Alterar a palavra de ativação (wake word)", {"word": {"type": "string"}}),
    ("embedding_model_set", JarvisFeatures.embedding_model_set,
     "Alterar modelo de embedding para memória semântica", {"model": {"type": "string"}}),
    ("theme_set", JarvisFeatures.theme_set,
     "Alterar tema da interface (dark/light/hacker/ironman)", {"theme": {"type": "string"}}),
    ("notification_send", JarvisFeatures.notification_send,
     "Enviar notificação para o desktop", {"title": {"type": "string"}, "message": {"type": "string"}, "urgency": {"type": "string"}}),
    ("voice_emotion_set", JarvisFeatures.voice_emotion_set,
     "Alterar emoção da voz do TTS", {"emotion": {"type": "string"}}),

    # Music
    ("ambient_music_play", JarvisFeatures.ambient_music_play,
     "Tocar música ambiente", {"file": {"type": "string"}}),
    ("ambient_music_stop", JarvisFeatures.ambient_music_stop,
     "Parar música", {}),

    # Network Monitor
    ("network_monitor_start", JarvisFeatures.network_monitor_start,
     "Iniciar monitoramento de rede em background", {}),
    ("network_monitor_stop", JarvisFeatures.network_monitor_stop,
     "Parar monitoramento de rede", {}),

    # Communication
    ("email_fetch", JarvisFeatures.email_fetch,
     "Buscar emails da caixa de entrada (IMAP)", {"limit": {"type": "integer"}}),
    ("discord_send", JarvisFeatures.discord_send,
     "Enviar mensagem no Discord via webhook", {"webhook_url": {"type": "string"}, "message": {"type": "string"}}),
    ("whatsapp_send", JarvisFeatures.whatsapp_send,
     "Abrir WhatsApp Web para enviar mensagem", {"number": {"type": "string"}, "message": {"type": "string"}}),
    ("sms_send", JarvisFeatures.sms_send,
     "Enviar SMS (precisa gnokii instalado)", {"number": {"type": "string"}, "message": {"type": "string"}}),

    # Home Assistant
    ("home_assistant_query", JarvisFeatures.home_assistant_query,
     "Consultar estado de entidade no Home Assistant", {"entity": {"type": "string"}}),
    ("home_assistant_control", JarvisFeatures.home_assistant_control,
     "Controlar entidade no Home Assistant", {"entity": {"type": "string"}, "service": {"type": "string"}}),

    # Code Review
    ("code_review", JarvisFeatures.code_review,
     "Revisar código Python e apontar problemas", {"path": {"type": "string"}}),
]
