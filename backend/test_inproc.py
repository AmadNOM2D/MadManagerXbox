import asyncio, json, subprocess, importlib.util, time

subprocess.run(["ollama", "serve"], capture_output=True, timeout=3)

spec = importlib.util.spec_from_file_location("mmapp", "/Users/mw/xbox-agent/backend/app.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

collected = []
async def fake_send(payload):
    collected.append(payload)
    t = payload.get("type")
    if t == "delta":
        print(payload.get("content",""), end="", flush=True)
    elif t in ("start", "end", "tool_done", "reset_done", "pong"):
        print(f"\n[{t}]")
    elif t == "tool":
        print(f"\n[tool:{payload.get('name')} arg={payload.get('arg','')[:80]}]")
    elif t == "tool_result":
        print(f"\n[result:{payload.get('content','')[:200]}]")

m.mgr.send = fake_send

print("=== Turn 1: ask time via bash ===")
asyncio.run(m.run_agent_turn("What time is it on this Mac? Use the bash tool to run `date +%s` and report the epoch number."))
print(f"\n(total events: {len(collected)})")

print("\n=== Turn 2: verify memory of turn 1 (continuation) ===")
asyncio.run(m.run_agent_turn("Earlier you gave me an epoch. Is that number even or odd? Don't re-run date."))
print(f"\n(total events: {len(collected)})")
