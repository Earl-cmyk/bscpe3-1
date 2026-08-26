import json, os, sys, numpy as np
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),"..")); MODELS=os.path.join(ROOT,"models")
sys.path.insert(0,os.path.dirname(__file__))
from tokenizer import Vocabulary

def main():
    npz=np.load(os.path.join(MODELS,"embedding_mlp.npz")); vocab=Vocabulary.load(os.path.join(MODELS,"embedding_mlp.vocab.json"))
    meta_path=os.path.join(MODELS,"embedding_mlp.npz.meta.json"); meta=json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    artifact={"format_version":2,"model_type":"embedding_mlp_relu","embedding_dim":int(npz["E"].shape[1]),"hidden_dim":int(npz["W1"].shape[1]),"vocab_size":int(npz["E"].shape[0]),"num_labels":int(npz["W2"].shape[1]),"labels":[str(x) for x in npz["labels"]],"vocab":vocab.token_to_id,"E":npz["E"].tolist(),"W1":npz["W1"].tolist(),"b1":npz["b1"].tolist(),"W2":npz["W2"].tolist(),"b2":npz["b2"].tolist(),"training_meta":meta}
    out=os.path.join(MODELS,"model_artifact.json")
    with open(out,"w",encoding="utf8") as f: json.dump(artifact,f,separators=(",",":"))
    print(f"Exported {out}: {artifact['vocab_size']} vocab, {artifact['embedding_dim']}D, {artifact['hidden_dim']} hidden, {artifact['num_labels']} labels")
if __name__=="__main__": main()
