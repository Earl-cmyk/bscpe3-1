"""Train Reinitialized models.

The deployed neural model is a compact embedding MLP:
    tokens -> embedding lookup -> masked mean pool -> Linear -> ReLU -> Linear
It is intentionally small and easy to reproduce in Rust.
"""
import argparse, json, os, time
import numpy as np
from dataset import load_jsonl, DATA_DIR

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODELS_DIR = os.path.join(ROOT, "models")


def load_split(name):
    return load_jsonl(os.path.join(DATA_DIR, f"{name}.jsonl"))


def train_tfidf_logreg(seed, C=2.0):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    train = load_split("train")
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1)),
        ("clf", LogisticRegression(max_iter=2000, C=C, random_state=seed)),
    ])
    pipe.fit([r["text"] for r in train], [r["intent"] for r in train])
    return pipe, {"C": C, "ngram_range": [1, 2], "max_iter": 2000}


def train_embedding_mlp(seed, embedding_dim=32, hidden_dim=64, epochs=1200, lr=0.05, weight_decay=1e-4):
    from tokenizer import Vocabulary
    train = load_split("train")
    texts = [r["text"] for r in train]
    labels = sorted(set(r["intent"] for r in train))
    label_to_id = {x: i for i, x in enumerate(labels)}
    vocab = Vocabulary.build(texts, min_freq=1)
    token_ids = [vocab.encode(t) for t in texts]
    V, D, H, C = len(vocab), embedding_dim, hidden_dim, len(labels)
    rng = np.random.default_rng(seed)
    E = rng.normal(0, 0.05, (V, D)).astype(np.float32)
    W1 = rng.normal(0, np.sqrt(2 / D), (D, H)).astype(np.float32)
    b1 = np.zeros(H, np.float32)
    W2 = rng.normal(0, np.sqrt(2 / H), (H, C)).astype(np.float32)
    b2 = np.zeros(C, np.float32)
    y = np.array([label_to_id[r["intent"]] for r in train], dtype=np.int64)

    # Adam keeps this tiny full-batch model stable as the dataset grows.
    params = [E, W1, b1, W2, b2]
    m = [np.zeros_like(p) for p in params]; v = [np.zeros_like(p) for p in params]
    beta1, beta2, eps = 0.9, 0.999, 1e-8

    def forward(ids):
        pooled = np.zeros((len(ids), D), np.float32)
        for i, seq in enumerate(ids):
            real = [t for t in seq if t != 0]
            if real: pooled[i] = E[real].mean(axis=0)
        z1 = pooled @ W1 + b1
        h = np.maximum(z1, 0)
        logits = h @ W2 + b2
        return pooled, z1, h, logits

    best = None; best_acc = -1.0
    val = load_split("validation")
    val_ids = [vocab.encode(r["text"]) for r in val]
    val_y = np.array([label_to_id[r["intent"]] for r in val])
    for step in range(1, epochs + 1):
        pooled, z1, h, logits = forward(token_ids)
        z = logits - logits.max(axis=1, keepdims=True)
        probs = np.exp(z); probs /= probs.sum(axis=1, keepdims=True)
        loss = -np.log(probs[np.arange(len(y)), y] + 1e-9).mean()
        grad = probs; grad[np.arange(len(y)), y] -= 1; grad /= len(y)
        gW2 = h.T @ grad + weight_decay * W2
        gb2 = grad.sum(0)
        gh = grad @ W2.T; gz1 = gh * (z1 > 0)
        gW1 = pooled.T @ gz1 + weight_decay * W1
        gb1 = gz1.sum(0)
        gp = gz1 @ W1.T
        gE = np.zeros_like(E)
        for i, seq in enumerate(token_ids):
            real = [t for t in seq if t != 0]
            if real:
                np.add.at(gE, real, gp[i] / len(real))
        grads = [gE, gW1, gb1, gW2, gb2]
        for j, (p, g) in enumerate(zip(params, grads)):
            m[j] = beta1*m[j] + (1-beta1)*g; v[j] = beta2*v[j] + (1-beta2)*(g*g)
            mh = m[j] / (1-beta1**step); vh = v[j] / (1-beta2**step)
            p -= lr * mh / (np.sqrt(vh)+eps)
        if step == 1 or step % 100 == 0 or step == epochs:
            _, _, _, vl = forward(val_ids)
            va = float(np.mean(np.argmax(vl, axis=1) == val_y))
            print(f"  epoch {step:4d} loss={loss:.4f} val_acc={va:.4f}")
            if va > best_acc:
                best_acc = va
                best = [p.copy() for p in params]
    if best is not None:
        E, W1, b1, W2, b2 = best
    return {"type":"embedding_mlp", "E":E, "W1":W1, "b1":b1, "W2":W2, "b2":b2,
            "vocab":vocab, "labels":labels, "label_to_id":label_to_id, "embedding_dim":D,
            "hidden_dim":H}, {"embedding_dim":D,"hidden_dim":H,"epochs":epochs,"lr":lr,"weight_decay":weight_decay,"vocab_size":V}


def main():
    p=argparse.ArgumentParser(); p.add_argument("--model",choices=["tfidf_logreg","embedding_mlp"],default="embedding_mlp")
    p.add_argument("--seed",type=int,default=42); p.add_argument("--epochs",type=int,default=1200); p.add_argument("--out")
    a=p.parse_args(); os.makedirs(MODELS_DIR,exist_ok=True)
    meta=json.load(open(os.path.join(DATA_DIR,"dataset_meta.json"))) if os.path.exists(os.path.join(DATA_DIR,"dataset_meta.json")) else {}
    start=time.time()
    if a.model=="tfidf_logreg":
        model,h=train_tfidf_logreg(a.seed); out=a.out or os.path.join(MODELS_DIR,"tfidf_logreg.joblib")
        import joblib; joblib.dump(model,out)
    else:
        model,h=train_embedding_mlp(a.seed,epochs=a.epochs); out=a.out or os.path.join(MODELS_DIR,"embedding_mlp.npz")
        np.savez(out,E=model["E"],W1=model["W1"],b1=model["b1"],W2=model["W2"],b2=model["b2"],labels=np.array(model["labels"]))
        model["vocab"].save(os.path.join(MODELS_DIR,"embedding_mlp.vocab.json"))
    run={"model_type":a.model,"seed":a.seed,"dataset_version":meta.get("dataset_version"),"dataset_source_hash":meta.get("source_hash"),"hyperparameters":h,"train_time_seconds":round(time.time()-start,3),"artifact_path":os.path.relpath(out,ROOT)}
    with open(out+".meta.json","w") as f: json.dump(run,f,indent=2)
    print(json.dumps(run,indent=2))

if __name__=="__main__": main()
