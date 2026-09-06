//! determinism-lint: enforces docs/DETERMINISM.md rules 1-4 (plus the threading and
//! dependency-tree corollaries) in the constrained crates `blindside-sim`,
//! `blindside-vm` and `blindside-gen`.
//!
//! Source checks work on the Rust token stream, not on text. `proc_macro2` lexes each
//! file: comments vanish, doc comments become `#[doc = "..."]` string literals, and string
//! literals are opaque tokens. Only identifiers, path sequences and numeric literals are
//! inspected, so documentation that *mentions* a banned token never trips the lint.
//!
//! Rejected tokens (see [`Rule`]):
//!   - identifiers `f32`, `f64`; float literals (suffixed or not)
//!   - identifiers `HashMap`, `HashSet`
//!   - identifiers `SystemTime`, `Instant`; paths `std::time`, `core::time`
//!   - identifier `rand` and any `rand_*` crate; identifier `rayon`
//!   - paths `std::thread`, `core::thread`
//!
//! `--check-all` additionally verifies each constrained crate's `Cargo.toml` pulls in
//! nothing but the allow-listed dependencies.

use proc_macro2::{TokenStream, TokenTree};
use std::fmt;
use std::path::{Path, PathBuf};

/// The constrained crates, relative to the workspace root.
pub const CONSTRAINED_CRATES: [&str; 3] = [
    "crates/blindside-sim",
    "crates/blindside-vm",
    "crates/blindside-gen",
];

/// The only crates a constrained crate may list under `[dependencies]` or
/// `[build-dependencies]` (ARCHITECTURE.md "Crate layout"; DETERMINISM.md rule 1;
/// PHASE-0-HARNESS.md state hash).
pub const ALLOWED_DEPENDENCIES: [&str; 4] =
    ["blindside-vm", "blindside-content", "fixed", "blake3"];

/// Which DETERMINISM.md rule a finding violates.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Rule {
    /// Rule 1: no `f32`/`f64`, fixed-point only.
    Float,
    /// Rule 2: no `HashMap`/`HashSet` (unordered iteration).
    HashCollection,
    /// Rule 3: no wall clock (`std::time`, `SystemTime`, `Instant`).
    WallClock,
    /// Rule 4: no `rand`; RNG is counter-based and stateless.
    Rand,
    /// Rule 5: no threading inside a tick (`std::thread`, `rayon`).
    Thread,
    /// ARCHITECTURE.md: dependency tree must stay auditable.
    Dependency,
    /// The file could not be read or lexed; treated as a failure so nothing slips by.
    Unparseable,
}

impl Rule {
    pub fn describe(self) -> &'static str {
        match self {
            Rule::Float => "rule 1: no f32/f64, fixed-point (Fx) only",
            Rule::HashCollection => {
                "rule 2: no HashMap/HashSet; use BTreeMap or SlotMap with explicit ordering"
            }
            Rule::WallClock => "rule 3: no SystemTime/Instant/std::time",
            Rule::Rand => "rule 4: no rand; RNG is draw(seed, tick, entity_id, purpose_id)",
            Rule::Thread => "rule 5: no threading inside a tick",
            Rule::Dependency => {
                "dependency tree: constrained crates may only depend on the allow-list"
            }
            Rule::Unparseable => "file could not be read or lexed",
        }
    }
}

/// One violation, pointing at a file, line and column.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Finding {
    pub file: PathBuf,
    /// 1-based. 0 when the finding is about the whole file / manifest.
    pub line: usize,
    /// 1-based. 0 when the finding is about the whole file / manifest.
    pub column: usize,
    pub token: String,
    pub rule: Rule,
}

impl fmt::Display for Finding {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{}:{}:{}: `{}` -- {}",
            self.file.display(),
            self.line,
            self.column,
            self.token,
            self.rule.describe()
        )
    }
}

// ---------------------------------------------------------------------------------------
// Source scanning
// ---------------------------------------------------------------------------------------

const BANNED_IDENTS: [(&str, Rule); 8] = [
    ("f32", Rule::Float),
    ("f64", Rule::Float),
    ("HashMap", Rule::HashCollection),
    ("HashSet", Rule::HashCollection),
    ("SystemTime", Rule::WallClock),
    ("Instant", Rule::WallClock),
    ("rand", Rule::Rand),
    ("rayon", Rule::Thread),
];

/// `<root>::<module>` path prefixes that are banned regardless of what follows.
const BANNED_PATHS: [(&str, &str, Rule); 4] = [
    ("std", "time", Rule::WallClock),
    ("core", "time", Rule::WallClock),
    ("std", "thread", Rule::Thread),
    ("core", "thread", Rule::Thread),
];

