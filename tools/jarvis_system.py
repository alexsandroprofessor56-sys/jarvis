import base64
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from tools.registry import registry

# GUI libraries are imported lazily inside functions to avoid
# crashes when DISPLAY is not available at import time.

logger = logging.getLogger("jarvis_system")

# ── Helpers ───────────────────────────────────────────────────────────

def _lazy_imports():
    import mss as _mss
    import pyautogui as _pyautogui
    import pyperclip as _pyperclip
    import pytesseract as _pytesseract
    from PIL import Image as _PILImage
    return _mss, _pyautogui, _pyperclip, _pytesseract, _PILImage


def _screenshot_pil(region=None):
    """Capture screen → PIL Image using mss (fast, no external deps)."""
    _ensure()
    mss, _, _, _, PIL = _lazy_imports()
    with mss.MSS() as sct:
        if region:
            mon = {"left": region[0], "top": region[1], "width": region[2], "height": region[3]}
        else:
            mon = sct.monitors[1]  # primary monitor
        sct_img = sct.grab(mon)
        # sct_img: ScreenShot with .rgb (bytes) and .width / .height
        return PIL.frombytes("RGB", (sct_img.width, sct_img.height), sct_img.rgb)


def _img_to_b64(img, fmt="PNG") -> str:
    import io
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode()


def _ensure_display():
    if not os.environ.get("DISPLAY"):
        os.environ["DISPLAY"] = ":0"


_ENSURED_DISPLAY = False


def _ensure():
    global _ENSURED_DISPLAY
    if not _ENSURED_DISPLAY:
        _ensure_display()
        _ENSURED_DISPLAY = True


def tool_result(data=None, **kwargs):
    if data is not None:
        return json.dumps({"success": True, "data": data, **kwargs})
    return json.dumps({"success": True, **kwargs})


def tool_error(msg):
    return json.dumps({"success": False, "error": msg})


# ── Tools ─────────────────────────────────────────────────────────────

# ── Screen Capture ────────────────────────────────────────────────────

def screen_capture(region=None, as_base64=False, path=None):
    _ensure()
    _, pag, _, _, _ = _lazy_imports()
    try:
        r = None
        if region:
            r = (region["x"], region["y"], region["w"], region["h"])
        img = _screenshot_pil(r)
        ts = datetime.now().isoformat()

        if path:
            os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
            img.save(path)
            return tool_result(path=os.path.abspath(path), ts=ts)

        if as_base64:
            b64 = _img_to_b64(img)
            return tool_result(base64=b64, ts=ts, format="PNG")

        return tool_result(ts=ts, width=img.width, height=img.height, message="Capturado")
    except Exception as e:
        return tool_error(str(e))


SCREEN_CAPTURE_SCHEMA = {
    "name": "screen_capture",
    "description": "Capturar a tela (ou região) como imagem. Salva em arquivo ou retorna base64.",
    "parameters": {
        "type": "object",
        "properties": {
            "region": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer"}, "y": {"type": "integer"},
                    "w": {"type": "integer"}, "h": {"type": "integer"},
                },
                "description": "Região da tela: {x, y, w, h}. Opcional — captura tela toda.",
            },
            "as_base64": {
                "type": "boolean",
                "description": "Retornar imagem em base64 (para visão da IA). Default false.",
            },
            "path": {
                "type": "string",
                "description": "Salvar em arquivo. Ex: /tmp/screenshot.png. Opcional.",
            },
        },
    },
}


# ── Screen OCR ────────────────────────────────────────────────────────

def screen_ocr(region=None, lang="por"):
    _ensure()
    _, _, _, tes, _ = _lazy_imports()
    try:
        r = None
        if region:
            r = (region["x"], region["y"], region["w"], region["h"])
        img = _screenshot_pil(r)
        text = tes.image_to_string(img, lang=lang)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        return tool_result(text=text, lines=lines, line_count=len(lines))
    except Exception as e:
        return tool_error(str(e))


SCREEN_OCR_SCHEMA = {
    "name": "screen_ocr",
    "description": "Extrair texto da tela (OCR). Lê o que está visível e retorna como texto.",
    "parameters": {
        "type": "object",
        "properties": {
            "region": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer"}, "y": {"type": "integer"},
                    "w": {"type": "integer"}, "h": {"type": "integer"},
                },
                "description": "Região para OCR. Opcional — usa tela toda.",
            },
            "lang": {
                "type": "string",
                "description": "Idioma do OCR. Default 'por' (português).",
                "default": "por",
            },
        },
    },
}


