import requests, json

bash_tool = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run a shell command and return its stdout.",
        "parameters": {
            "type": "object",
            "properties": {"cmd": {"type": "string", "description": "shell command"}},
            "required": ["cmd"],
        },
    },
}
body = {
    "model": "qwen2.5-coder:7b",
    "messages": [{"role": "user", "content": "What time is it? Use the bash tool to run `date +%s`."}],
    "tools": [bash_tool],
    "tool_choice": "required",
    "stream": True,
    "max_tokens": 256,
}
resp = requests.post("http://127.0.0.1:11434/v1/chat/completions", json=body, timeout=60)
print("HTTP", resp.status_code)
seen_final = None
for line in resp.iter_lines():
    if not line:
        continue
    if not line.startswith(b"data: "):
        continue
    obj = json.loads(line[6:])
    choice = obj.get("choices", [{}])[0]
    delta = choice.get("delta", {})
    finish = choice.get("finish_reason")
    tc = delta.get("tool_calls")
    keys = list(delta.keys())
    if tc:
        print("TOOL_CHUNK:", json.dumps(tc)[:300])
    if finish:
        seen_final = choice
        print("FINISH:", finish)
if seen_final:
    print("FINAL delta:", json.dumps(seen_final.get("delta", {}))[:400])
