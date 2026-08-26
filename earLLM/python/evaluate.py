"""
evaluate.py

Evaluation pipeline (section 22) for Reinitialized intent classifiers.

Reports, per split:
    - accuracy
    - macro precision / recall / F1
    - per-intent precision / recall / F1
    - confusion matrix

Also runs error analysis (section 23): every misclassified example is
printed with input / expected / predicted, so failures can be traced back
to specific confusing intent pairs.

Usage:
    python python/evaluate.py --model tfidf_logreg --split test
    python python/evaluate.py --model embedding_mlp --split test
"""

import argparse
import json
import os

import numpy as np

from dataset import load_jsonl, DATA_DIR
from entities import extract_entities, SUPPORTED_ENTITY_TYPES

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))

# entities.py can produce topic/title/description, but title and description
# are open-ended, heuristic extractors (not a closed lexicon like course/topic)
# and are noticeably weaker. They're still scored -- excluding them would hide
# real weaknesses -- but they're broken out separately in the report so a
# strong overall entity F1 doesn't quietly average over two soft fields.
OPEN_ENDED_ENTITY_TYPES = {"title", "description"}


def load_tfidf_logreg():
    import joblib
    return joblib.load(os.path.join(MODELS_DIR, "tfidf_logreg.joblib"))


def predict_tfidf_logreg(model, texts):
    preds = model.predict(texts)
    probs = model.predict_proba(texts)
    confidences = probs.max(axis=1)
    return list(preds), list(confidences)


def load_embedding_mlp():
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from tokenizer import Vocabulary
    npz = np.load(os.path.join(MODELS_DIR, "embedding_mlp.npz"))
    vocab = Vocabulary.load(os.path.join(MODELS_DIR, "embedding_mlp.vocab.json"))
    return {"E":npz["E"],"W1":npz["W1"],"b1":npz["b1"],"W2":npz["W2"],"b2":npz["b2"],"labels":list(npz["labels"]),"vocab":vocab}

def predict_embedding_mlp(model,texts):
    E,W1,b1,W2,b2=model["E"],model["W1"],model["b1"],model["W2"],model["b2"]
    vocab,labels=model["vocab"],model["labels"]
    preds=[]; confs=[]
    for text in texts:
        ids=[i for i in vocab.encode(text) if i!=0]
        if not ids:
            preds.append("UNKNOWN"); confs.append(0.0); continue
        pooled=E[ids].mean(axis=0); h=np.maximum(pooled@W1+b1,0); logits=h@W2+b2; z=logits-logits.max(); probs=np.exp(z); probs/=probs.sum(); idx=int(np.argmax(probs)); c=float(probs[idx])
        if all(i==1 for i in ids) or c<0.35: preds.append("UNKNOWN"); confs.append(c)
        else: preds.append(labels[idx]); confs.append(c)
    return preds,confs


def precision_recall_f1(y_true, y_pred, labels):
    metrics = {}
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        metrics[label] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}
    return metrics


def confusion_matrix(y_true, y_pred, labels):
    idx = {l: i for i, l in enumerate(labels)}
    matrix = [[0] * len(labels) for _ in labels]
    for t, p in zip(y_true, y_pred):
        matrix[idx[t]][idx[p]] += 1
    return matrix


def print_confusion_matrix(matrix, labels, min_count=1):
    print("\nConfusion matrix (row=expected, col=predicted; only nonzero off-diagonal shown):")
    for i, row in enumerate(matrix):
        for j, count in enumerate(row):
            if i != j and count >= min_count:
                print(f"  {labels[i]:<24} -> predicted {labels[j]:<24} x{count}")


def evaluate_entities(records, predictions):
    """Field-by-field entity precision/recall/F1 (spec section 22).

    `predictions` is the list of predicted intents (already computed by the
    caller for the intent-accuracy pass) -- entities are extracted with
    entities.extract_entities(text, predicted_intent), i.e. using the
    *predicted* intent, since that's what the system would actually have
    available at inference time (a wrong intent can cascade into wrong or
    missing entities, and that cascade is exactly what this metric should
    capture, not hide by cheating with the gold intent).

    Ground truth records may carry entity fields nothing in entities.py
    extracts yet. Those are still counted here (title/description) but
    flagged as open-ended/heuristic in the printed report and the saved
    JSON, rather than silently pretending they're as reliable as the
    closed-vocabulary fields (course/topic) or regex fields (date/time/
    amount/deadline_id).
    """
    per_type = {t: {"tp": 0, "fp": 0, "fn": 0} for t in SUPPORTED_ENTITY_TYPES}

    for record, predicted_intent in zip(records, predictions):
        gold = record.get("entities", {}) or {}
        pred = extract_entities(record["text"], predicted_intent)

        for etype in SUPPORTED_ENTITY_TYPES:
            has_gold = etype in gold
            has_pred = etype in pred
            if has_gold and has_pred and gold[etype] == pred[etype]:
                per_type[etype]["tp"] += 1
            else:
                if has_pred:
                    per_type[etype]["fp"] += 1
                if has_gold:
                    per_type[etype]["fn"] += 1

    metrics = {}
    total_tp = total_fp = total_fn = 0
    for etype, counts in per_type.items():
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
        total_tp += tp
        total_fp += fp
        total_fn += fn
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        metrics[etype] = {
            "precision": precision, "recall": recall, "f1": f1,
            "support": tp + fn,
            "open_ended": etype in OPEN_ENDED_ENTITY_TYPES,
        }

    micro_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0.0
    micro_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0.0
    micro_f1 = (
        2 * micro_precision * micro_recall / (micro_precision + micro_recall)
        if (micro_precision + micro_recall) else 0.0
    )

    return {
        "per_type": metrics,
        "micro_precision": micro_precision,
        "micro_recall": micro_recall,
        "micro_f1": micro_f1,
        "excluded_fields": [],
        "open_ended_fields": sorted(OPEN_ENDED_ENTITY_TYPES),
    }