# ── Screen Ask ────────────────────────────────────────────────────────

def _try_vision_tts(text, lang="pt"):
    """Fala o texto usando TTS no sistema (fallback silencioso)."""
    try:
        import subprocess
        subprocess.run(["spd-say", "-l", lang, text],
                       timeout=10, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    except Exception:
        pass


def _find_vision_model():
    """Check Ollama for a vision-capable model. Returns model name or None."""
    try:
        import httpx
        resp = httpx.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            # Check known vision models in priority order
            vision_models = [m for m in models if any(k in m.lower() for k in
                            ("llava", "minicpm", "moondream", "bakllava", "vision", "v LLM"))]
            if vision_models:
                return sorted(vision_models)[0]
    except Exception:
        pass
    return None


def screen_ask(question, region=None):
    _ensure()
    _, _, _, _, _ = _lazy_imports()
    try:
        r = None
        if region:
            r = (region["x"], region["y"], region["w"], region["h"])
        img = _screenshot_pil(r)
        b64 = _img_to_b64(img)

        # Try vision model first
        vision_model = _find_vision_model()
        if vision_model:
            prompt = f"""Analise esta imagem da tela e responda: {question}

Descreva o que você vê na tela em detalhes. Que aplicativos estão abertos? 
Que conteúdo é visível? Responda em português."""
            import httpx
            resp = httpx.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": vision_model,
                    "prompt": prompt,
                    "images": [b64],
                    "stream": False,
                },
                timeout=120,
            )
            if resp.status_code == 200:
                data = resp.json()
                answer = data.get("response", "")
                return tool_result(answer=answer, question=question)

        # Fallback: describe via OCR
        import pytesseract
        text = pytesseract.image_to_string(img, lang="por")
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        answer = f"Não há modelo de visão disponível. O que vi na tela via OCR:\n" + "\n".join(lines[:30])
        if len(lines) > 30:
            answer += f"\n... e mais {len(lines)-30} linhas."
        return tool_result(answer=answer, question=question, via_ocr=True)

    except Exception as e:
        return tool_error(str(e))


SCREEN_ASK_SCHEMA = {
    "name": "screen_ask",
    "description": "Tirar um print da tela e perguntar algo sobre ela para a IA com visão (Ollama). Ex: 'o que tem na tela?', 'tem algum erro visível?'",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "Pergunta sobre a tela.",
            },
            "region": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer"}, "y": {"type": "integer"},
                    "w": {"type": "integer"}, "h": {"type": "integer"},
                },
                "description": "Região da tela. Opcional.",
            },
        },
        "required": ["question"],
    },
}


# ── Mouse ─────────────────────────────────────────────────────────────

def mouse_move(x, y, duration=0.2):
    _ensure()
    _, pag, _, _, _ = _lazy_imports()
    try:
        pag.moveTo(x, y, duration=duration)
        return tool_result(message=f"Mouse movido para ({x}, {y})")
    except Exception as e:
        return tool_error(str(e))


MOUSE_MOVE_SCHEMA = {
    "name": "mouse_move",
    "description": "Mover o cursor do mouse para coordenadas (x, y) na tela.",
    "parameters": {
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "Coordenada X."},
            "y": {"type": "integer", "description": "Coordenada Y."},
            "duration": {"type": "number", "description": "Duração do movimento em segundos. Default 0.2.", "default": 0.2},
        },
        "required": ["x", "y"],
    },
}


def mouse_click(x=None, y=None, button="left", clicks=1):
    _ensure()
    _, pag, _, _, _ = _lazy_imports()
    try:
        if x is not None and y is not None:
            pag.click(x, y, clicks=clicks, button=button)
        else:
            pag.click(clicks=clicks, button=button)
        return tool_result(message=f"Clique {button} em ({x or 'atual'}, {y or 'atual'})")
    except Exception as e:
        return tool_error(str(e))


MOUSE_CLICK_SCHEMA = {
    "name": "mouse_click",
    "description": "Clicar com o mouse. Pode especificar posição ou clicar onde o cursor está.",
    "parameters": {
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "Coordenada X. Opcional."},
            "y": {"type": "integer", "description": "Coordenada Y. Opcional."},
            "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "Botão. Default 'left'.", "default": "left"},
            "clicks": {"type": "integer", "description": "Número de cliques. Default 1.", "default": 1},
        },
    },
}


