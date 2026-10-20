import os, requests, json

for line in open(os.path.expanduser("~/.hermes/.env")):
    line = line.strip()
    if line.startswith("API_SERVER_KEY="):
        os.environ["API_SERVER_KEY"] = line.split("=", 1)[1]

k = os.environ["API_SERVER_KEY"]
H = {"Authorization": f"Bearer {k}", "Content-Type": "application/json"}
BASE = "https://inference-api.nousresearch.com/v1"

r = requests.get(BASE + "/models", headers=H, timeout=20)
data = r.json().get("data", [])
print("total models:", len(data))
for m in data:
    print(f"- {m.get('id')}  | ctx {m.get('context_length')} | owned by {m.get('owned_by')}")

print("=== streaming + tool-call test (deepseek-v4.1-flash) ===")
add_tool = {
    "type": "function",
    "function": {
        "name": "add",
        "description": "add two numbers",
        "parameters": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}},
    },
}
body = {
    "model": "deepseek/deepseek-v4.1-flash-1017",
    "messages": [
        {"role": "system", "content": "You are a terse agent."},
        {"role": "user", "content": "What is 2+2? Use the add tool."},
    ],
    "tools": [add_tool],
    "tool_choice": "required",
    "max_tokens": 64,
    "stream": True,
}
resp = requests.post(BASE + "/chat/completions", headers=H, json=body, timeout=30)
print("stream HTTP", resp.status_code)
if resp.status_code == 200:
    n = 0
    for chunk in resp.iter_lines():
        if not chunk:
            continue
        n += 1
        if n <= 6:
            print("  ", chunk[:140])
    print("...(total chunks:", n, ")")
else:
    print(resp.text[:400])
