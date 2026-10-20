import requests, json

bash_tool = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run a shell command. Returns stdout.",
        "parameters": {
            "type": "object",
            "properties": {"cmd": {"type": "string", "description": "the shell command to run"}},
            "required": ["cmd"],
        },
    },
}

# --- 1) Native /api/chat non-streaming: confirm structured tool_calls ---
body = {
    "model": "qwen2.5-coder:7b",
    "messages": [{"role": "user", "content": "Run the bash tool to print 'hello-from-tool'."}],
    "tools": [bash_tool],
    "stream": False,
}
r = requests.post("http://127.0.0.1:11434/api/chat", json=body, timeout=60)
print("native non-stream HTTP", r.status_code)
obj = r.json()
m = obj.get("message", {})
print("native message keys:", list(m.keys()))
print("native content:", repr(m.get("content"))[:200])
print("native tool_calls:", json.dumps(m.get("tool_calls"))[:300])

# --- 2) /v1 chat non-streaming: confirm OpenAI tool_calls shape ---
body2 = {
    "model": "qwen2.5-coder:7b",
    "messages": [{"role": "user", "content": "Run the bash tool to print 'hello-from-tool'."}],
    "tools": [bash_tool],
    "stream": False,
}
r2 = requests.post("http://127.0.0.1:11434/v1/chat/completions",
                   headers={"Content-Type": "application/json"}, json=body2, timeout=60)
print("\nv1 non-stream HTTP", r2.status_code)
j = r2.json()
ch = j.get("choices", [{}])[0]
msg = ch.get("message", {})
print("v1 message keys:", list(msg.keys()))
print("v1 content:", repr(msg.get("content"))[:200])
print("v1 tool_calls:", json.dumps(msg.get("tool_calls"))[:300])