/// Lex `source` (attributed to `file`) and return every banned token in it.
pub fn scan_source(file: &Path, source: &str) -> Vec<Finding> {
    let stream: TokenStream = match source.parse() {
        Ok(s) => s,
        Err(e) => {
            let start = e.span().start();
            return vec![Finding {
                file: file.to_path_buf(),
                line: start.line,
                column: start.column + 1,
                token: e.to_string(),
                rule: Rule::Unparseable,
            }];
        }
    };
    let mut out = Vec::new();
    scan_stream(file, stream, &mut out);
    out
}

fn scan_stream(file: &Path, stream: TokenStream, out: &mut Vec<Finding>) {
    let tokens: Vec<TokenTree> = stream.into_iter().collect();
    for (i, tt) in tokens.iter().enumerate() {
        match tt {
            // Delimiters carry no information for us; recurse into the body.
            TokenTree::Group(g) => scan_stream(file, g.stream(), out),
            TokenTree::Ident(id) => {
                let name = id.to_string();
                let rule = BANNED_IDENTS
                    .iter()
                    .find(|(n, _)| *n == name)
                    .map(|(_, r)| *r)
                    .or_else(|| name.starts_with("rand_").then_some(Rule::Rand))
                    .or_else(|| banned_path_tail(&tokens, i, &name));
                if let Some(rule) = rule {
                    out.push(finding(file, id.span(), &name, rule));
                }
            }
            TokenTree::Literal(lit) => {
                let text = lit.to_string();
                // `t.0.1` lexes as Ident, '.', Literal("0.1"): a tuple index, not a float.
                let after_dot =
                    i > 0 && matches!(&tokens[i - 1], TokenTree::Punct(p) if p.as_char() == '.');
                if !after_dot && is_float_literal(&text) {
                    out.push(finding(file, lit.span(), &text, Rule::Float));
                }
            }
            TokenTree::Punct(_) => {}
        }
    }
}

/// If `tokens[i]` (named `name`) is the tail of `<root> :: <name>` for a banned pair,
/// return that pair's rule.
fn banned_path_tail(tokens: &[TokenTree], i: usize, name: &str) -> Option<Rule> {
    if i < 3 {
        return None;
    }
    let is_colon = |t: &TokenTree| matches!(t, TokenTree::Punct(p) if p.as_char() == ':');
    if !(is_colon(&tokens[i - 1]) && is_colon(&tokens[i - 2])) {
        return None;
    }
    let root = match &tokens[i - 3] {
        TokenTree::Ident(id) => id.to_string(),
        _ => return None,
    };
    BANNED_PATHS
        .iter()
        .find(|(r, m, _)| *r == root && *m == name)
        .map(|(_, _, rule)| *rule)
}

const INT_SUFFIXES: [&str; 12] = [
    "u8", "u16", "u32", "u64", "u128", "usize", "i8", "i16", "i32", "i64", "i128", "isize",
];

/// True for any numeric literal Rust would type as a float: a `.`, an exponent, or an
/// `f32`/`f64` suffix on a non-radix number.
fn is_float_literal(text: &str) -> bool {
    let Some(first) = text.chars().next() else {
        return false;
    };
    if !first.is_ascii_digit() {
        return false; // string, char, byte literal: not numeric
    }
    let lower = text.to_ascii_lowercase();
    if lower.starts_with("0x") || lower.starts_with("0o") || lower.starts_with("0b") {
        return false; // radix integers may contain 'e' (0x1e5) but are never floats
    }
    if lower.ends_with("f32") || lower.ends_with("f64") {
        return true;
    }
    if INT_SUFFIXES.iter().any(|s| lower.ends_with(s)) {
        return false;
    }
    lower.contains('.') || lower.contains('e')
}

fn finding(file: &Path, span: proc_macro2::Span, token: &str, rule: Rule) -> Finding {
    let start = span.start();
    Finding {
        file: file.to_path_buf(),
        line: start.line,
        column: start.column + 1,
        token: token.to_string(),
        rule,
    }
}

/// Walk `<crate_dir>/src` and scan every `.rs` file, in sorted path order.
pub fn scan_crate_sources(crate_dir: &Path) -> Vec<Finding> {
    let src = crate_dir.join("src");
    let mut files = Vec::new();
    collect_rs_files(&src, &mut files);
    files.sort();
    let mut out = Vec::new();
    if files.is_empty() {
        out.push(Finding {
            file: src.clone(),
            line: 0,
            column: 0,
            token: "no .rs files found".to_string(),
            rule: Rule::Unparseable,
        });
    }
    for file in files {
        match std::fs::read_to_string(&file) {
            Ok(text) => out.extend(scan_source(&file, &text)),
            Err(e) => out.push(Finding {
                file: file.clone(),
                line: 0,
                column: 0,
                token: format!("read error: {e}"),
                rule: Rule::Unparseable,
            }),
        }
    }
    out
}

