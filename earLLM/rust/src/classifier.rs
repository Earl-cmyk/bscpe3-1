//! Confidence banding (spec section 10).
//!
//!   confidence >= 0.90        -> High
//!   0.60 <= confidence < 0.90 -> PossibleAmbiguity
//!   confidence < 0.60         -> ClarificationRequired
//!
//! Low-confidence predictions must never be executed blindly -- callers
//! (Rein) are expected to branch on this band, not just the raw intent.

use serde::Serialize;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ConfidenceBand {
    High,
    PossibleAmbiguity,
    ClarificationRequired,
}

pub fn band_for(confidence: f32) -> ConfidenceBand {
    if confidence >= 0.90 {
        ConfidenceBand::High
    } else if confidence >= 0.60 {
        ConfidenceBand::PossibleAmbiguity
    } else {
        ConfidenceBand::ClarificationRequired
    }
}

/// Given the label list and their probabilities (same order, sums to 1.0),
/// return (predicted_label, confidence).
pub fn argmax_label(labels: &[String], probs: &[f32]) -> (String, f32) {
    let mut best_idx = 0usize;
    let mut best_val = f32::MIN;
    for (i, &p) in probs.iter().enumerate() {
        if p > best_val {
            best_val = p;
            best_idx = i;
        }
    }
    (labels[best_idx].clone(), best_val)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn high_confidence_band() {
        assert_eq!(band_for(0.97), ConfidenceBand::High);
        assert_eq!(band_for(0.90), ConfidenceBand::High);
    }

    #[test]
    fn possible_ambiguity_band() {
        assert_eq!(band_for(0.75), ConfidenceBand::PossibleAmbiguity);
        assert_eq!(band_for(0.60), ConfidenceBand::PossibleAmbiguity);
    }

    #[test]
    fn clarification_required_band() {
        assert_eq!(band_for(0.59), ConfidenceBand::ClarificationRequired);
        assert_eq!(band_for(0.10), ConfidenceBand::ClarificationRequired);
    }

    #[test]
    fn argmax_picks_highest_probability_label() {
        let labels = vec!["A".to_string(), "B".to_string(), "C".to_string()];
        let probs = vec![0.1, 0.7, 0.2];
        let (label, conf) = argmax_label(&labels, &probs);
        assert_eq!(label, "B");
        assert!((conf - 0.7).abs() < 1e-6);
    }
}
