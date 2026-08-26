"""
tokenize.py

Stage 1 tokenizer: deterministic word-level tokenizer + vocabulary.

Progression per spec section 4:
    whitespace tokenizer -> word tokenizer -> subword tokenizer (later)

This module implements the "word tokenizer" step: lowercase, split on
whitespace, and peel punctuation off as separate tokens. It is deterministic
(same input always yields same output) and has no randomness.

Vocabulary contract (must match rust/src/vocabulary.rs so a vocab built here
can be exported and reused by the Rust inference engine):

    special tokens, in fixed order:
        0: [PAD]
        1: [UNK]
        2: [BOS]
        3: [EOS]

Example:
    "add HDL deadline tomorrow"
        -> ["add", "hdl", "deadline", "tomorrow"]
        -> [42, 183, 91, 17]
"""

import json
import os
import re
from collections import Counter

PAD_TOKEN = "[PAD]"
UNK_TOKEN = "[UNK]"
BOS_TOKEN = "[BOS]"
EOS_TOKEN = "[EOS]"
SPECIAL_TOKENS = [PAD_TOKEN, UNK_TOKEN, BOS_TOKEN, EOS_TOKEN]

PAD_ID, UNK_ID, BOS_ID, EOS_ID = 0, 1, 2, 3

# Split off punctuation as its own token; keep apostrophes inside words
# (e.g. "3's" stays one token) since course/entity text relies on it.
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)*|[^\sA-Za-z0-9]")


def word_tokenize(text: str):
    """Deterministic word tokenizer: lowercase, split words vs punctuation."""
    text = text.strip().lower()
    return _TOKEN_RE.findall(text)


def whitespace_tokenize(text: str):
    """Simplest possible tokenizer, kept for comparison/debugging."""
    return text.strip().split()


class Vocabulary:
    def __init__(self, token_to_id=None):
        if token_to_id is None:
            token_to_id = {tok: i for i, tok in enumerate(SPECIAL_TOKENS)}
        self.token_to_id = dict(token_to_id)
        self.id_to_token = {i: t for t, i in self.token_to_id.items()}

    @classmethod
    def build(cls, texts, min_freq=1, max_size=None):
        vocab = cls()
        counter = Counter()
        for text in texts:
            counter.update(word_tokenize(text))

        # Deterministic ordering: frequency desc, then alphabetical for ties.
        items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
        for token, freq in items:
            if freq < min_freq:
                continue
            if max_size is not None and len(vocab.token_to_id) >= max_size:
                break
            if token not in vocab.token_to_id:
                idx = len(vocab.token_to_id)
                vocab.token_to_id[token] = idx
                vocab.id_to_token[idx] = token
        return vocab

    def __len__(self):
        return len(self.token_to_id)

    def encode_tokens(self, tokens, add_bos_eos=False, pad_to=None):
        ids = [self.token_to_id.get(t, UNK_ID) for t in tokens]
        if add_bos_eos:
            ids = [BOS_ID] + ids + [EOS_ID]
        if pad_to is not None:
            if len(ids) > pad_to:
                ids = ids[:pad_to]
            else:
                ids = ids + [PAD_ID] * (pad_to - len(ids))
        return ids

    def encode(self, text, add_bos_eos=False, pad_to=None):
        return self.encode_tokens(word_tokenize(text), add_bos_eos=add_bos_eos, pad_to=pad_to)

    def decode(self, ids, skip_special=True):
        tokens = []
        for i in ids:
            tok = self.id_to_token.get(i, UNK_TOKEN)
            if skip_special and tok in SPECIAL_TOKENS:
                continue
            tokens.append(tok)
        return " ".join(tokens)

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"token_to_id": self.token_to_id}, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(token_to_id=data["token_to_id"])


def _demo():
    text = "add HDL deadline tomorrow"
    print("whitespace:", whitespace_tokenize(text))
    print("word:      ", word_tokenize(text))

    vocab = Vocabulary.build([text, "add a deadline for HDL tomorrow"])
    ids = vocab.encode(text)
    print("ids:       ", ids)
    print("decoded:   ", vocab.decode(ids))


if __name__ == "__main__":
    _demo()