fn collect_rs_files(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            collect_rs_files(&path, out);
        } else if path.extension().is_some_and(|e| e == "rs") {
            out.push(path);
        }
    }
}

// ---------------------------------------------------------------------------------------
// Manifest (Cargo.toml) dependency check
// ---------------------------------------------------------------------------------------

/// A dependency declared in a manifest, with the line it was declared on.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DeclaredDependency {
    pub name: String,
    pub line: usize,
    /// `dependencies`, `build-dependencies` or `dev-dependencies`.
    pub kind: String,
}

/// Minimal Cargo.toml reader: collects dependency names from `[dependencies]`,
/// `[build-dependencies]`, `[dev-dependencies]`, their `[<kind>.<name>]` table forms and
/// `[target.<cfg>.<kind>]` forms. Deliberately not a TOML parser; the lint has no
/// third-party dependencies beyond the lexer.
pub fn declared_dependencies(manifest: &str) -> Vec<DeclaredDependency> {
    let mut out = Vec::new();
    let mut current_kind: Option<String> = None;
    for (idx, raw) in manifest.lines().enumerate() {
        let line = strip_toml_comment(raw).trim().to_string();
        if line.is_empty() {
            continue;
        }
        if line.starts_with('[') {
            current_kind = None;
            let header = line.trim_start_matches('[').trim_end_matches(']').trim(); // also [[bin]]
            let segs = split_toml_header(header);
            // Find the dependency-kind segment (skipping a `target.<cfg>` prefix).
            let kind_pos = segs.iter().position(|s| {
                s == "dependencies" || s == "build-dependencies" || s == "dev-dependencies"
            });
            let Some(pos) = kind_pos else { continue };
            if pos > 0 && segs[0] != "target" {
                continue; // e.g. [workspace.dependencies]
            }
            let kind = segs[pos].clone();
            if let Some(name) = segs.get(pos + 1) {
                out.push(DeclaredDependency {
                    name: name.clone(),
                    line: idx + 1,
                    kind,
                });
            } else {
                current_kind = Some(kind);
            }
            continue;
        }
        if let Some(kind) = &current_kind {
            if let Some(eq) = line.find('=') {
                let key = line[..eq].trim().trim_matches('"').trim_matches('\'');
                if !key.is_empty() {
                    out.push(DeclaredDependency {
                        name: key.to_string(),
                        line: idx + 1,
                        kind: kind.clone(),
                    });
                }
            }
        }
    }
    out
}

fn strip_toml_comment(line: &str) -> &str {
    let mut in_str: Option<char> = None;
    for (i, c) in line.char_indices() {
        match in_str {
            Some(q) if c == q => in_str = None,
            Some(_) => {}
            None if c == '"' || c == '\'' => in_str = Some(c),
            None if c == '#' => return &line[..i],
            None => {}
        }
    }
    line
}

/// Split a table header on `.` outside quotes: `target.'cfg(unix)'.dependencies` ->
/// ["target", "cfg(unix)", "dependencies"].
fn split_toml_header(header: &str) -> Vec<String> {
    let mut segs = Vec::new();
    let mut cur = String::new();
    let mut in_str: Option<char> = None;
    for c in header.chars() {
        match in_str {
            Some(q) if c == q => in_str = None,
            Some(_) => cur.push(c),
            None if c == '"' || c == '\'' => in_str = Some(c),
            None if c == '.' => segs.push(std::mem::take(&mut cur).trim().to_string()),
            None => cur.push(c),
        }
    }
    segs.push(cur.trim().to_string());
    segs
}

/// Check `<crate_dir>/Cargo.toml` against [`ALLOWED_DEPENDENCIES`]. `[dev-dependencies]`
/// are returned separately as warnings (they never reach shipped sim code).
pub fn check_manifest(crate_dir: &Path) -> (Vec<Finding>, Vec<DeclaredDependency>) {
    let manifest_path = crate_dir.join("Cargo.toml");
    let text = match std::fs::read_to_string(&manifest_path) {
        Ok(t) => t,
        Err(e) => {
            return (
                vec![Finding {
                    file: manifest_path,
                    line: 0,
                    column: 0,
                    token: format!("read error: {e}"),
                    rule: Rule::Unparseable,
                }],
                Vec::new(),
            )
        }
    };
    let mut findings = Vec::new();
    let mut dev_warnings = Vec::new();
    for dep in declared_dependencies(&text) {
        if dep.kind == "dev-dependencies" {
            dev_warnings.push(dep);
            continue;
        }
        if !ALLOWED_DEPENDENCIES.contains(&dep.name.as_str()) {
            findings.push(Finding {
                file: manifest_path.clone(),
                line: dep.line,
                column: 1,
                token: format!("{} ({})", dep.name, dep.kind),
                rule: Rule::Dependency,
            });
        }
    }
    (findings, dev_warnings)
}

