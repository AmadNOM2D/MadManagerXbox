import os, requests, json
for line in open(os.path.expanduser("~/.hermes/.env")):
    line=line.strip()
    if line.startswith("API_SERVER_KEY="):
        os.environ["API_SERVER_KEY"]=line.split("=",1)[1]
key=os.environ["API_SERVER_KEY"]
H={"Authorization":f"Bearer {key}","Content-Type":"application/json"}
BASE="https://inference-api.nousresearch.com/v1"
for model in ["poolside/laguna-s-2.1:free","upstage/solar-mini4:free","anthropic/claude-haiku-5.5","deepseek/deepseek-v4-flash-0731"]:
    body={"model":model,"messages":[{"role":"user","content":"Reply exactly: ok"}],"max_tokens":16,"stream":False}
    try:
        r=requests.post(BASE+"/chat/completions",headers=H,json=body,timeout=30)
        s=r.text[:220]
        if r.status_code==200:
            d=r.json()
            print(f"[OK ] {model}: {d['choices'][0]['message'].get('content','?')[:60]!r}")
        else:
            print(f"[ERR] {model}: HTTP {r.status_code} {s}")
    except Exception as e:
        print(f"[EXC] {model}: {e}")
