# Reinitialized

## Project Goal

Build a small, self-contained language model/NLU system called **Reinitialized**, designed as the future language-understanding engine for the Rein assistant.

This is an educational and portfolio project.

The goal is NOT to reproduce ChatGPT or train a massive general-purpose LLM.

The goal is to understand and implement the fundamental components behind language models while producing a practical model that can eventually understand natural-language requests and convert them into structured Rein intents.

The project should prioritize:

* learning
* correctness
* explainability
* reproducibility
* Rust systems programming
* Python ML experimentation
* clean architecture
* measurable performance

Avoid unnecessary complexity.

---

# 1. Architecture

Use a hybrid Rust/Python architecture.

```text
                    REINITIALIZED
                          │
             ┌────────────┴────────────┐
             │                         │
          Python                     Rust
             │                         │
       Training / Data            Core / Inference
             │                         │
             └────────────┬────────────┘
                          ↓
                    Model Artifact
                          ↓
                    Rein Assistant
```

## Python

Use Python for:

* dataset preparation
* tokenization experiments
* training experiments
* evaluation
* visualization
* model analysis
* hyperparameter experiments
* exporting model weights

## Rust

Use Rust for:

* tokenizer implementation
* tensor/data structures where appropriate
* model architecture
* inference
* serialization/loading
* CLI
* benchmarking
* eventual Rein integration

The architecture must allow the model to be trained experimentally in Python and eventually executed through the Rust implementation.

---

# 2. Do Not Build a Giant LLM

The first version should be intentionally small.

Do not attempt:

* billions of parameters
* internet-scale datasets
* GPT-scale training
* distributed training
* massive GPU infrastructure
* custom CUDA kernels
* training a general-purpose ChatGPT replacement

Instead, build a small model that can demonstrate the core concepts.

The initial model may be:

* intent classifier
* sequence classifier
* small Transformer
* tiny causal language model

Prioritize an achievable implementation.

---

# 3. Development Stages

Build Reinitialized incrementally.

Do not immediately jump into a Transformer.

## Stage 0 — Baseline

Implement a deterministic baseline.

Example:

```text
TF-IDF
   ↓
Logistic Regression / SVM
   ↓
Intent
```

Use this as the baseline for evaluating the neural model.

Record:

* accuracy
* precision
* recall
* F1
* confusion matrix

---

# 4. Stage 1 — Tokenizer

Implement a tokenizer.

Start simple.

Possible progression:

```text
whitespace tokenizer
        ↓
word tokenizer
        ↓
subword tokenizer
```

The tokenizer should eventually support:

* vocabulary
* token IDs
* unknown token
* padding
* beginning/end tokens
* encoding
* decoding

Example:

```text
"add HDL deadline tomorrow"

↓

["add", "HDL", "deadline", "tomorrow"]

↓

[42, 183, 91, 17]
```

Keep tokenizer behavior deterministic.

---

# 5. Stage 2 — Intent Dataset

Create a dataset specifically for Reinitialized.

Example:

```json
{
  "text": "Can you mark LCD as having no class tomorrow?",
  "intent": "MARK_NO_CLASS",
  "entities": {
    "course": "LCD",
    "date": "tomorrow"
  }
}
```

Examples of intents:

```text
GET_SCHEDULE
GET_TODAY_SCHEDULE
GET_TOMORROW_SCHEDULE

GET_DEADLINES
GET_COURSE_DEADLINES
GET_WEEK_DEADLINES

SEARCH_NOTES
LEARN_TOPIC
EXPLAIN_TOPIC
QUIZ_TOPIC
PRACTICE_TOPIC

GET_ANNOUNCEMENTS
GET_POLLS

GET_FUND_BALANCE
GET_FUND_TRANSACTIONS

CREATE_DEADLINE
UPDATE_DEADLINE
DELETE_DEADLINE

MARK_NO_CLASS

CREATE_ANNOUNCEMENT
CREATE_NOTE
CREATE_POLL

RECORD_DEPOSIT
RECORD_EXPENSE
```

Start with approximately 20–30 intents.

Do not create hundreds of intents unnecessarily.

---

# 6. Dataset Diversity

Each intent should have many natural variations.

For:

```text
CREATE_DEADLINE
```

include examples such as:

```text
"Add an HDL deadline for tomorrow."

"Can you add a deadline for HDL tomorrow?"

"Please create an HDL lab report deadline."

"I need to add Lab Report to HDL."

"Put an HDL lab report due tomorrow at 6 PM."

"Schedule an HDL deadline for tomorrow evening."

"Add this assignment to the deadlines."
```

The objective is for the model to learn the underlying intent rather than memorize exact phrases.

