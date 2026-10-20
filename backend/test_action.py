import asyncio, json, subprocess, importlib.util, os

subprocess.run(["ollama", "serve"], capture_output=True, timeout=3)
os.environ["MM_MODEL"] = os.environ.get("MM_MODEL", "qwen2.5-coder:7b")

spec = importlib.util.spec_from_file_location("mmapp", "/Users/mw/xbox-agent/backend/app.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

events = []
async def fake_send(payload):
    events.append(payload)
    t = payload.get("type")
    if t == "delta":
        print(payload.get("content", ""), end="", flush=True)
    elif t in ("start", "end", "tool_done"):
        print(f"\n[{t}]")
    elif t == "tool":
        print(f"\n[tool:{payload.get('name')} :: {payload.get('arg','')[:120]}]")
    elif t == "tool_result":
        print(f"\n[result: {payload.get('content','')[:200]}]")

m.mgr.send = fake_send
print("=== ACTION REQUEST (should call bash, run date +%s) ===")
asyncio.run(m.run_agent_turn(None, "What time is it? Run `date +%s` to get the epoch and report it."))
print(f"\n(events: {len(events)})")
