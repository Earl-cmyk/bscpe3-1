# Reinitialized project audit

## 1. Current architecture

The project currently follows a split Python-for-training / Rust-for-inference design:

- Python handles dataset validation, tokenization, model training, evaluation, artifact export, and metadata writing.
- Rust loads the export artifact and performs model inference, entity extraction, confidence banding, CLI commands, and the local HTTP service.
- The shared contract is a JSON model artifact exported from Python and loaded by Rust without Python dependencies at runtime.

The current directory layout is consistent with the project’s intended scope:

- `data/`: source and split dataset files
- `python/`: dataset, tokenizer, training, evaluation, export, entity scripts
- `rust/`: tokenizer, model loader, inference path, CLI, HTTP server, tests
- `models/`: exported artifacts and evaluation outputs
- `docs/`: architecture/design documents

## 2. What already works

- Deterministic word-level tokenizer in Python and Rust
- Real compact neural classifier architecture in Python: embedding -> mean pooling -> hidden layer -> ReLU -> output logits
- Training pipeline that loads JSONL data, stratifies by intent, and exports model weights
- Evaluation pipeline with accuracy, precision, recall, F1, confusion matrix, and entity metrics
- JSON export for Rust consumption
- Rust model loading from the exported artifact
- Rust inference path with probabilities and confidence bands
- Local CLI and HTTP service scaffolding
- Security guardrails to avoid echoing arbitrary SQL, shell, or file-path payloads into structured output

## 3. What is incomplete or still risky

1. Dataset cleanup is not fully enforced in the checked-in source dataset.
   - The source file still contains at least one exact duplicate utterance.
   - The project must detect and remove duplicate text before split generation and explicitly reject cross-split leakage.

2. The project needs a formal artifact specification.
   - The current export is a JSON file with model weights, but it does not yet fully match the clean long-term artifact layout requested for standalone portability.
   - Metadata should include model version, architecture, dims, SHA-256, tokenizer version, dataset version, and validation flags.

3. CLI and server behavior are partially complete but still not fully release-polished.
   - The CLI includes predict/tokenize/inspect/benchmark/serve, but several commands still behave like placeholders rather than full operational features.
   - The HTTP server implements health and predict, but it still needs the final validated contract and edge-case handling.

4. The project would benefit from a stronger Python test suite and a release checklist.
   - The current repo has useful Rust tests, but the Python side still needs broad dataset/tokenizer/entity regression tests.

5. Unknown/out-of-domain behavior is acceptable for a domain-specific NLU engine, but it needs stronger explicit validation.
   - It is not enough to classify any low-confidence input as a valid intent; the system must be transparent about uncertainty.

## 4. Known TODOs

- Remove the remaining exact duplicate example in the canonical dataset.
- Add explicit artifact validation before Rust inference.
- Add stronger parity tests for token IDs/logits/probabilities on a fixed set of at least 20 sentences.
- Add benchmark harness output with average, min, max, and optional p50/p95 for tokenizer/model/full prediction latency.
- Finalize the CLI and server command contracts around the real on-disk artifact.
- Add Python-side tests for tokenizer, dataset integrity, entities, unknown handling, and export validation.
- Reconcile project docs with the actual implementation rather than the aspirational design.

## 5. Rust/Python compatibility issues

The design intent is sound, but the project still needs repeated verification to catch drift between Python and Rust:

- Tokenizer normalization and punctuation handling must match exactly.
- Special-token numbering must match exactly across Python and Rust.
- Exported vocab keys must map to the same IDs that the Rust loader reads.
- Embedding, hidden-layer, and output-layer weights must be loaded in the same matrix order in both environments.
- Softmax and argmax behavior must be numerically stable and checked against tolerance-based parity tests.

The main risk is silent mismatch when the exported artifact is updated without verifying both inference paths on the same sentence set.

## 6. Model architecture

The intended architecture is:

- tokens
- vocabulary lookup
- embedding table
- mean pooling over valid tokens
- linear layer: embedding_dim -> hidden_dim
- ReLU
- linear layer: hidden_dim -> num_classes
- softmax
- predicted intent + confidence

The Python implementation is already close to this architecture, which is a real small MLP rather than a simple embedding-plus-linear classifier.

## 7. Artifact format

The project is currently exporting a JSON artifact that includes:

- format version
- model_type
- embedding_dim
- hidden_dim
- vocab_size
- num_labels
- labels
- vocab map
- weight matrices
- bias vectors
- training metadata

This is usable, but the project should explicitly adopt a cleaner portable specification that includes metadata fields for:

- model version
- architecture name
- embedding dimension
- hidden dimension
- vocabulary size
- number of classes
- labels
- tokenizer version
- weight SHA-256
- dataset version
- validation status

## 8. Test coverage

The repo already contains useful Rust tests and some dataset-related Python checks, but the coverage is uneven:

- Good: Rust tokenizer tests, model tests, integration tests, security tests
- Weak: Python dataset integrity coverage, export validation, tokenizer parity, unknown handling, API validation
- Missing: formal at-least-20-sentence parity suite spanning all major intents

## 9. Recommended fixes

1. Keep the current, compact domain-specific scope; do not broaden into a general LLM.
2. Enforce dataset purity before training: remove exact duplicates and reject cross-split leakage.
3. Verify Python and Rust tokenizers with a single fixed parity sentence suite.
4. Add artifact validation before any inference call.
5. Finalize the CLI and HTTP server contract and test both with real command output.
6. Keep the model small and efficient; the project’s value is a safe local NLU engine, not a giant model.
7. Update README and docs to describe the actual architecture and limitations instead of the aspirational design.

## 10. Bottom line

The project is viable as a compact local NLU engine, but it still needs disciplined cleanup, parity verification, and release-level validation before it can be called finished. The current codebase is not “fake”; it is a real prototype that needs tightening, not replacement.