Include:

* short sentences
* long sentences
* formal requests
* casual requests
* questions
* commands
* incomplete phrases
* different word orders
* numbers
* dates
* times

Do not rely entirely on synthetic data.

Collect realistic examples from actual anticipated Rein usage where appropriate and anonymize them.

---

# 7. Stage 3 — Intent Classifier

Implement a neural intent classifier.

Start with a small architecture.

Possible first architecture:

```text
Tokens
 ↓
Embedding
 ↓
Pooling / sequence representation
 ↓
Linear layer
 ↓
Softmax
 ↓
Intent
```

Then implement a small Transformer as the next version.

Track experiments.

Example:

```text
Model A:
TF-IDF + Logistic Regression
Accuracy: 94%

Model B:
Embedding + MLP
Accuracy: 95%

Model C:
Small Transformer
Accuracy: 97%
```

Do not assume a more complicated model is automatically better.

---

# 8. Stage 4 — Entity Extraction

Intent classification is not enough.

Reinitialized must eventually identify entities.

Example:

```text
"Add HDL Lab Report tomorrow at 6 PM"
```

Output:

```json
{
  "intent": "CREATE_DEADLINE",
  "entities": {
    "course": "HDL",
    "title": "Lab Report",
    "date": "tomorrow",
    "time": "18:00"
  }
}
```

Possible entity types:

```text
COURSE
TASK
TITLE
DATE
TIME
AMOUNT
DEADLINE_ID
TOPIC
DESCRIPTION
```

Initially implement deterministic entity extraction where appropriate.

Do not force the neural model to solve every problem.

Hybrid systems are acceptable.

---

# 9. Structured Output

The final model interface should produce structured data.

Example:

```json
{
  "intent": "CREATE_DEADLINE",
  "confidence": 0.96,
  "entities": {
    "course": "HDL",
    "title": "Lab Report",
    "date": "2026-08-27",
    "time": "18:00"
  }
}
```

Never allow Reinitialized to produce arbitrary executable code.

Never allow it to directly execute SQL.

Never allow it to directly modify Rein's database.

---

# 10. Confidence

Implement confidence estimation.

Example:

```text
confidence >= 0.90
    ↓
high confidence

0.60–0.89
    ↓
possible ambiguity

< 0.60
    ↓
clarification required
```

Do not blindly execute low-confidence predictions.

Example:

```text
User:
"Do something with HDL tomorrow."

Reinitialized:
Intent uncertain.

Rein:
"What would you like to do with HDL tomorrow?"
```

---

# 11. Learning Model

After the intent classifier works, implement a small Transformer.

Recommended conceptual architecture:

```text
Token IDs
    ↓
Token Embeddings
    +
Positional Embeddings
    ↓
Transformer Encoder
    ↓
Sequence Representation
    ↓
Classification Head
    ↓
Intent
```

For the first Transformer:

* small embedding dimension
* few layers
* few attention heads
* short context length

Keep it small enough to train locally.

---

# 12. Optional Causal Language Model

After the NLU model works, create a separate experimental tiny language model.

Architecture:

```text
Tokens
 ↓
Embedding
 ↓
Positional Encoding
 ↓
Transformer Decoder Blocks
 ↓
Linear Projection
 ↓
Next-token probabilities
```

Training objective:

```text
predict the next token
```

Example:

```text
Input:
"the HDL deadline is"

Target:
"tomorrow"
```

This is an educational experiment.

Do not make this model responsible for Rein's production commands.

---

# 13. Why Two Models

Keep the distinction:

```text
Reinitialized-NLU
```

for:

```text
natural language
→ intent + entities
```

and:

```text
Reinitialized-LM
```

for:

```text
text
→ next token
```

The NLU model is the practical Rein component.

The tiny LM is the deeper ML research/learning component.

---

# 14. Rust Core

Implement the inference engine in Rust.

Suggested project structure:

```text
reinitialized/
│
├── Cargo.toml
├── README.md
│
├── rust/
│   ├── src/
│   │   ├── main.rs
│   │   ├── tokenizer.rs
│   │   ├── vocabulary.rs
│   │   ├── model.rs
│   │   ├── transformer.rs
│   │   ├── attention.rs
│   │   ├── embeddings.rs
│   │   ├── classifier.rs
│   │   ├── inference.rs
│   │   └── serialization.rs
│   │
│   └── tests/
│
├── python/
│   ├── dataset.py
│   ├── tokenize.py
│   ├── train.py
│   ├── evaluate.py
│   ├── export.py
│   └── experiments/
│
├── data/
│   ├── intents.jsonl
│   ├── train.jsonl
│   ├── validation.jsonl
│   └── test.jsonl
│
├── models/
│
└── docs/
```

