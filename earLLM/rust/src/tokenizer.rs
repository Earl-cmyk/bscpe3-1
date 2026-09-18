//! Deterministic word tokenizer -- must match python/tokenizer.py::word_tokenize
//! so text tokenized in Python during training matches text tokenized here at
//! inference time. No randomness, no locale-dependent behavior.
//!
//! "add HDL deadline tomorrow" -> ["add", "hdl", "deadline", "tomorrow"]

/// Lowercase, then split into words (letters/digits, with internal apostrophes
/// kept, e.g. "3's") and punctuation (each punctuation char its own token).
pub fn word_tokenize(text: &str) -> Vec<String> {
    let lower = text.trim().to_lowercase();
    let chars: Vec<char> = lower.chars().collect();
    let mut tokens = Vec::new();
    let mut i = 0;

    while i < chars.len() {
        let c = chars[i];
        if c.is_whitespace() {
            i += 1;
            continue;
        }
        if c.is_alphanumeric() {
            let start = i;
            while i < chars.len() {
                if chars[i].is_alphanumeric() {
                    i += 1;
                } else if chars[i] == '\''
                    && i + 1 < chars.len()
                    && chars[i + 1].is_alphanumeric()
                {
                    // keep internal apostrophe, e.g. "3's"
                    i += 1;
                } else {
                    break;
                }
            }
            tokens.push(chars[start..i].iter().collect());
        } else {
            // punctuation: single-char token
            tokens.push(c.to_string());
            i += 1;
        }
    }

    tokens
}

/// Simplest possible tokenizer, kept for comparison/debugging (spec section 4).
#[allow(dead_code)]
pub fn whitespace_tokenize(text: &str) -> Vec<String> {
    text.trim().split_whitespace().map(|s| s.to_string()).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tokenizes_simple_sentence() {
        let tokens = word_tokenize("add HDL deadline tomorrow");
        assert_eq!(tokens, vec!["add", "hdl", "deadline", "tomorrow"]);
    }

    #[test]
    fn lowercases_input() {
        let tokens = word_tokenize("HDL Lab Report");
        assert_eq!(tokens, vec!["hdl", "lab", "report"]);
    }

    #[test]
    fn splits_punctuation_as_separate_tokens() {
        let tokens = word_tokenize("Can you mark LCD as having no class tomorrow?");
        assert_eq!(tokens.last().unwrap(), "?");
        assert!(tokens.contains(&"lcd".to_string()));
    }

    #[test]
    fn keeps_internal_apostrophe() {
        let tokens = word_tokenize("How do I use 3's complement?");
        assert!(tokens.contains(&"3's".to_string()));
    }

    #[test]
    fn empty_input_yields_no_tokens() {
        assert!(word_tokenize("").is_empty());
        assert!(word_tokenize("   ").is_empty());
    }

    #[test]
    fn whitespace_tokenizer_matches_python_naive_split() {
        let tokens = whitespace_tokenize("add HDL deadline tomorrow");
        assert_eq!(tokens, vec!["add", "HDL", "deadline", "tomorrow"]);
    }
}
