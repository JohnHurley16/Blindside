//! determinism-lint CLI. See lib.rs for what is checked and why.
//!
//! Exit codes: 0 clean, 1 findings, 2 usage or I/O error.

use determinism_lint::{
    check_manifest, find_workspace_root, scan_crate_sources, Finding, ALLOWED_DEPENDENCIES,
    CONSTRAINED_CRATES,
};
use std::path::PathBuf;
use std::process::ExitCode;

const USAGE: &str = "\
determinism-lint: reject non-deterministic constructs in the constrained crates
(docs/DETERMINISM.md rules 1-5; ARCHITECTURE.md dependency tree).

USAGE:
    determinism-lint [OPTIONS] [CRATE_DIR ...]

ARGS:
    CRATE_DIR ...    crate directories to lint (each must contain src/ and Cargo.toml).
                     Default: crates/blindside-sim, crates/blindside-vm, crates/blindside-gen
                     under the workspace root.

OPTIONS:
    --root <DIR>     workspace root used to resolve the default crate list.
                     Default: nearest ancestor of the current directory whose Cargo.toml
                     has a [workspace] table, else the root this binary was built in.
    --check-all      also verify each crate's Cargo.toml lists only allow-listed
                     dependencies (blindside-vm, blindside-content, fixed, blake3) under
                     [dependencies] / [build-dependencies]; [dev-dependencies] are warned.
    -q, --quiet      print only the summary line.
    -h, --help       this text.

Rejected in src/**/*.rs (comments, doc comments and string literals are ignored):
    f32 f64 and float literals     HashMap HashSet     SystemTime Instant std::time
    rand rand_* rayon              std::thread core::time core::thread

EXIT CODE: 0 clean, 1 findings, 2 usage/IO error.
";

struct Args {
    root: Option<PathBuf>,
    check_all: bool,
    quiet: bool,
    crates: Vec<PathBuf>,
}

fn parse_args() -> Result<Args, String> {
    let mut args = Args {
        root: None,
        check_all: false,
        quiet: false,
        crates: Vec::new(),
    };
    let mut it = std::env::args().skip(1);
    while let Some(a) = it.next() {
        match a.as_str() {
            "-h" | "--help" => {
                print!("{USAGE}");
                std::process::exit(0);
            }
            "--check-all" => args.check_all = true,
            "-q" | "--quiet" => args.quiet = true,
            "--root" => {
                let v = it.next().ok_or("--root needs a directory")?;
                args.root = Some(PathBuf::from(v));
            }
            s if s.starts_with("--root=") => args.root = Some(PathBuf::from(&s[7..])),
            s if s.starts_with('-') => return Err(format!("unknown option `{s}`")),
            s => args.crates.push(PathBuf::from(s)),
        }
    }
    Ok(args)
}

fn main() -> ExitCode {
    let args = match parse_args() {
        Ok(a) => a,
        Err(e) => {
            eprintln!("determinism-lint: {e}\n\n{USAGE}");
            return ExitCode::from(2);
        }
    };

    let crates: Vec<PathBuf> = if args.crates.is_empty() {
        let root = match args.root.clone() {
            Some(r) => r,
            None => match std::env::current_dir() {
                Ok(cwd) => find_workspace_root(&cwd),
                Err(e) => {
                    eprintln!("determinism-lint: cannot read current directory: {e}");
                    return ExitCode::from(2);
                }
            },
        };
        CONSTRAINED_CRATES.iter().map(|c| root.join(c)).collect()
    } else {
        args.crates.clone()
    };

    let mut findings: Vec<Finding> = Vec::new();
    let mut files_hit = std::collections::BTreeSet::new();
    let mut crates_hit = 0usize;

    for crate_dir in &crates {
        if !crate_dir.is_dir() {
            eprintln!(
                "determinism-lint: `{}` is not a directory",
                crate_dir.display()
            );
            return ExitCode::from(2);
        }
        let mut crate_findings = scan_crate_sources(crate_dir);
        if args.check_all {
            let (dep_findings, dev_warnings) = check_manifest(crate_dir);
            crate_findings.extend(dep_findings);
            for w in dev_warnings {
                if !args.quiet {
                    println!(
                        "{}:{}:1: warning: dev-dependency `{}` is not on the allow-list ({}); \
                         allowed for tests only",
                        crate_dir.join("Cargo.toml").display(),
                        w.line,
                        w.name,
                        ALLOWED_DEPENDENCIES.join(", ")
                    );
                }
            }
        }
        if !crate_findings.is_empty() {
            crates_hit += 1;
        }
        for f in &crate_findings {
            files_hit.insert(f.file.clone());
            if !args.quiet {
                println!("{f}");
            }
        }
        findings.extend(crate_findings);
    }

    let checks = if args.check_all {
        "sources + Cargo.toml dependencies"
    } else {
        "sources"
    };
    if findings.is_empty() {
        println!(
            "determinism-lint: OK -- {} crate(s) clean ({checks}): {}",
            crates.len(),
            crates
                .iter()
                .map(|c| c.display().to_string())
                .collect::<Vec<_>>()
                .join(", ")
        );
        ExitCode::SUCCESS
    } else {
        println!(
            "determinism-lint: FAIL -- {} finding(s) in {} file(s) across {} of {} crate(s) ({checks})",
            findings.len(),
            files_hit.len(),
            crates_hit,
            crates.len()
        );
        ExitCode::from(1)
    }
}
