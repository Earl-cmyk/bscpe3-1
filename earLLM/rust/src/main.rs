//! reinitialized CLI (spec section 26).
//!
//!   reinitialized predict "Can you mark LCD as having no class tomorrow?"
//!   reinitialized inspect models/model_artifact.json
//!   reinitialized tokenize "hello Rein"
//!   reinitialized benchmark
//!   reinitialized evaluate
//!   reinitialized chat

use std::io::{self, Write};
use std::path::PathBuf;
use std::time::Instant;

use clap::{Parser, Subcommand};

use reinitialized::{classifier, entities, inference, Model, serialization, tokenizer, server};

#[derive(Parser)]
#[command(name = "reinitialized", version, about = "Reinitialized NLU inference CLI")]
struct Cli {
    #[command(subcommand)]
    command: Command,

    /// Path to the model artifact JSON. Defaults to ../models/model_artifact.json
    /// (relative to rust/), matching the project's standard layout.
    #[arg(long, global = true)]
    model: Option<PathBuf>,
}

#[derive(Subcommand)]
enum Command {
    /// Predict intent + entities + confidence for a piece of text.
    Predict {
        text: String,
    },
    /// Print model artifact metadata (labels, vocab size, dims).
    Inspect {
        #[arg(default_value = None)]
        path: Option<PathBuf>,
    },
    /// Tokenize text and print token ids (no model needed).
    Tokenize {
        text: String,
    },
    /// Run repeated predictions and report throughput/latency.
    Benchmark {
        #[arg(long, default_value_t = 200)]
        iterations: usize,
    },
    /// Placeholder for wiring into python/evaluate.py-style metrics from Rust.
    Evaluate,
    /// Interactive REPL: type text, get structured predictions.
    Chat,
    /// Run a local HTTP inference service.
    Serve {
        #[arg(long, default_value = "127.0.0.1:8787")]
        bind: String,
    },
}

fn resolve_model_path(cli_path: &Option<PathBuf>) -> PathBuf {
    cli_path
        .clone()
        .unwrap_or_else(serialization::default_artifact_path)
}

fn load_model_or_exit(path: &PathBuf) -> Model {
    if let Err(e) = serialization::check_artifact_exists(path) {
        eprintln!("{e}");
        std::process::exit(1);
    }
    match Model::load(path) {
        Ok(m) => m,
        Err(e) => {
            eprintln!("Model:\nfailed to load artifact at {}\n{e}", path.display());
            std::process::exit(1);
        }
    }
}

fn print_prediction(result: &inference::StructuredPrediction) {
    println!("Intent: {}", result.intent);
    for (k, v) in &result.entities {
        let display = match v {
            entities::EntityValue::Text(s) => s.clone(),
            entities::EntityValue::Int(i) => i.to_string(),
        };
        println!("{}: {}", capitalize(k), display);
    }
    println!("Confidence: {:.2}", result.confidence);
    println!("Confidence band: {:?}", result.confidence_band);

    match result.confidence_band {
        classifier::ConfidenceBand::ClarificationRequired => {
            println!("\n[low confidence -- Rein should ask a clarifying question]");
        }
        classifier::ConfidenceBand::PossibleAmbiguity => {
            println!("\n[possible ambiguity -- Rein may want to confirm]");
        }
        classifier::ConfidenceBand::High => {}
    }
}

fn capitalize(s: &str) -> String {
    let mut c = s.chars();
    match c.next() {
        None => String::new(),
        Some(f) => f.to_uppercase().collect::<String>() + c.as_str(),
    }
}

fn main() {
    let cli = Cli::parse();
    let model_path = resolve_model_path(&cli.model);

    match cli.command {
        Command::Predict { text } => {
            let model = load_model_or_exit(&model_path);
            let result = inference::predict(&model, &text);
            print_prediction(&result);
        }
        Command::Inspect { path } => {
            let path = path.unwrap_or(model_path);
            let model = load_model_or_exit(&path);
            println!("Model artifact: {}", path.display());
            println!("  embedding_dim: {}", model.embedding_dim);
            println!("  vocab_size:    {}", model.vocab.len());
            println!("  num_labels:    {}", model.num_labels);
            println!("  labels:");
            for label in &model.labels {
                println!("    - {label}");
            }
        }
        Command::Tokenize { text } => {
            let tokens = tokenizer::word_tokenize(&text);
            println!("Tokens: {tokens:?}");
            // Without a loaded model we can't show real ids, but we can show
            // that tokenization is deterministic and ready to be encoded.
        }
        Command::Benchmark { iterations } => {
            let model = load_model_or_exit(&model_path);
            let sample = "Can you mark LCD as having no class tomorrow?";
            let start = Instant::now();
            for _ in 0..iterations {
                let _ = inference::predict(&model, sample);
            }
            let elapsed = start.elapsed();
            let per_call = elapsed / iterations as u32;
            println!("Ran {iterations} predictions in {elapsed:?}");
            println!("Average latency: {per_call:?}");
        }
        Command::Evaluate => { println!("Use python/python/evaluate.py for the full metrics report."); }
        Command::Serve { bind } => {
            if let Err(e) = server::serve(&model_path, &bind) { eprintln!("server error: {e}"); std::process::exit(1); }
        }
        Command::Chat => {
            let model = load_model_or_exit(&model_path);
            println!("Reinitialized chat (Ctrl+D to exit)");
            let stdin = io::stdin();
            loop {
                print!("> ");
                io::stdout().flush().ok();
                let mut line = String::new();
                let bytes = stdin.read_line(&mut line).unwrap_or(0);
                if bytes == 0 {
                    break;
                }
                let line = line.trim();
                if line.is_empty() {
                    continue;
                }
                let result = inference::predict(&model, line);
                print_prediction(&result);
                println!();
            }
        }
    }
}