def mouse_scroll(clicks, x=None, y=None):
    _ensure()
    _, pag, _, _, _ = _lazy_imports()
    try:
        if x is not None and y is not None:
            pag.scroll(clicks, x=x, y=y)
        else:
            pag.scroll(clicks)
        direction = "para cima" if clicks > 0 else "para baixo"
        return tool_result(message=f"Scroll {direction} ({clicks} cliques)")
    except Exception as e:
        return tool_error(str(e))


MOUSE_SCROLL_SCHEMA = {
    "name": "mouse_scroll",
    "description": "Rolar a tela (scroll). Positivo = para cima, negativo = para baixo.",
    "parameters": {
        "type": "object",
        "properties": {
            "clicks": {"type": "integer", "description": "Quantidade de scroll. Positivo sobe, negativo desce."},
            "x": {"type": "integer", "description": "Posição X. Opcional."},
            "y": {"type": "integer", "description": "Posição Y. Opcional."},
        },
        "required": ["clicks"],
    },
}


# ── Keyboard ──────────────────────────────────────────────────────────

def keyboard_type(text, interval=0.01):
    _ensure()
    _, pag, _, _, _ = _lazy_imports()
    try:
        pag.typewrite(text, interval=interval)
        return tool_result(message=f"Texto digitado ({len(text)} caracteres)")
    except Exception as e:
        return tool_error(str(e))


KEYBOARD_TYPE_SCHEMA = {
    "name": "keyboard_type",
    "description": "Digitar texto via teclado. Simula digitação humana com intervalo entre teclas.",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Texto a ser digitado."},
            "interval": {"type": "number", "description": "Intervalo entre teclas em segundos. Default 0.01.", "default": 0.01},
        },
        "required": ["text"],
    },
}


def keyboard_hotkey(keys):
    _ensure()
    _, pag, _, _, _ = _lazy_imports()
    try:
        if isinstance(keys, str):
            keys = keys.split("+")
        pag.hotkey(*keys)
        return tool_result(message=f"Atalho: {'+'.join(keys)}")
    except Exception as e:
        return tool_error(str(e))


KEYBOARD_HOTKEY_SCHEMA = {
    "name": "keyboard_hotkey",
    "description": "Pressionar atalho do teclado. Ex: ['ctrl', 'c'] para copiar, ['alt', 'tab'] para alternar janela.",
    "parameters": {
        "type": "object",
        "properties": {
            "keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Lista de teclas do atalho. Ex: ['ctrl', 'c'].",
            },
        },
        "required": ["keys"],
    },
}


# ── Clipboard ─────────────────────────────────────────────────────────

def clipboard_get():
    _ensure()
    _, _, clip, _, _ = _lazy_imports()
    try:
        text = clip.paste()
        return tool_result(text=text, length=len(text))
    except Exception as e:
        return tool_error(str(e))


CLIPBOARD_GET_SCHEMA = {
    "name": "clipboard_get",
    "description": "Obter o conteúdo atual da área de transferência.",
    "parameters": {"type": "object", "properties": {}},
}


def clipboard_set(text):
    _ensure()
    _, _, clip, _, _ = _lazy_imports()
    try:
        clip.copy(text)
        return tool_result(message=f"Texto copiado para área de transferência ({len(text)} chars)")
    except Exception as e:
        return tool_error(str(e))


CLIPBOARD_SET_SCHEMA = {
    "name": "clipboard_set",
    "description": "Definir o conteúdo da área de transferência (copiar texto).",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Texto a copiar."},
        },
        "required": ["text"],
    },
}


# ── File Operations ───────────────────────────────────────────────────

def file_create(path, content="", is_dir=False):
    try:
        p = Path(path).expanduser().resolve()
        if is_dir:
            p.mkdir(parents=True, exist_ok=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        return tool_result(path=str(p), action="created", is_dir=is_dir)
    except Exception as e:
        return tool_error(str(e))


FILE_CREATE_SCHEMA = {
    "name": "file_create",
    "description": "Criar um arquivo ou diretório.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Caminho do arquivo/diretório."},
            "content": {"type": "string", "description": "Conteúdo do arquivo (se não for diretório).", "default": ""},
            "is_dir": {"type": "boolean", "description": "Se true, cria diretório.", "default": False},
        },
        "required": ["path"],
    },
}


