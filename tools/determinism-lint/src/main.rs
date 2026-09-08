//! determinism-lint CLI. See lib.rs for what is checked and why.
//!
//! Exit codes: 0 clean, 1 findings, 2 usage or I/O error.

use determinism_lint::{
    check_manifest, find_workspace_root, scan_crate_sources, Finding, CONSTRAINED_CRATES,
    KNOWN_GAPS,
};
use std::path::PathBuf;
use std::process::ExitCode;

const USAGE: &str = "\
determinism-lint: reject non-deterministic constructs in the constrained crates
(docs/DETERMINISM.md rules 1-5; ARCHITECTURE.md dependency tree).

USAGE:
    determinism-lint [OPTIONS] [CRATE_DIR ...]

ARGS:
    CRATE_DIR ...    crate directories to lint (each must contain src/lib.rs and Cargo.toml).
                     Default: crates/blindside-sim, crates/blindside-vm, crates/blindside-gen
                     under the workspace root.

OPTIONS:
    --root <DIR>     workspace root used to resolve the default crate list.
                     Default: nearest ancestor of the current directory whose Cargo.toml
                     has a [workspace] table, else the root this binary was built in.
    --check-all      also verify each crate's Cargo.toml lists only allow-listed
                     dependencies (blindside-vm, blindside-content, fixed, blake3) under
                     [dependencies], [build-dependencies] and [dev-dependencies] alike.
                     A `package = \"..\"` rename is checked by the package, not the key, in
                     the inline-table, [dependencies.<key>] and dotted-key spellings. A
                     `workspace = true` entry is resolved through the nearest ancestor
                     Cargo.toml with a [workspace] table; with no such ancestor it is
                     warned, not failed, because Cargo could not build that crate either.
    -q, --quiet      print only the summary line.
    -h, --help       this text.

Rejected in src/**/*.rs (comments and doc comments are ignored; string literals are
opaque except for a pointer format spec):
    f32 f64 and float literals     HashMap HashSet     SystemTime Instant std::time
    rand rand_* rayon              std::thread core::time core::thread
    DefaultHasher RandomState SipHasher* std::collections::hash_map
    *const *mut std::ptr as_ptr as_mut_ptr addr_of addr_of_mut into_raw transmute NonNull
    fmt::Pointer, and `{:p}` / `{:#p}` in any string literal that is not a doc comment
    std::process std::env env! option_env!
    std::fs std::io std::net (ARCHITECTURE.md: blindside-sim is \"no I/O\")
    include!, and #[path = \"..\"] -- bare or inside cfg_attr -- that leaves src/ or does
    not name a .rs file (the src/ walk reads only *.rs)
    `unsafe`, #[allow(unsafe_code)] or #[expect(unsafe_code)] without a `// SAFETY:` line
    in the comment block directly above (attribute lines between are skipped);
    #![allow(unsafe_code)] anywhere (rule 8, the spelling half)

The one exemption: inside an item under the outer attribute
#[cfg(feature = \"inject-desync\")] -- that exact spelling -- HashMap, HashSet and the std
hashers are not findings (the canary's injection fixture, BLD-35). It ends with the item
(`{..}` body or `;`), never covers a `mod` or a file-level #![cfg(..)], and exempts
nothing else: a float inside the fixture is still a finding.

Rejected in the crate layout, with or without --check-all:
    a `path` under [lib] or [[bin]] in Cargo.toml: the crate root is src/lib.rs, and a
    root moved elsewhere is a crate this lint never opens
    a build script (build.rs, or `build = \"..\"` in [package]): it runs unlinted before
    the crate compiles and can change what gets compiled
    no src/lib.rs

Matched through braced use trees (`use std::{thread, time};`) and through raw
identifiers (`r#f64` is `f64`).

EXIT CODE: 0 clean, 1 findings, 2 usage/IO error.
";

/// Printed on every run, pass or fail: a clean exit means "no banned token was written in
/// these files", which is narrower than "this code is deterministic". The list is
/// [`KNOWN_GAPS`] in one line.
const SCOPE: &str = "determinism-lint: token-level check; not seen: macro expansion, \
                     dependency contents, most pointer casts, indirect `{:p}`, \
                     `use std as sys` / glob roots, a hostile manifest, rules 6-8 \
                     (`--help` has the list).";

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
                // The gaps print with the usage, not in a corner of the docs. A lint whose
                // limits are invisible gets trusted for things it never checked.
                print!("{USAGE}\n{KNOWN_GAPS}");
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
            let report = check_manifest(crate_dir);
            crate_findings.extend(report.findings);
            for w in report.warnings {
                if !args.quiet {
                    println!(
                        "{}:{}:1: warning: {}",
                        crate_dir.join("Cargo.toml").display(),
                        w.line,
                        w.message
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
        "sources + layout + Cargo.toml dependencies"
    } else {
        "sources + layout"
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
        println!("{SCOPE}");
        ExitCode::SUCCESS
    } else {
        println!(
            "determinism-lint: FAIL -- {} finding(s) in {} file(s) across {} of {} crate(s) ({checks})",
            findings.len(),
            files_hit.len(),
            crates_hit,
            crates.len()
        );
        println!("{SCOPE}");
        ExitCode::from(1)
    }
}