// ---------------------------------------------------------------------------------------
// Workspace root discovery
// ---------------------------------------------------------------------------------------

/// Find the workspace root: walk up from `start` looking for a `Cargo.toml` that contains
/// a `[workspace]` table; fall back to the root this binary was compiled in.
pub fn find_workspace_root(start: &Path) -> PathBuf {
    let mut dir = Some(start.to_path_buf());
    while let Some(d) = dir {
        let manifest = d.join("Cargo.toml");
        if let Ok(text) = std::fs::read_to_string(&manifest) {
            if text.lines().any(|l| l.trim() == "[workspace]") {
                return d;
            }
        }
        dir = d.parent().map(Path::to_path_buf);
    }
    Path::new(env!("CARGO_MANIFEST_DIR")).join("..").join("..")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn scan(src: &str) -> Vec<(usize, usize, String, Rule)> {
        scan_source(Path::new("t.rs"), src)
            .into_iter()
            .map(|f| (f.line, f.column, f.token, f.rule))
            .collect()
    }

    #[test]
    fn comments_and_strings_are_ignored() {
        let src = "// f64 HashMap std::time\n/* Instant rand */\n/// doc f32\nfn f() -> &'static str { \"HashSet f64\" }\n";
        assert!(scan(src).is_empty());
    }

    #[test]
    fn float_type_is_flagged_with_position() {
        let src = "pub struct S {\n    pub x: f64,\n}\n";
        assert_eq!(scan(src), vec![(2, 12, "f64".to_string(), Rule::Float)]);
    }

    #[test]
    fn float_literals_are_flagged_but_tuple_indexes_are_not() {
        assert_eq!(scan("const A: u8 = 1;").len(), 0);
        assert_eq!(scan("fn f() { let _ = 1.0f64; }")[0].2, "1.0f64");
        assert_eq!(scan("fn f() { let _ = 2.5; }")[0].2, "2.5");
        assert_eq!(scan("fn f() { let _ = 1e3; }")[0].2, "1e3");
        assert!(scan("const H: u32 = 0x1e5;").is_empty());
        assert!(scan("const N: u64 = 1_000u64;").is_empty());
        assert!(scan("fn f(t: ((u8,u8),u8)) -> u8 { t.0.1 }").is_empty());
    }

    #[test]
    fn std_paths_are_flagged_only_when_rooted() {
        assert_eq!(scan("use std::time::Duration;")[0].3, Rule::WallClock);
        assert_eq!(scan("use core::time::Duration;")[0].3, Rule::WallClock);
        assert_eq!(
            scan("fn f() { std::thread::spawn(|| ()); }")[0].3,
            Rule::Thread
        );
        // A module of our own called `time` is fine.
        assert!(scan("mod time {} use crate::time::x;").is_empty());
    }

    #[test]
    fn rand_and_rayon_are_flagged() {
        assert_eq!(scan("use rand::Rng;")[0].3, Rule::Rand);
        assert_eq!(scan("use rand_chacha::ChaCha8Rng;")[0].3, Rule::Rand);
        assert_eq!(scan("use rayon::prelude::*;")[0].3, Rule::Thread);
    }

    #[test]
    fn manifest_parser_handles_all_forms() {
        let m = r#"
[package]
name = "x"
[dependencies]
fixed = "1" # comment
"blake3" = { version = "1" }
[dependencies.serde]
version = "1"
[target.'cfg(unix)'.dependencies]
libc = "0.2"
[dev-dependencies]
proptest = "1"
[workspace.dependencies]
ignored = "1"
"#;
        let deps = declared_dependencies(m);
        let names: Vec<(String, String)> = deps.into_iter().map(|d| (d.name, d.kind)).collect();
        assert_eq!(
            names,
            vec![
                ("fixed".into(), "dependencies".into()),
                ("blake3".into(), "dependencies".into()),
                ("serde".into(), "dependencies".into()),
                ("libc".into(), "dependencies".into()),
                ("proptest".into(), "dev-dependencies".into()),
            ]
        );
    }
}