def file_delete(path, recursive=False):
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return tool_error(f"Arquivo não encontrado: {path}")
        if p.is_dir():
            if recursive:
                shutil.rmtree(p)
            else:
                p.rmdir()
        else:
            p.unlink()
        return tool_result(path=str(p), action="deleted")
    except Exception as e:
        return tool_error(str(e))


FILE_DELETE_SCHEMA = {
    "name": "file_delete",
    "description": "Deletar arquivo ou diretório. Use recursive=true para deletar diretório com conteúdo.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Caminho do arquivo/diretório."},
            "recursive": {"type": "boolean", "description": "Deletar recursivamente (para diretórios).", "default": False},
        },
        "required": ["path"],
    },
}


def file_copy(src, dst):
    try:
        sp = Path(src).expanduser().resolve()
        dp = Path(dst).expanduser().resolve()
        if not sp.exists():
            return tool_error(f"Origem não encontrada: {src}")
        dp.parent.mkdir(parents=True, exist_ok=True)
        if sp.is_dir():
            shutil.copytree(sp, dp)
        else:
            shutil.copy2(sp, dp)
        return tool_result(src=str(sp), dst=str(dp), action="copied")
    except Exception as e:
        return tool_error(str(e))


FILE_COPY_SCHEMA = {
    "name": "file_copy",
    "description": "Copiar arquivo ou diretório.",
    "parameters": {
        "type": "object",
        "properties": {
            "src": {"type": "string", "description": "Caminho de origem."},
            "dst": {"type": "string", "description": "Caminho de destino."},
        },
        "required": ["src", "dst"],
    },
}


def file_move(src, dst):
    try:
        sp = Path(src).expanduser().resolve()
        dp = Path(dst).expanduser().resolve()
        if not sp.exists():
            return tool_error(f"Origem não encontrada: {src}")
        dp.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(sp), str(dp))
        return tool_result(src=str(sp), dst=str(dp), action="moved")
    except Exception as e:
        return tool_error(str(e))


FILE_MOVE_SCHEMA = {
    "name": "file_move",
    "description": "Mover ou renomear arquivo/diretório.",
    "parameters": {
        "type": "object",
        "properties": {
            "src": {"type": "string", "description": "Caminho de origem."},
            "dst": {"type": "string", "description": "Caminho de destino."},
        },
        "required": ["src", "dst"],
    },
}


def file_list(path=".", pattern=None):
    try:
        p = Path(path).expanduser().resolve()
        if not p.is_dir():
            return tool_error(f"Diretório não encontrado: {path}")
        items = []
        for child in sorted(p.iterdir()):
            if pattern and pattern not in child.name:
                continue
            stat = child.stat()
            items.append({
                "name": child.name,
                "path": str(child),
                "is_dir": child.is_dir(),
                "size": stat.st_size if child.is_file() else 0,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        return tool_result(directory=str(p), items=items, count=len(items))
    except Exception as e:
        return tool_error(str(e))


FILE_LIST_SCHEMA = {
    "name": "file_list",
    "description": "Listar conteúdo de um diretório.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Caminho do diretório. Default '.'."},
            "pattern": {"type": "string", "description": "Filtro por nome (substring). Opcional."},
        },
    },
}


# ── Application Management ───────────────────────────────────────────

def app_launch(command_or_path, args=None, wait=False):
    try:
        cmd = command_or_path
        if args:
            if isinstance(args, list):
                cmd = [cmd] + args
            else:
                cmd = [cmd, args]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        if wait:
            proc.wait(timeout=30)
        return tool_result(pid=proc.pid, command=str(command_or_path), action="launched")
    except Exception as e:
        return tool_error(str(e))


APP_LAUNCH_SCHEMA = {
    "name": "app_launch",
    "description": "Lançar uma aplicação ou comando. Ex: 'firefox', 'nautilus /home', 'code /projeto'.",
    "parameters": {
        "type": "object",
        "properties": {
            "command_or_path": {"type": "string", "description": "Comando ou caminho do executável."},
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Argumentos da linha de comando. Opcional.",
            },
            "wait": {
                "type": "boolean",
                "description": "Aguardar finalização? Default false (não bloqueia).",
                "default": False,
            },
        },
        "required": ["command_or_path"],
    },
}


