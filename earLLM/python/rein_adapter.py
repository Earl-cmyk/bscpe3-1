"""Tiny zero-dependency client for a running Reinitialized Rust server."""
import json
from urllib.request import Request,urlopen

def predict(text,base_url="http://127.0.0.1:8787",timeout=2.0):
    body=json.dumps({"text":text}).encode(); req=Request(base_url.rstrip("/")+"/predict",data=body,headers={"Content-Type":"application/json"},method="POST")
    with urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode())