Adjust this structure if a simpler arrangement makes more sense.

---

# 15. Rust Libraries

Use established Rust libraries where they provide value.

Do not implement every numerical primitive from scratch merely for the sake of it.

Possible technologies to evaluate:

* `ndarray`
* `candle`
* `burn`
* `tokenizers`
* `serde`
* `serde_json`
* `bincode` or an appropriate model serialization format

Evaluate libraries based on the learning objective.

If implementing attention manually is useful for learning, do it.

If implementing low-level tensor memory management adds complexity without educational value, use an established library.

---

# 16. Python Training

Python should be the experimentation environment.

Use standard ML tooling where appropriate.

Possible stack:

```text
Python
NumPy
PyTorch
scikit-learn
matplotlib
```

Training should produce reproducible artifacts.

Record:

* seed
* dataset version
* hyperparameters
* training loss
* validation loss
* accuracy
* F1
* model version

---

# 17. Model Export

Create a stable model artifact format.

Example:

```text
trained model
     ↓
export.py
     ↓
model artifact
     ↓
Rust loader
     ↓
Rust inference
```

The exact serialization format can be chosen after evaluating the Rust ML framework.

The important requirement is:

> A model trained in Python must be loadable by the Rust inference engine.

---

# 18. Rein Integration

Reinitialized should eventually integrate with Rein like this:

```text
User
 ↓
Rein
 ↓
Reinitialized
 ↓
Intent + entities
 ↓
Existing Mastercontrol / Assistant tools
 ↓
Authorization
 ↓
Confirmation
 ↓
Execution
```

Example:

```text
User:
"Could you remove deadline 7?"

Reinitialized:

{
  "intent": "DELETE_DEADLINE",
  "entities": {
    "deadline_id": 7
  },
  "confidence": 0.98
}
```

Rein then handles authorization and confirmation.

---

# 19. Learning Buddy Integration

Reinitialized should also support academic intent detection.

Example:

```text
"How do I use 3's complement?"
```

Output:

```json
{
  "intent": "LEARN_TOPIC",
  "entities": {
    "topic": "3's complement"
  }
}
```

Rein then performs:

```text
LEARN_TOPIC
 ↓
search class knowledge base
 ↓
retrieve relevant notes
 ↓
answer using retrieved material
```

The model itself does not need to know the contents of the class notes.

---

# 20. Strict Separation of Responsibilities

This is critical.

```text
Reinitialized
    ↓
understands language

Rein
    ↓
orchestrates actions

Mastercontrol
    ↓
authorizes mutations

Backend
    ↓
validates operations

Database
    ↓
stores truth
```

Never collapse these responsibilities.

The model should never be trusted as an authorization system.

---

# 21. Security

Never allow model output to directly execute:

```text
SQL
Python
Shell commands
Rust code
database queries
arbitrary HTTP requests
```

The model can only select from a fixed set of known intents/tools.

Example:

```text
Allowed:
CREATE_DEADLINE

Not allowed:
"DELETE FROM deadlines WHERE..."
```

The backend must validate every field.

---

# 22. Evaluation

Build a proper evaluation pipeline.

Measure:

### Intent classification

* accuracy
* precision
* recall
* macro F1
* confusion matrix

### Entity extraction

* entity precision
* entity recall
* entity F1

### End-to-end

Measure:

```text
User sentence
 ↓
Correct intent?
 ↓
Correct entities?
 ↓
Correct tool?
```

Track the complete success rate.

Example:

```text
Intent accuracy:       96.8%
Entity F1:             93.4%
Tool selection:        95.1%
End-to-end accuracy:   91.7%
```

Do not hide poor results behind a single accuracy number.

---

# 23. Error Analysis

Create an error-analysis tool.

For every failed prediction, show:

```text
Input:
"Could you mark LCD as having no class tomorrow?"

Expected:
MARK_NO_CLASS

Predicted:
CREATE_DEADLINE

Why did this happen?
```

Group failures by:

* confusing intents
* missing entities
* date parsing
* course recognition
* long sentences
* ambiguous requests

Use these failures to improve the dataset.

---

# 24. Dataset Versioning

Treat the dataset as an actual ML asset.

Use:

```text
dataset_v1
dataset_v2
dataset_v3
```

Document changes.

Do not silently modify the dataset and compare models without recording what changed.

---

# 25. Human Feedback Loop

Eventually allow Rein to record corrections.

Example:

```text
Reinitialized:
I think you want CREATE_DEADLINE.

User:
No, I wanted MARK_NO_CLASS.

System:
Record correction?
```

