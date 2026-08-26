# Reinitialized — Definition of Done

## Current release

- [x] Versioned dataset
- [x] Stratified train/validation/test split
- [x] TF-IDF baseline
- [x] Two-layer embedding MLP
- [x] Reproducible training metadata
- [x] Model export artifact
- [x] Rust model loader
- [x] Rust MLP forward pass
- [x] Deterministic tokenizer
- [x] Deterministic entity extraction
- [x] Confidence banding
- [x] Unknown handling
- [x] Rust CLI
- [x] Local HTTP inference service
- [x] Python Rein adapter
- [x] Regression smoke tests
- [x] Security separation from mutations

## Acceptance examples

The current trained model must correctly classify:

1. `Can you mark LCD as having no class tomorrow?`
2. `Please add a deadline for my HDL class tomorrow at 6 PM titled lab report.`
3. `Record a 500 peso deposit for HDL for printing materials.`
4. `Could you remove deadline 7?`
5. `How do I use 3's complement?`

Entity extraction must preserve the relevant course/date/time/title/amount/id/topic values.

## Not a requirement

A Transformer, causal LM, or general English generation is not required for this release. Those are separate experiments that can be added without changing the Rein security boundary.