def evaluate_end_to_end(records, predictions):
    """success = intent correct AND every ground-truth entity present and
    exactly correct (spec section 22). This is intentionally stricter than
    both intent accuracy and entity F1 individually: a record only counts
    if the *whole* pipeline (intent -> entities -> tool call) would have
    produced the right result.
    """
    successes = 0
    for record, predicted_intent in zip(records, predictions):
        if predicted_intent != record["intent"]:
            continue
        gold = record.get("entities", {}) or {}
        pred = extract_entities(record["text"], predicted_intent)
        if pred == gold:
            successes += 1
    return successes / len(records) if records else 0.0


def error_analysis(records, y_pred, confidences):
    errors = [
        (r["text"], r["intent"], p, c)
        for r, p, c in zip(records, y_pred, confidences)
        if r["intent"] != p
    ]
    if not errors:
        print("\nNo errors on this split.")
        return
    print(f"\nError analysis ({len(errors)} misclassified examples):")
    for text, expected, predicted, conf in errors:
        print(f"  Input:     \"{text}\"")
        print(f"  Expected:  {expected}")
        print(f"  Predicted: {predicted}  (confidence={conf:.2f})")
        print()


def main():
    parser = argparse.ArgumentParser(description="Evaluate a Reinitialized intent classifier")
    parser.add_argument("--model", choices=["tfidf_logreg", "embedding_mlp"], default="tfidf_logreg")
    parser.add_argument("--split", choices=["train", "validation", "test"], default="test")
    args = parser.parse_args()

    records = load_jsonl(os.path.join(DATA_DIR, f"{args.split}.jsonl"))
    texts = [r["text"] for r in records]
    y_true = [r["intent"] for r in records]

    if args.model == "tfidf_logreg":
        model = load_tfidf_logreg()
        y_pred, confidences = predict_tfidf_logreg(model, texts)
    else:
        model = load_embedding_mlp()
        y_pred, confidences = predict_embedding_mlp(model, texts)

    labels = sorted(set(y_true) | set(y_pred))
    accuracy = sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)
    per_intent = precision_recall_f1(y_true, y_pred, labels)
    macro_precision = np.mean([m["precision"] for m in per_intent.values()])
    macro_recall = np.mean([m["recall"] for m in per_intent.values()])
    macro_f1 = np.mean([m["f1"] for m in per_intent.values()])

    print(f"Model: {args.model}  |  Split: {args.split}  |  n={len(records)}")
    print(f"Accuracy:        {accuracy:.4f}")
    print(f"Macro precision: {macro_precision:.4f}")
    print(f"Macro recall:    {macro_recall:.4f}")
    print(f"Macro F1:        {macro_f1:.4f}")

    print("\nPer-intent metrics:")
    for label in labels:
        m = per_intent[label]
        print(f"  {label:<24} P={m['precision']:.2f}  R={m['recall']:.2f}  "
              f"F1={m['f1']:.2f}  support={m['support']}")

    matrix = confusion_matrix(y_true, y_pred, labels)
    print_confusion_matrix(matrix, labels)

    error_analysis(records, y_pred, confidences)

    entity_metrics = evaluate_entities(records, y_pred)
    end_to_end_accuracy = evaluate_end_to_end(records, y_pred)

    print("\nEntity metrics (predicted intent -> extract_entities, vs. gold entities):")
    print(f"  Micro precision: {entity_metrics['micro_precision']:.4f}")
    print(f"  Micro recall:    {entity_metrics['micro_recall']:.4f}")
    print(f"  Micro F1:        {entity_metrics['micro_f1']:.4f}")
    for etype, m in entity_metrics["per_type"].items():
        if m["support"] == 0 and m["precision"] == 0 and m["recall"] == 0:
            continue
        flag = " (open-ended/heuristic)" if m["open_ended"] else ""
        print(f"    {etype:<12} P={m['precision']:.2f}  R={m['recall']:.2f}  "
              f"F1={m['f1']:.2f}  support={m['support']}{flag}")

    print(f"\nEnd-to-end accuracy (intent AND entities correct): {end_to_end_accuracy:.4f}")

    results = {
        "model": args.model,
        "split": args.split,
        "n": len(records),
        "accuracy": accuracy,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "per_intent": per_intent,
        "entity_metrics": entity_metrics,
        "end_to_end_accuracy": end_to_end_accuracy,
    }
    out_path = os.path.join(MODELS_DIR, f"{args.model}.{args.split}.eval.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=float)
    print(f"\nSaved evaluation results to {out_path}")


if __name__ == "__main__":
    main()
