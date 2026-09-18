"""One-command local verification for the Python side of Reinitialized."""
import json, os, subprocess, sys
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
cmds=[
 [sys.executable,"python/dataset.py","--version","v4","--seed","42"],
 [sys.executable,"python/train.py","--model","embedding_mlp","--epochs","1000"],
 [sys.executable,"python/evaluate.py","--model","embedding_mlp","--split","test"],
 [sys.executable,"python/export.py"],
 [sys.executable,"python/quickcheck.py"],
]
for c in cmds:
 print("$ "+" ".join(c)); subprocess.run(c,cwd=ROOT,check=True)
with open(os.path.join(ROOT,"models","model_artifact.json"),encoding="utf8") as f:a=json.load(f)
assert a["format_version"]==2 and a["model_type"]=="embedding_mlp_relu"
print("Reinitialized Python verification: PASS")
print("Rust verification requires a Rust toolchain: cd rust && cargo test && cargo build --release")
