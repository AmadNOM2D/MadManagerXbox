"""
Mad Manager — live agent backend (runs on Mark's Mac).

Engine: Ollama (qwen2.5-coder:7b) via the OpenAI-compatible /v1 API.
Transport: WebSocket (consumed by the Xbox UWP WebView client).

Verified fact driving the design:
  qwen2.5-coder:7b via Ollama /v1 does NOT emit OpenAI delta.tool_calls.
  It returns the tool invocation as a JSON blob INSIDE message.content, e.g.
    {"name":"bash","arguments":{"cmd":"echo hello"}}
  => we stream content deltas as live text, and at turn-end JSON-parse content
     into a tool call; on success we execute the tool locally and continue.
"""
import asyncio, json, os, subprocess, re, pathlib
import httpx, uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/v1")
MODEL = os.environ.get("MM_MODEL", "qwen2.5-coder:7b")
PORT = int(os.environ.get("MM_PORT", "8765"))
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
SYSTEM_PROMPT = (ROOT / "SYSTEM_PROMPT.md").read_text().strip()
WEB_DIR = ROOT / "web"

# ---- tools the agent may call (executed locally = full local tool access) ----
TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command on Mark's Mac. Returns stdout+stderr+exit. Use for filesystem ops, deploys (e.g. Xbox Device Portal curl), social CLIs, WHBQ scripts, git, ffmpeg, anything reachable from the shell.",
            "parameters": {"type": "object", "properties": {"cmd": {"type": "string", "description": "shell command to execute"}}, "required": ["cmd"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch a URL and return its text content (truncated).",
            "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file at an absolute path.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write text content to an absolute path (creates parent dirs, overwrites).",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
        },
    },
]
TOOLS = {t["function"]["name"]: t["function"] for t in TOOLS_SPEC}

# Safety: block only catastrophically self-destructive commands. The agent runs as
# non-root, so it can't poweroff/reboot/sudo anyway, but guard the obvious landmines.
_DENY = re.compile(r"\brm\s+-rf\s+/(?:\s|$)|mkfs|sudo\b|\bdd\s+if=/dev/", re.I)

def _bash_cmd(cmd: str) -> str:
    if _DENY.search(cmd):
        return "BLOCKED: command denied by safety policy."
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        out = p.stdout
        err = p.stderr.strip()
        if err:
            out += f"\n[stderr {p.returncode}]: {err}"
        return (out.strip()[:4000] or f"(exit {p.returncode}, no output)")
    except subprocess.TimeoutExpired:
        return "ERROR: command timed out after 15s."
    except Exception as e:
        return f"ERROR: {e}"

def parse_tool_call(content: str):
    """Return {"name":..., "arguments":{...}} if content is a tool call, else None."""
    if not content:
        return None
    c = content.strip()
    if c.startswith("```"):
        c = re.sub(r"^```[a-zA-Z]*\n", "", c)
        c = re.sub(r"\n```$", "", c)
        c = c.strip()
    try:
        obj = json.loads(c)
    except Exception:
        return None
    if isinstance(obj, dict) and "name" in obj and "arguments" in obj:
        return obj
    if isinstance(obj, list) and obj and isinstance(obj[0], dict) and "name" in obj[0] and "arguments" in obj[0]:
        return obj[0]
    return None

def normalize_args(arguments):
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except Exception:
            return None
    if not isinstance(arguments, dict):
        return None
    return arguments

async def execute_tool(name: str, arguments):
    args = normalize_args(arguments)
    if args is None:
        return "ERROR: malformed tool arguments"
    if name == "bash":
        return await asyncio.get_event_loop().run_in_executor(None, _bash_cmd, args.get("cmd", ""))
    if name == "web_fetch":
        try:
            async with httpx.AsyncClient(timeout=25, follow_redirects=True) as c:
                r = await c.get(args.get("url", ""), headers={"User-Agent": "MadManager/1.0"})
                return r.text[:6000]
        except Exception as e:
            return f"ERROR: {e}"
    if name == "read_file":
        try:
            return pathlib.Path(args.get("path", "")).read_text(errors="replace")[:8000]
        except Exception as e:
            return f"ERROR: {e}"
    if name == "write_file":
        try:
            p = pathlib.Path(args.get("path", ""))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(args.get("content", ""))
            return f"wrote {p}"
        except Exception as e:
            return f"ERROR: {e}"
    return f"unknown tool: {name}"

