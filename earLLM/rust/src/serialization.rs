//! Serialization helpers: resolving the on-disk model artifact path.
//! The actual (de)serialization of the artifact's fields lives in model.rs,
//! next to the struct it fills in -- this module only owns "where is the
//! artifact file and does it look sane before we try to load it".

use std::path::{Path, PathBuf};

pub fn default_artifact_path() -> PathBuf {
    PathBuf::from("../models/model_artifact.json")
}

/// Friendly existence check so CLI errors point at the fix (run export.py)
/// instead of a raw filesystem error.
pub fn check_artifact_exists(path: &Path) -> Result<(), String> {
    if !path.exists() {
        return Err(format!(
            "Model artifact not found at {}.\n\
             Train and export it first:\n  \
             python python/train.py --model embedding_mlp\n  \
             python python/export.py",
            path.display()
        ));
    }
    Ok(())
}
