//! Integration tests (spec section 14/29): "natural language -> model ->
//! intent -> Rein tool", exercised against the *real* exported model
//! artifact at models/model_artifact.json -- not a hand-built fixture like
//! the unit tests in src/*.rs use. This is what would actually catch a
//! regression in export.py, the artifact schema, or the tokenizer/model
//! dispatch breaking the on-disk format.
//!
//! Run with: cargo test --test integration_test
//! (run from rust/, matching the rest of the project's paths)

use reinitialized::inference::predict;
use reinitialized::model::Model;

fn load_real_model() -> Model {
    // Same relative path convention as serialization::default_artifact_path,
    // but resolved from the crate root since integration tests run with
    // rust/ as the working directory.
    Model::load("../models/model_artifact.json")
        .expect("models/model_artifact.json should load -- run `python python/export.py` first")
}

/// A fixed set of canonical sentences drawn directly from data/test.jsonl,
/// one per intent family that's easy to disambiguate, paired with the
/// intent recorded there. Kept as literals (rather than parsed from the
/// jsonl at test time) so this test has no dependency on the dataset file
/// existing or being in a particular order -- it's testing the shipped
/// model artifact against fixed, known-good expectations.
const CANONICAL_CASES: &[(&str, &str)] = &[
    ("What's due this week?", "GET_WEEK_DEADLINES"),
    ("Move the Thesis deadline to tomorrow", "UPDATE_DEADLINE"),
    ("I'm trying to learn linked lists", "LEARN_TOPIC"),
    ("create a new deadline for Thesis, due Friday", "CREATE_DEADLINE"),
    ("create a note with today's key takeaways", "CREATE_NOTE"),
    ("let me see my classes", "GET_SCHEDULE"),
    ("did I miss any announcements", "GET_ANNOUNCEMENTS"),
    ("what's tomorrow looking like class-wise", "GET_TOMORROW_SCHEDULE"),
    ("give me today's timetable", "GET_TODAY_SCHEDULE"),
    ("Record a deposit of 500 pesos", "RECORD_DEPOSIT"),
    ("put in an expense of 1200 for the venue deposit", "RECORD_EXPENSE"),
    ("I want to practice karnaugh maps", "PRACTICE_TOPIC"),
];

#[test]
fn produces_valid_structured_output_for_canonical_sentences() {
    let model = load_real_model();

    for (text, _expected_intent) in CANONICAL_CASES {
        let result = predict(&model, text);

        // Contract checks (spec section 9's schema): every field must be
        // present and well-formed, regardless of whether the intent is
        // actually correct -- that's checked separately below with more
        // tolerance, since the model isn't (and isn't claimed to be) 100%
        // accurate.
        assert!(
            model.labels.contains(&result.intent),
            "predicted intent {:?} for {:?} is not one of the model's known labels",
            result.intent,
            text
        );
        assert!(
            (0.0..=1.0).contains(&result.confidence),
            "confidence {} for {:?} is out of [0, 1]",
            result.confidence,
            text
        );
        // entities is a BTreeMap<String, EntityValue> -- serializable and
        // possibly empty, but must not panic to construct or serialize.
        let _ = serde_json::to_string(&result).expect("StructuredPrediction must serialize");
    }
}

#[test]
fn matches_expected_intent_on_a_majority_of_canonical_sentences() {
    // Deliberately not "all" -- both baselines sit at ~90-92% test accuracy
    // (see README), so a handful of misses among 12 easy, per-intent
    // examples is expected and not a regression by itself. What *would* be
    // a regression is the model getting most or all of these wrong (e.g.
    // predict() silently always returning the same label, or the artifact
    // being loaded with a shuffled label list).
    let model = load_real_model();

    let correct = CANONICAL_CASES
        .iter()
        .filter(|(text, expected)| predict(&model, text).intent == *expected)
        .count();

    assert!(
        correct * 100 >= CANONICAL_CASES.len() * 60,
        "only {correct}/{} canonical sentences got the expected intent -- \
         check the artifact wasn't exported with a shuffled label list or \
         mismatched vocab",
        CANONICAL_CASES.len()
    );
}

#[test]
fn empty_input_does_not_panic() {
    let model = load_real_model();
    let result = predict(&model, "");
    assert!(result.intent == "UNKNOWN" || model.labels.contains(&result.intent));
    assert!((0.0..=1.0).contains(&result.confidence));
}