# ---- WebSocket manager (single active Xbox client) ----
class Manager:
    def __init__(self):
        self.ws: WebSocket | None = None
    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.ws = ws
    def disconnect(self, ws: WebSocket):
        if self.ws is ws:
            self.ws = None
    async def send(self, payload: dict):
        if self.ws is None:
            return
        await self.ws.send_text(json.dumps(payload))

mgr = Manager()
MESSAGES: list = []  # conversation history (single global agent session)

async def run_agent_turn(user_msg: str):
    """Run one agent turn (may loop over multiple tool calls). Stream to the client."""
    MESSAGES.append({"role": "user", "content": user_msg})
    await mgr.send({"type": "start"})
    # Bias a weak local model toward tool use on action-oriented prompts.
    needs_action = bool(re.search(
        r"\b(run|execute|do|deploy|post|make|create|write|edit|open|curl|send|"
        r"build|compile|install|check|status|list|show|whbq|social|email|xbox|"
        r"phone|tweet|upload|publish|report|summary|what time|date)\b",
        user_msg, re.I))
    while True:
        body = {
            "model": MODEL,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + MESSAGES[1:],
            "tools": TOOLS_SPEC,
            "stream": True,
            "max_tokens": 1024,
            "temperature": 0.2,
            "tool_choice": "required" if needs_action else "auto",
        }
        final = ""
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", OLLAMA_URL + "/chat/completions", json=body) as resp:
                if resp.status_code != 200:
                    txt = await resp.aread()
                    await mgr.send({"type": "delta", "content": f"\n[Ollama HTTP {resp.status_code}: {txt[:120]}]"})
                    await mgr.send({"type": "end"})
                    MESSAGES.append({"role": "assistant", "content": f"[Ollama error {resp.status_code}]"})
                    return
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    if line == "data: [DONE]":
                        continue
                    try:
                        chunk = json.loads(line[6:])
                    except Exception:
                        continue
                    delta = chunk.get("choices", [{}])[0].get("delta", {}) if chunk.get("choices") else {}
                    content = delta.get("content") or ""
                    if content:
                        final += content
                        await mgr.send({"type": "delta", "content": content})
                    if chunk.get("choices") and chunk["choices"][0].get("finish_reason") == "stop":
                        break
        tc = parse_tool_call(final)
        if tc:
            name, args = tc["name"], tc.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            arg_summary = ""
            if isinstance(args, dict) and name == "bash":
                arg_summary = args.get("cmd", "")
            elif isinstance(args, dict) and name == "web_fetch":
                arg_summary = args.get("url", "")
            else:
                arg_summary = json.dumps(args)[:160]
            await mgr.send({"type": "tool", "name": name, "arg": arg_summary})
            result = await execute_tool(name, args)
            await mgr.send({"type": "tool_result", "name": name, "content": str(result)[:3000]})
            MESSAGES.append({"role": "assistant", "content": final})
            MESSAGES.append({"role": "tool", "content": str(result)})
            await mgr.send({"type": "tool_done"})
            # loop: let the model continue with the tool result
            continue
        else:
            MESSAGES.append({"role": "assistant", "content": final})
            await mgr.send({"type": "end"})
            # cap history
            if len(MESSAGES) > 24:
                MESSAGES[:] = MESSAGES[-22:]
            return

app = FastAPI()

@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "model": MODEL})

@app.get("/config.json")
async def config():
    return JSONResponse({"apiBase": f"ws://192.168.12.242:{PORT}"})

@app.get("/")
async def index():
    return FileResponse(str(WEB_DIR / "index.html"))

app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web")

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await mgr.connect(ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            if msg.get("type") == "ping":
                await mgr.send({"type": "pong"})
                continue
            if msg.get("type") == "chat":
                await run_agent_turn(msg.get("content", ""))
            elif msg.get("type") == "reset":
                MESSAGES.clear()
                await mgr.send({"type": "reset_done"})
    except WebSocketDisconnect:
        mgr.disconnect(ws)

if __name__ == "__main__":
    # ensure ollama is running
    try:
        subprocess.run(["ollama", "serve"], capture_output=True, timeout=3)
    except Exception:
        pass
    uvicorn.run(app, host="0.0.0.0", port=PORT)
