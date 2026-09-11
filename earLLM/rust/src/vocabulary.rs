//! Vocabulary: token <-> id mapping, loaded from the exported model artifact.
//!
//! Contract (must match python/tokenizer.py):
//!   special tokens, fixed ids:
//!     0: [PAD]
//!     1: [UNK]
//!     2: [BOS]
//!     3: [EOS]
//!
//! Input shape:  Vec<String> tokens
//! Output shape: Vec<u32> token ids, same length as input tokens

use std::collections::HashMap;

pub const PAD_ID: u32 = 0;
pub const UNK_ID: u32 = 1;
#[allow(dead_code)]
pub const BOS_ID: u32 = 2;
#[allow(dead_code)]
pub const EOS_ID: u32 = 3;

#[derive(Debug, Clone)]
pub struct Vocabulary {
    token_to_id: HashMap<String, u32>,
}

impl Vocabulary {
    pub fn from_map(token_to_id: HashMap<String, u32>) -> Self {
        Vocabulary { token_to_id }
    }

    pub fn len(&self) -> usize {
        self.token_to_id.len()
    }

    #[allow(dead_code)]
    pub fn is_empty(&self) -> bool {
        self.token_to_id.is_empty()
    }

    /// Encode already-tokenized words into ids. Unknown tokens map to UNK_ID.
    pub fn encode_tokens(&self, tokens: &[String]) -> Vec<u32> {
        tokens
            .iter()
            .map(|t| *self.token_to_id.get(t.as_str()).unwrap_or(&UNK_ID))
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_vocab() -> Vocabulary {
        let mut map = HashMap::new();
        map.insert("[PAD]".to_string(), 0);
        map.insert("[UNK]".to_string(), 1);
        map.insert("[BOS]".to_string(), 2);
        map.insert("[EOS]".to_string(), 3);
        map.insert("add".to_string(), 4);
        map.insert("hdl".to_string(), 5);
        map.insert("deadline".to_string(), 6);
        map.insert("tomorrow".to_string(), 7);
        Vocabulary::from_map(map)
    }

    #[test]
    fn encodes_known_tokens() {
        let vocab = test_vocab();
        let tokens = vec!["add".to_string(), "hdl".to_string(), "deadline".to_string()];
        assert_eq!(vocab.encode_tokens(&tokens), vec![4, 5, 6]);
    }

    #[test]
    fn unknown_token_maps_to_unk() {
        let vocab = test_vocab();
        let tokens = vec!["xyz_never_seen".to_string()];
        assert_eq!(vocab.encode_tokens(&tokens), vec![UNK_ID]);
    }

    #[test]
    fn vocab_len_matches_map_size() {
        let vocab = test_vocab();
        assert_eq!(vocab.len(), 8);
    }
}
