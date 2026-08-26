//! Library surface for `reinitialized`.
//!
//! This exists so `rust/tests/` (external integration tests, spec section 29)
//! can call `predict()` and load a real model artifact the same way the CLI
//! binary does, instead of only being testable by shelling out to the
//! compiled binary and scraping stdout.
//!
//! This is deliberately the same split that section 18 asks for (a thin
//! library crate Rein can link against directly): `main.rs` becomes a thin
//! wrapper over this crate rather than owning the modules itself.

pub mod classifier;
pub mod entities;
pub mod inference;
pub mod model;
pub mod serialization;
pub mod server;
pub mod tokenizer;
pub mod vocabulary;

pub use inference::{predict, StructuredPrediction};
pub use model::Model;