def app_kill(name_or_pid=None, all_by_name=False):
    try:
        if name_or_pid is None:
            return tool_error("Forneça nome ou PID")

        killed = []
        import psutil
        # Try as PID first
        try:
            pid = int(name_or_pid)
            proc = psutil.Process(pid)
            name = proc.name()
            proc.terminate()
            killed.append(f"{name}(PID {pid})")
            return tool_result(killed=killed)
        except (ValueError, psutil.NoSuchProcess):
            pass

        # Kill by name
        for proc in psutil.process_iter(["pid", "name"]):
            if name_or_pid.lower() in proc.info["name"].lower():
                try:
                    p = psutil.Process(proc.info["pid"])
                    p.terminate()
                    killed.append(f"{proc.info['name']}(PID {proc.info['pid']})")
                    if not all_by_name:
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        if killed:
            return tool_result(killed=killed)
        return tool_error(f"Processo não encontrado: {name_or_pid}")
    except Exception as e:
        return tool_error(str(e))


APP_KILL_SCHEMA = {
    "name": "app_kill",
    "description": "Finalizar um processo por nome ou PID.",
    "parameters": {
        "type": "object",
        "properties": {
            "name_or_pid": {"type": "string", "description": "Nome do processo ou PID."},
            "all_by_name": {"type": "boolean", "description": "Matar todos com esse nome? Default false (só o primeiro).", "default": False},
        },
        "required": ["name_or_pid"],
    },
}


def app_list(filter_str=None):
    try:
        import psutil
        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "create_time"]):
            try:
                info = proc.info
                if filter_str and filter_str.lower() not in info["name"].lower():
                    continue
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu": info["cpu_percent"],
                    "memory": info["memory_percent"],
                    "started": datetime.fromtimestamp(info["create_time"]).isoformat() if info["create_time"] else None,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return tool_result(processes=procs, count=len(procs))
    except Exception as e:
        return tool_error(str(e))


APP_LIST_SCHEMA = {
    "name": "app_list",
    "description": "Listar processos em execução. Opcionalmente filtrar por nome.",
    "parameters": {
        "type": "object",
        "properties": {
            "filter_str": {
                "type": "string",
                "description": "Filtrar processos por nome (substring). Opcional.",
            },
        },
    },
}


# ── System ────────────────────────────────────────────────────────────

def system_info():
    try:
        import platform
        import psutil
        info = {
            "hostname": platform.node(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "arch": platform.machine(),
            "cpu": {
                "cores": psutil.cpu_count(logical=False),
                "logical": psutil.cpu_count(logical=True),
                "usage": psutil.cpu_percent(interval=1),
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
            },
            "disk": {
                "total": psutil.disk_usage("/").total,
                "free": psutil.disk_usage("/").free,
                "percent": psutil.disk_usage("/").percent,
            },
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            "user": os.environ.get("USER", ""),
            "display": os.environ.get("DISPLAY", ""),
        }
        return tool_result(**info)
    except Exception as e:
        return tool_error(str(e))


SYSTEM_INFO_SCHEMA = {
    "name": "system_info",
    "description": "Obter informações do sistema: hostname, CPU, memória, disco, boot, etc.",
    "parameters": {"type": "object", "properties": {}},
}


def system_run(command, timeout=30):
    _ensure()
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return tool_result(
            command=command,
            returncode=result.returncode,
            stdout=result.stdout[:5000],
            stderr=result.stderr[:2000],
        )
    except subprocess.TimeoutExpired:
        return tool_error(f"Comando excedeu timeout de {timeout}s")
    except Exception as e:
        return tool_error(str(e))


SYSTEM_RUN_SCHEMA = {
    "name": "system_run",
    "description": "Executar um comando no shell do sistema (com timeout). Para tarefas administrativas.",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Comando shell a executar."},
            "timeout": {"type": "integer", "description": "Timeout em segundos. Default 30.", "default": 30},
        },
        "required": ["command"],
    },
}


# ── Browser ───────────────────────────────────────────────────────────

def browser_open(url, new_tab=True):
    _ensure()
    try:
        import webbrowser
        webbrowser.open(url, new=1 if new_tab else 0)
        return tool_result(url=url, action="opened")
    except Exception as e:
        return tool_error(str(e))


