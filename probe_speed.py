import time, requests, os, subprocess, json
BASE="http://127.0.0.1:11434/v1"
H={"Content-Type":"application/json"}
def call():
    b={"model":"qwen2.5-coder:7b","messages":[{"role":"user","content":"hi"}],"max_tokens":16,"stream":False}
    t=time.time(); r=requests.post(BASE+"/chat/completions",headers=H,json=b,timeout=120); return time.time()-t, r.status_code
# cold
t1,st=call(); print(f"COLD 1st: {t1:.1f}s HTTP {st}")
# warm
t2,st=call(); print(f"WARM 2nd: {t2:.1f}s HTTP {st}")
# ollama ps (GPU)
try:
    out=subprocess.run(["ollama","ps"],capture_output=True,text=True,timeout=10).stdout
    print("ollama ps:\n"+out)
except Exception as e: print("ps err",e)
