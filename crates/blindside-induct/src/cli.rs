//! The four subcommands, exactly as the contract states them. JSON on stdout; exit 0, or 2
//! on a usage or input error with the reason on stderr.

use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};

use clap::{Parser, Subcommand};
use serde::Serialize;

use crate::blocks::BlockSet;
use crate::choices::Choices;
use crate::decision::Decision;
use crate::diff::diff;
use crate::error::{Error, Result};
use crate::induce::induce;
use crate::named_trace::NamedTrace;
use crate::render::render;
use crate::step_input::StepInput;
use crate::trace::Trace;
use crate::tree::DecisionTree;

#[derive(Debug, Parser)]
#[command(
    name = "induct",
    version,
    about = "Demonstration traces -> decision trees"
)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Command,
}

#[derive(Debug, Subcommand)]
pub enum Command {
    /// Induce the minimal separator from one or more traces.
    Induce {
        /// The block list.
        #[arg(long, value_name = "blocks.json")]
        blocks: PathBuf,
        /// Where to write the tree when the traces are consistent.
        #[arg(long, value_name = "tree.json")]
        out: PathBuf,
        /// One or more demonstrations.
        #[arg(required = true, value_name = "TRACE.json")]
        traces: Vec<PathBuf>,
    },
    /// Render a tree as indented lines and as one sentence.
    Render {
        tree: PathBuf,
        #[arg(long, value_name = "blocks.json")]
        blocks: PathBuf,
    },
    /// Decide one stop: reads the stop's "predicates" and "raw" as JSON on stdin.
    Decide {
        tree: PathBuf,
        #[arg(long, value_name = "blocks.json")]
        blocks: PathBuf,
    },
    /// The first differing choice between two choice lists.
    Diff {
        #[arg(long, value_name = "blocks.json")]
        blocks: PathBuf,
        a: PathBuf,
        b: PathBuf,
    },
}

/// Parses the process arguments, runs, prints, and returns the exit code.
pub fn run() -> i32 {
    let cli = match Cli::try_parse() {
        Ok(cli) => cli,
        Err(err) => {
            let _ = err.print();
            return err.exit_code();
        }
    };
    match execute(cli.command, &mut std::io::stdin()) {
        Ok(json) => {
            println!("{json}");
            0
        }
        Err(err) => {
            eprintln!("induct: {err}");
            2
        }
    }
}

/// Runs one subcommand and returns the JSON it prints.
pub fn execute(command: Command, stdin: &mut dyn Read) -> Result<String> {
    match command {
        Command::Induce {
            blocks,
            out,
            traces,
        } => {
            let blocks = BlockSet::load(&blocks)?;
            let traces = traces
                .iter()
                .map(|path| {
                    Ok(NamedTrace {
                        name: path.display().to_string(),
                        trace: Trace::load(path)?,
                    })
                })
                .collect::<Result<Vec<_>>>()?;
            let result = induce(&blocks, &traces)?;
            if let Some(tree) = &result.tree {
                write_json(&out, tree)?;
            }
            to_json(&result)
        }
        Command::Render { tree, blocks } => {
            let blocks = BlockSet::load(&blocks)?;
            let tree = DecisionTree::load(&tree)?;
            tree.validate(&blocks)?;
            to_json(&render(&tree, &blocks))
        }
        Command::Decide { tree, blocks } => {
            let blocks = BlockSet::load(&blocks)?;
            let tree = DecisionTree::load(&tree)?;
            tree.validate(&blocks)?;
            let mut text = String::new();
            stdin
                .read_to_string(&mut text)
                .map_err(|e| Error::io(Path::new("stdin"), e))?;
            let input: StepInput =
                serde_json::from_str(&text).map_err(|e| Error::json("stdin", e))?;
            to_json(&Decision {
                action: tree.decide(&input, &blocks).to_string(),
            })
        }
        Command::Diff { blocks, a, b } => {
            let blocks = BlockSet::load(&blocks)?;
            let left = Choices::load(&a)?;
            left.validate(&blocks, &a.display().to_string())?;
            let right = Choices::load(&b)?;
            right.validate(&blocks, &b.display().to_string())?;
            to_json(&diff(&left.choices, &right.choices))
        }
    }
}

fn to_json<T: Serialize>(value: &T) -> Result<String> {
    serde_json::to_string_pretty(value).map_err(|e| Error::json("output", e))
}

fn write_json<T: Serialize>(path: &Path, value: &T) -> Result<()> {
    let mut text = to_json(value)?;
    text.push('\n');
    fs::write(path, text).map_err(|e| Error::io(path, e))
}
