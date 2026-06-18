#!/usr/bin/env python3
"""Hermes Tool Proxy - expõe todas as ferramentas do Hermes via HTTP para o Jarvis."""
import os
import sys
import json
import logging
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
HERMES_AGENT = HERMES_HOME / "hermes-agent"

sys.path.insert(0, str(HERMES_AGENT))

os.environ.setdefault("HERMES_HOME", str(HERMES_HOME))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("hermes_proxy")

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
import uvicorn

from tools.registry import discover_builtin_tools, registry
from model_tools import get_tool_definitions, handle_function_call
from toolsets import resolve_toolset

tool_schemas: list = []
tool_map: dict = {}


class ToolCallRequest(BaseModel):
    args: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global tool_schemas, tool_map
    logger.info("Inicializando Hermes Tool Proxy...")
    discover_builtin_tools()
    all_tools = get_tool_definitions(quiet_mode=True)
    tool_schemas = all_tools
    tool_map = {t["function"]["name"]: t["function"] for t in all_tools}
    logger.info(f"{len(all_tools)} ferramentas carregadas")
    yield


app = FastAPI(title="Hermes Tool Proxy", version="1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "tools_count": len(tool_schemas)}


@app.get("/hermes/tools")
async def list_tools():
    return {
        "count": len(tool_schemas),
        "tools": [
            {
                "name": t["function"]["name"],
                "description": t["function"].get("description", ""),
                "parameters": t["function"].get("parameters", {}),
            }
            for t in tool_schemas
        ],
    }


@app.get("/hermes/tools/{name}")
async def get_tool(name: str):
    schema = tool_map.get(name)
    if not schema:
        raise HTTPException(404, f"Ferramenta '{name}' não encontrada")
    return schema


@app.post("/hermes/tools/{name}")
async def call_tool(name: str, req: ToolCallRequest):
    if name not in tool_map:
        raise HTTPException(404, f"Ferramenta '{name}' não encontrada")
    try:
        result = handle_function_call(name, req.args)
        try:
            return {"status": "ok", "result": json.loads(result)}
        except (json.JSONDecodeError, TypeError):
            return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(500, str(e))


def run():
    uvicorn.run(app, host="127.0.0.1", port=8766, log_level="info")


if __name__ == "__main__":
    run()
