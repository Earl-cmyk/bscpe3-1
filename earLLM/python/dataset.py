"""
dataset.py

Dataset loading + versioned stratified splitting for Reinitialized.

Responsibilities:
- Load data/intents.jsonl
- Validate schema (text, intent, entities)
- Produce a reproducible stratified split into train/validation/test
- Write dataset_version metadata so experiments are comparable (section 24)

Run:
    python python/dataset.py --version v1 --seed 42
Writes:
    data/train.jsonl
    data/validation.jsonl
    data/test.jsonl
    data/dataset_meta.json
"""

import argparse
import hashlib
import json
import os
import random
from collections import defaultdict

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
INTENTS_PATH = os.path.join(DATA_DIR, "intents.jsonl")


class DatasetError(Exception):
    pass


def load_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                raise DatasetError(f"{path}:{lineno}: malformed JSON: {e}")
            validate_record(record, path, lineno)
            records.append(record)
    return records


def validate_record(record, path, lineno):
    for field in ("text", "intent", "entities"):
        if field not in record:
            raise DatasetError(f"{path}:{lineno}: missing required field '{field}'")
    if not isinstance(record["text"], str) or not record["text"].strip():
        raise DatasetError(f"{path}:{lineno}: 'text' must be a non-empty string")
    if not isinstance(record["intent"], str) or not record["intent"].strip():
        raise DatasetError(f"{path}:{lineno}: 'intent' must be a non-empty string")
    if not isinstance(record["entities"], dict):
        raise DatasetError(f"{path}:{lineno}: 'entities' must be an object")


def remove_exact_duplicates(records):
    """Drop exact duplicate utterances while preserving the first occurrence."""
    deduped = []
    seen = set()
    for record in records:
        text = record["text"]
        key = text.casefold().strip()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def detect_cross_split_duplicates(train, val, test):
    """Report duplicate utterances across splits so no leakage slips into evaluation."""
    seen = {}
    leakage = []
    for split_name, split in (("train", train), ("validation", val), ("test", test)):
        for record in split:
            key = record["text"].casefold().strip()
            if key in seen:
                leakage.append({
                    "text": record["text"],
                    "first_seen_in": seen[key][0],
                    "duplicate_in": split_name,
                    "first_intent": seen[key][1],
                    "duplicate_intent": record["intent"],
                })
            else:
                seen[key] = (split_name, record["intent"])
    return leakage


def summarize_intents(records):
    counts = defaultdict(int)
    for record in records:
        counts[record["intent"]] += 1
    ordered = {intent: counts[intent] for intent in sorted(counts)}
    total = sum(ordered.values())
    imbalance = max(ordered.values()) / total if total else 0.0
    return ordered, imbalance


def stratified_split(records, seed=42, train_frac=0.7, val_frac=0.15):
    """Split each intent's examples proportionally so every split sees every intent
    (important with only ~4-9 examples per intent)."""
    by_intent = defaultdict(list)
    for r in records:
        by_intent[r["intent"]].append(r)

    rng = random.Random(seed)
    train, val, test = [], [], []

    for intent, examples in by_intent.items():
        examples = examples[:]
        rng.shuffle(examples)
        n = len(examples)
        n_train = max(1, round(n * train_frac))
        n_val = max(1, round(n * val_frac)) if n - n_train > 1 else 0
        n_train = min(n_train, n)
        n_val = min(n_val, n - n_train)

        train.extend(examples[:n_train])
        val.extend(examples[n_train:n_train + n_val])
        test.extend(examples[n_train + n_val:])

    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)
    return train, val, test


def write_jsonl(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()[:12]


def main():
    parser = argparse.ArgumentParser(description="Build versioned train/val/test splits")
    parser.add_argument("--version", default="v1", help="Dataset version label")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-frac", type=float, default=0.7)
    parser.add_argument("--val-frac", type=float, default=0.15)
    args = parser.parse_args()

    records = remove_exact_duplicates(load_jsonl(INTENTS_PATH))
    intents = sorted(set(r["intent"] for r in records))

    train, val, test = stratified_split(
        records, seed=args.seed, train_frac=args.train_frac, val_frac=args.val_frac
    )

    leakage = detect_cross_split_duplicates(train, val, test)
    if leakage:
        raise DatasetError(
            "train/validation/test leakage detected: " + json.dumps(leakage[:5], ensure_ascii=False)
        )

    write_jsonl(os.path.join(DATA_DIR, "train.jsonl"), train)
    write_jsonl(os.path.join(DATA_DIR, "validation.jsonl"), val)
    write_jsonl(os.path.join(DATA_DIR, "test.jsonl"), test)

    intent_counts, class_imbalance = summarize_intents(records)
    meta = {
        "dataset_version": args.version,
        "seed": args.seed,
        "source": "data/intents.jsonl",
        "source_hash": file_hash(INTENTS_PATH),
        "num_examples": len(records),
        "num_intents": len(intents),
        "intents": intents,
        "examples_per_intent": intent_counts,
        "duplicate_examples_removed": len(load_jsonl(INTENTS_PATH)) - len(records),
        "train_count": len(train),
        "validation_count": len(val),
        "test_count": len(test),
        "class_imbalance_ratio": round(class_imbalance, 4),
        "split_sizes": {"train": len(train), "validation": len(val), "test": len(test)},
        "split_fracs": {"train": args.train_frac, "validation": args.val_frac,
                         "test": round(1 - args.train_frac - args.val_frac, 4)},
    }
    with open(os.path.join(DATA_DIR, "dataset_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