BROWSER_OPEN_SCHEMA = {
    "name": "browser_open",
    "description": "Abrir URL no navegador padrão.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL a abrir."},
            "new_tab": {"type": "boolean", "description": "Abrir em nova aba? Default true.", "default": True},
        },
        "required": ["url"],
    },
}


# ── Registry ──────────────────────────────────────────────────────────
# Each register() call is at module level so the AST scanner in
# discover_builtin_tools() picks up this file automatically.

def _mk_handler(fn):
    return lambda args, **kw: fn(**{k: v for k, v in args.items()})

registry.register(name="screen_capture", toolset="jarvis", schema=SCREEN_CAPTURE_SCHEMA, handler=_mk_handler(screen_capture), emoji="🖥️")
registry.register(name="screen_ocr", toolset="jarvis", schema=SCREEN_OCR_SCHEMA, handler=_mk_handler(screen_ocr), emoji="🖥️")
registry.register(name="screen_ask", toolset="jarvis", schema=SCREEN_ASK_SCHEMA, handler=_mk_handler(screen_ask), emoji="🖥️")
registry.register(name="mouse_move", toolset="jarvis", schema=MOUSE_MOVE_SCHEMA, handler=_mk_handler(mouse_move), emoji="🖥️")
registry.register(name="mouse_click", toolset="jarvis", schema=MOUSE_CLICK_SCHEMA, handler=_mk_handler(mouse_click), emoji="🖥️")
registry.register(name="mouse_scroll", toolset="jarvis", schema=MOUSE_SCROLL_SCHEMA, handler=_mk_handler(mouse_scroll), emoji="🖥️")
registry.register(name="keyboard_type", toolset="jarvis", schema=KEYBOARD_TYPE_SCHEMA, handler=_mk_handler(keyboard_type), emoji="🖥️")
registry.register(name="keyboard_hotkey", toolset="jarvis", schema=KEYBOARD_HOTKEY_SCHEMA, handler=_mk_handler(keyboard_hotkey), emoji="🖥️")
registry.register(name="clipboard_get", toolset="jarvis", schema=CLIPBOARD_GET_SCHEMA, handler=_mk_handler(clipboard_get), emoji="🖥️")
registry.register(name="clipboard_set", toolset="jarvis", schema=CLIPBOARD_SET_SCHEMA, handler=_mk_handler(clipboard_set), emoji="🖥️")
registry.register(name="file_create", toolset="jarvis", schema=FILE_CREATE_SCHEMA, handler=_mk_handler(file_create), emoji="🖥️")
registry.register(name="file_delete", toolset="jarvis", schema=FILE_DELETE_SCHEMA, handler=_mk_handler(file_delete), emoji="🖥️")
registry.register(name="file_copy", toolset="jarvis", schema=FILE_COPY_SCHEMA, handler=_mk_handler(file_copy), emoji="🖥️")
registry.register(name="file_move", toolset="jarvis", schema=FILE_MOVE_SCHEMA, handler=_mk_handler(file_move), emoji="🖥️")
registry.register(name="file_list", toolset="jarvis", schema=FILE_LIST_SCHEMA, handler=_mk_handler(file_list), emoji="🖥️")
registry.register(name="app_launch", toolset="jarvis", schema=APP_LAUNCH_SCHEMA, handler=_mk_handler(app_launch), emoji="🖥️")
registry.register(name="app_kill", toolset="jarvis", schema=APP_KILL_SCHEMA, handler=_mk_handler(app_kill), emoji="🖥️")
registry.register(name="app_list", toolset="jarvis", schema=APP_LIST_SCHEMA, handler=_mk_handler(app_list), emoji="🖥️")
registry.register(name="system_info", toolset="jarvis", schema=SYSTEM_INFO_SCHEMA, handler=_mk_handler(system_info), emoji="🖥️")
registry.register(name="system_run", toolset="jarvis", schema=SYSTEM_RUN_SCHEMA, handler=_mk_handler(system_run), emoji="🖥️")
registry.register(name="browser_open", toolset="jarvis", schema=BROWSER_OPEN_SCHEMA, handler=_mk_handler(browser_open), emoji="🖥️")

logger.info("Jarvis System Tools loaded: screen, mouse, keyboard, clipboard, file, app, system")