Store the corrected example separately.

Do not automatically retrain from every interaction.

Instead:

```text
user corrections
 ↓
review dataset
 ↓
approved examples
 ↓
dataset version
 ↓
retraining
 ↓
evaluation
 ↓
new model
```

---

# 26. CLI

Create a useful Rust CLI.

Example:

```bash
reinitialized predict "Can you mark LCD as having no class tomorrow?"
```

Output:

```text
Intent: MARK_NO_CLASS
Course: LCD
Date: tomorrow
Confidence: 0.97
```

Also support:

```bash
reinitialized inspect model.bin

reinitialized tokenize "hello Rein"

reinitialized benchmark

reinitialized evaluate

reinitialized chat
```

---

# 27. Debugging Philosophy

The developer has limited tolerance for debugging complexity.

Therefore:

* keep modules small
* provide clear errors
* avoid unnecessary abstractions
* write tests before complex refactors
* make each stage independently executable
* provide diagnostic commands
* avoid giant files
* avoid hidden magic
* document tensor shapes
* document model dimensions
* assert tensor dimensions where possible

For every neural component, document:

```text
Input shape
Output shape
Expected dtype
Expected dimensions
```

Example:

```text
Input:
[batch, sequence_length]

Embedding:
[batch, sequence_length, embedding_dim]

Transformer:
[batch, sequence_length, embedding_dim]

Classifier:
[batch, num_classes]
```

This is especially important in Rust.

---

# 28. Debugging Requirements

When a test fails, error messages should identify:

```text
component
expected
actual
tensor shape
model configuration
dataset example
```

Avoid generic errors such as:

```text
something went wrong
```

Prefer:

```text
AttentionLayer:
expected q shape [4, 32, 64]
received [4, 31, 64]

Possible cause:
sequence length mismatch.
```

---

# 29. Tests

Implement tests for:

### Tokenizer

* encoding
* decoding
* unknown tokens
* special tokens

### Dataset

* schema
* malformed examples
* labels
* entity format

### Model

* forward pass
* tensor shapes
* output dimensions

### Training

* loss decreases on a tiny dataset

### Inference

* model loads correctly
* deterministic output with fixed seed/model

### Integration

```text
natural language
→ model
→ intent
→ Rein tool
```

### Security

Ensure model output cannot bypass Mastercontrol authorization.

---

# 30. First Milestone

Do NOT start with the Transformer.

The first successful milestone is:

```text
Python
 ↓
Dataset
 ↓
TF-IDF baseline
 ↓
Intent classification
 ↓
Evaluation
```

Then:

```text
Embedding model
 ↓
small neural classifier
```

Then:

```text
small Transformer
```

Then:

```text
Rust inference
```

Then:

```text
Rein integration
```

Then optionally:

```text
tiny causal language model
```

---

# 31. Definition of Done — Reinitialized v1

Reinitialized v1 is complete when:

* [ ] Dataset exists and is versioned.
* [ ] Tokenizer works.
* [ ] Intent taxonomy exists.
* [ ] TF-IDF baseline exists.
* [ ] Neural classifier exists.
* [ ] Evaluation pipeline exists.
* [ ] Entity extraction works for important Rein parameters.
* [ ] Model can export an artifact.
* [ ] Rust can load the model.
* [ ] Rust inference produces structured intent output.
* [ ] Confidence is available.
* [ ] Unknown/ambiguous requests are handled safely.
* [ ] Rein can consume the structured output.
* [ ] Mastercontrol remains responsible for authorization.
* [ ] No model output can directly execute database operations.
* [ ] Tests cover the critical pipeline.

---

# 32. Definition of Done — Reinitialized v2

After v1, optionally implement:

* [ ] Small Transformer.
* [ ] Better subword tokenizer.
* [ ] Context-aware intent classification.
* [ ] Better entity extraction.
* [ ] Tiny causal language model.
* [ ] Rust-native inference optimization.
* [ ] Quantization.
* [ ] Benchmarking against Python inference.
* [ ] Local/offline Rein NLU.

---

# Final Design Principle

Reinitialized is not intended to be a ChatGPT clone.

It is a **small language-model/NLU research project built specifically to become the language-understanding engine of Rein**.

The project should demonstrate that the developer understands:

```text
Data
 ↓
Tokenization
 ↓
Representation
 ↓
Machine Learning
 ↓
Transformer Architecture
 ↓
Inference
 ↓
Rust Systems Programming
 ↓
Structured AI Output
 ↓
Real Software Integration
```

Build the simplest working version first.

Do not skip directly to the most complicated architecture.

Every major component should be measurable, testable, replaceable, and understandable.
