# Reinitialized

Reinitialized is a small, local natural-language understanding engine for the Rein assistant. It is **not a general-purpose ChatGPT replacement**. Its job is to turn student language into a safe structured prediction:

```text
user text
  -> deterministic tokenizer
  -> embedding MLP
  -> intent + confidence
  -> deterministic entity extraction
  -> structured JSON
  -> Rein / Mastercontrol / Notes
```

## Current release

The repository now contains a working **Reinitialized NLU v4** pipeline:

- 936 labeled examples / 24 intents
- reproducible train/validation/test split
- TF-IDF + Logistic Regression baseline
- compact neural model: **32-d embedding -> mean pool -> 64-unit ReLU -> 24-class output**
- Python training and evaluation
- JSON model export
- native Rust inference implementation for the exported model
- Python/Rust tokenizer contract
- deterministic course/date/time/money/topic/id/title/description extraction
- confidence bands and safe `UNKNOWN` handling
- Rust CLI: `predict`, `inspect`, `tokenize`, `benchmark`, `evaluate`, `chat`, `serve`
- local HTTP `/predict` and `/health` service for Rein
- Python `rein_adapter.py` client
- regression smoke tests for the important Rein requests
- Mastercontrol-safe separation: Reinitialized produces intent/entities; it does not execute mutations

The latest held-out test run is **91.49% accuracy / 0.910 macro F1**. The exact Rein-style smoke tests for no-class, deadline creation, deposit recording, deadline deletion, and learning `3's complement` all produce the expected intent and relevant entities.

The test score is deliberately treated as an evaluation result, not a claim that Reinitialized understands arbitrary English. The model is domain-specific and its dataset should continue to grow with real student phrasing.

## Architecture

```text
                         Rein
                           |
                           v
                    Reinitialized
                           |
          +----------------+----------------+
          |                                 |
          v                                 v
     Intent model                       Entities
          |                                 |
          +----------------+----------------+
                           |
                           v
                 structured prediction
                           |
             +-------------+-------------+
             |                           |
             v                           v
        class notes                 Mastercontrol
        / FTS retrieval              PIN + confirm
             |                           |
             v                           v
        grounded answer               database
```

Reinitialized never receives database credentials and never executes SQL or Mastercontrol mutations.

## Neural model

The deployed model is intentionally small:

```text
word tokens
    |
    v
embedding table [vocab, 32]
    |
    v
masked mean pool [32]
    |
    v
Linear 32 -> 64
    |
   ReLU
    |
    v
Linear 64 -> 24 intents
    |
   softmax
```

This is a genuine two-layer MLP classifier rather than the earlier embedding-plus-single-linear baseline. The same tensor operations are implemented in Rust so the exported model can run without Python at inference time.

A Transformer is intentionally **not** required for this release. A small Transformer is a sensible future experiment, but making the existing NLU engine reliable is more useful than adding architecture before the data and integration are ready.

## Dataset

`data/intents.jsonl` is the source dataset. Each record has:

```json
{"text":"Can you mark LCD as having no class tomorrow?","intent":"MARK_NO_CLASS","entities":{"course":"LCD","date":"tomorrow"}}
```

Current intents cover schedules, deadlines, notes, learning, announcements, polls, funds, and Mastercontrol-style mutations.

The dataset is versioned through `data/dataset_meta.json`. Add realistic student paraphrases instead of relying only on templates.

## Python training

```bash
cd reinitialized
python -m pip install -r python/requirements.txt
python python/dataset.py --version v4 --seed 42
python python/train.py --model embedding_mlp --epochs 1000
python python/evaluate.py --model embedding_mlp --split test
python python/export.py
python python/quickcheck.py
```

The final artifact is:

```text
models/model_artifact.json
```

## Rust

A Rust toolchain is required for the native engine.

```bash
cd rust
cargo test
cargo build --release
```

Run predictions from `rust/`:

```bash
cargo run --release -- predict "Could you remove deadline 7?"
cargo run --release -- inspect
cargo run --release -- benchmark --iterations 500
cargo run --release -- chat
```

Start the local service:

```bash
cargo run --release -- serve --bind 127.0.0.1:8787
```

Endpoints:

```text
GET  /health
POST /predict
```

Request:

```json
{"text":"Please add a deadline for my HDL class tomorrow at 6 PM titled lab report."}
```

Response:

```json
{
  "intent":"CREATE_DEADLINE",
  "confidence":0.99,
  "confidence_band":"high",
  "entities":{
    "course":"HDL",
    "date":"tomorrow",
    "time":"18:00",
    "title":"lab report"
  }
}
```

## Rein integration

If the Rein backend is Python, the included client avoids an ML dependency inside the website:

```python
from python.rein_adapter import predict

result = predict("Could you remove deadline 7?")
```

The recommended production flow is:

```text
Rein Flask route
    |
    v
Reinitialized HTTP service
    |
    v
intent + entities
    |
    +--> read operation -> existing Rein service
    |
    +--> mutation -> Mastercontrol prepare -> PIN -> confirmation -> execute
```

Do not let a model prediction call a database function directly.

## Learning buddy

Reinitialized identifies the learning intent; Rein supplies the knowledge.

Example:

```text
User: How do I use 3's complement?

Reinitialized:
  intent = LEARN_TOPIC
  topic  = 3's complement

Rein:
  search Notes/FTS
  retrieve relevant class material
  answer from the retrieved material
```

This keeps the model small and prevents it from inventing class material that does not exist in the website's notes.

## Confidence and unknowns

Predictions expose:

- `high` >= 0.90
- `possible_ambiguity` >= 0.60
- `clarification_required` < 0.60

Inputs with no known vocabulary or very weak confidence become `UNKNOWN` and should be clarified instead of being executed.

The confidence value is **not** an authorization mechanism. Mastercontrol remains authoritative.

## What is still intentionally future work

- WordPiece/BPE tokenizer
- compact Transformer experiment
- stronger open-ended entity extraction
- better out-of-domain detection
- human feedback/review dataset
- Rust-side metric evaluation
- quantization
- optional tiny causal language-model research branch

These are extensions, not prerequisites for the current local NLU engine.
