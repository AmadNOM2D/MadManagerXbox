import os, requests, yaml

for line in open(os.path.expanduser("~/.hermes/.env")):
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ[k] = v

BASE = "https://inference-api.nousresearch.com/v1"
key = os.environ.get("LLM_API_KEY") or os.environ.get("LM_API_KEY") or os.environ.get("API_SERVER_KEY")
print("using key of len", len(key) if key else 0, "prefix", (key[:7] if key else None))
H = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

for model in ["poolside/laguna-s-2.1:free", "deepseek/deepseek-v4.1-flash-1017", "anthropic/claude-haiku-5.5"]:
    body = {"model": model, "messages": [{"role": "user", "content": "Reply exactly: ok"}], "max_tokens": 8}
    r = requests.post(BASE + "/chat/completions", headers=H, json=body, timeout=30)
    print(f"[{model}] HTTP {r.status_code} -> {r.text[:180]}")
