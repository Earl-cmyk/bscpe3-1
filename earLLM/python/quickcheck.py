"""Smoke test the exact Rein-style requests without a web server."""
import os,sys
sys.path.insert(0,os.path.dirname(__file__))
from evaluate import load_embedding_mlp,predict_embedding_mlp
from entities import extract_entities
cases=[
 ("Can you mark LCD as having no class tomorrow?","MARK_NO_CLASS"),
 ("Please add a deadline for my HDL class tomorrow at 6 PM titled lab report.","CREATE_DEADLINE"),
 ("Record a 500 peso deposit for HDL for printing materials.","RECORD_DEPOSIT"),
 ("Could you remove deadline 7?","DELETE_DEADLINE"),
 ("How do I use 3's complement?","LEARN_TOPIC"),
]
m=load_embedding_mlp();
for text,expected in cases:
 p,c=predict_embedding_mlp(m,[text]); intent=p[0]; print(f"{text}\n  intent={intent} expected={expected} confidence={c[0]:.3f} entities={extract_entities(text,intent)}")
