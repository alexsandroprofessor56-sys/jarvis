#!/usr/bin/env python3
"""
JARVIS HTTP API Bridge - Permite Hermes chamar JARVIS para ações físicas
Roda em background na porta 8765
"""
import os
import sys
import threading
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

from core.orchestrator import Orchestrator


app = FastAPI(title="JARVIS Physical Bridge", version="1.0")
orchestrator = None


class SpeakRequest(BaseModel):
    text: str


class CommandRequest(BaseModel):
    command: str


class MouseMoveRequest(BaseModel):
    x: int
    y: int


class MouseClickRequest(BaseModel):
    button: str = "left"


class TypeTextRequest(BaseModel):
    text: str


class HotkeyRequest(BaseModel):
    keys: List[str]


class ScreenshotRequest(BaseModel):
    pass


class AnalyzeScreenRequest(BaseModel):
    pass


class OpenAppRequest(BaseModel):
    app_name: str


class RunCommandRequest(BaseModel):
    command: str


class WebOpenRequest(BaseModel):
    url: str


class WebFetchRequest(BaseModel):
    url: str


def get_orchestrator():
    global orchestrator
    if orchestrator is None:
        orchestrator = Orchestrator()
        orchestrator.start()
    return orchestrator


@app.get("/health")
async def health():
    return {"status": "ok", "service": "jarvis-bridge"}


@app.post("/speak")
async def speak(req: SpeakRequest):
    try:
        o = get_orchestrator()
        o.tts.speak_async(req.text)
        return {"status": "ok", "message": "Falando..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process_text")
async def process_text(req: CommandRequest):
    try:
        o = get_orchestrator()
        o.process_text(req.command)
        return {"status": "ok", "message": "Comando processado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mouse/move")
async def mouse_move(req: MouseMoveRequest):
    try:
        o = get_orchestrator()
        result = o.tools.execute("mouse_move", x=req.x, y=req.y)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mouse/click")
async def mouse_click(req: MouseClickRequest):
    try:
        o = get_orchestrator()
        result = o.tools.execute("mouse_click", button=req.button)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mouse/scroll")
async def mouse_scroll(clicks: int = 3):
    try:
        o = get_orchestrator()
        result = o.tools.execute("mouse_scroll", clicks=clicks)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/keyboard/type")
async def keyboard_type(req: TypeTextRequest):
    try:
        o = get_orchestrator()
        result = o.tools.execute("type_text", text=req.text)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/keyboard/hotkey")
async def keyboard_hotkey(req: HotkeyRequest):
    try:
        o = get_orchestrator()
        result = o.tools.execute("keyboard_hotkey", keys=req.keys)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/screen/screenshot")
async def screenshot(req: ScreenshotRequest):
    try:
        o = get_orchestrator()
        result = o.tools.execute("screenshot")
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/screen/analyze")
async def analyze_screen(req: AnalyzeScreenRequest):
    try:
        o = get_orchestrator()
        result = o.tools.execute("analyze_screen")
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/app/open")
async def open_app(req: OpenAppRequest):
    try:
        o = get_orchestrator()
        result = o.tools.execute("open_app", app_name=req.app_name)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/shell/run")
async def run_command(req: RunCommandRequest):
    try:
        o = get_orchestrator()
        result = o.tools.execute("run_command", command=req.command)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/web/open")
async def web_open(req: WebOpenRequest):
    try:
        o = get_orchestrator()
        result = o.tools.execute("web_open", url=req.url)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/web/fetch")
async def web_fetch(req: WebFetchRequest):
    try:
        o = get_orchestrator()
        result = o.tools.execute("web_fetch", url=req.url)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools")
async def list_tools():
    o = get_orchestrator()
    return {"tools": list(o.tools.tools.keys())}


def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="warning")


def start_api_thread():
    t = threading.Thread(target=run_api, daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    print("Iniciando JARVIS API Bridge na porta 8765...")
    run_api()