//! determinism-lint: enforces docs/DETERMINISM.md rules 1-5 (plus the threading and
//! dependency-tree corollaries) in the constrained crates `blindside-sim`,
//! `blindside-vm` and `blindside-gen`.
//!
//! Source checks work on the Rust token stream, not on text. `proc_macro2` lexes each
//! file: comments vanish, doc comments become `#[doc = "..."]` string literals, and string
//! literals are opaque tokens. Only identifiers, path sequences, punctuation and numeric
//! literals are inspected, so documentation that *mentions* a banned token never trips the
//! lint. The one thing read out of a string literal is a pointer format spec (`{:p}`,
//! `{:#p}`), and `#[doc]` strings are exempt from that so prose stays prose.
//!
//! Rejected tokens (see [`Rule`]):
//!   - identifiers `f32`, `f64`; float literals (suffixed or not)
//!   - identifiers `HashMap`, `HashSet`
//!   - identifiers `SystemTime`, `Instant`; paths `std::time`, `core::time`
//!   - identifier `rand` and any `rand_*` crate; identifier `rayon`
//!   - paths `std::thread`, `core::thread`
//!   - `DefaultHasher`, `RandomState`, `SipHasher*`, `std::collections::hash_map`:
//!     std's hashers are seeded per process or change between std versions
//!   - raw pointers and the constructs that produce one: `*const`, `*mut`, `std::ptr`,
//!     `as_ptr`, `into_raw`, `transmute`, `NonNull`; and the ways of printing one:
//!     `fmt::Pointer`, a `{:p}` spec in a string literal
//!   - `std::process`, `std::env`, `env!`, `option_env!`: the machine is not a sim input
//!   - `include!`, and `#[path = "..."]` -- bare or inside `cfg_attr` -- that leaves
//!     `src/` or does not name a `.rs` file: both link code the `src/` walk never reads
//!
//! Rejected in the crate layout, read from `Cargo.toml` and the directory itself, on every
//! run and not only with `--check-all`:
//!   - a `path` under `[lib]` or `[[bin]]`: the crate root is `src/lib.rs`, and a root
//!     moved elsewhere is a crate this lint never opens
//!   - a build script (`build.rs`, or `build = ".."` in `[package]`): it runs unlinted
//!     before the crate compiles and can change what gets compiled
//!   - a missing `src/lib.rs`
//!
//! Two forms that used to slip through and no longer do: braced use trees, where the path
//! root sits outside the group (`use std::{thread, time};`), and raw identifiers, where
//! `r#f64` is the same type as `f64` to the compiler.
//!
//! `--check-all` additionally verifies each constrained crate's `Cargo.toml` pulls in
//! nothing but the allow-listed dependencies. A `package = "..."` rename is checked by
//! the package name, not the key, in every spelling Cargo accepts (inline table,
//! `[dependencies.<key>]` table, dotted key). A `workspace = true` entry is resolved
//! through the nearest ancestor `Cargo.toml` with a `[workspace]` table, the way Cargo
//! resolves it; when there is no such ancestor the entry is warned about rather than
//! failed, because Cargo could not build that crate either.
//!
//! # What this cannot see
//!
//! This is a lexer, not a compiler. It never expands a macro, resolves a name, or knows a
//! type. Where that leaves a hole the lint says so, rather than implying coverage it does
//! not have; [`KNOWN_GAPS`] is the same list condensed, and `--help` prints it.
//!
//! - **Macro-expanded tokens.** A `macro_rules!` body is scanned as written, but a proc
//!   macro can synthesise `f64` at expansion time and no text check will see it. The
//!   cheap ways to smuggle source into a crate -- `include!`, `env!`, a build script --
//!   are rejected, so what remains needs a dependency, and dependencies are allow-listed.
//! - **Anything a dependency defines.** `blindside_content::Table` may be a `HashMap`
//!   alias; the lint never opens that crate. `blindside-content` is an allowed dependency
//!   of every constrained crate and is not itself in [`CONSTRAINED_CRATES`], so none of
//!   these rules are enforced there. The allow-list bounds the blast radius; it does not
//!   close the hole. And the allow-list is a list of *names*: what `fixed` resolves to is
//!   settled by `Cargo.lock` and any `[patch]` table in the workspace root, neither of
//!   which this lint reads.
//! - **What a cast operates on.** `x as usize` is a pointer-to-integer cast only when `x`
//!   is a pointer, and the type is not in the token stream. Flagging every integer cast
//!   would bury real code in false positives, so the lint rejects the ways of obtaining a
//!   raw address instead. A pointer that arrives through a dependency's method and is then
//!   cast is not caught.
//! - **A `{:p}` built in pieces.** The pointer format spec is caught when the format
//!   string is one literal. `format!(concat!("{:", "p}"), x)` assembles it at expansion
//!   time, which is the macro gap above wearing a different hat.
//! - **A renamed or glob-imported root.** `use std as sys; sys::thread::spawn(..)`,
//!   `use std::*; thread::spawn(..)` and `use std::fmt::*; Pointer::fmt(..)` all defeat
//!   the `<root>::<name>` checks here, which match the spelled path and nothing else.
//!   Catching them means banning root renames and glob imports outright, which is a rule
//!   DETERMINISM.md does not state -- a decision for a human, not a guess by this lint.
//! - **Rules 6-8.** Iteration by stable ID, IDs that are not derived from name hashes, and
//!   justified `unsafe` are properties of meaning, not of spelling. `BTreeMap<NameHash, _>`
//!   reads perfectly and is still non-deterministic. The desync canary is what catches
//!   those, which is why DETERMINISM.md lists both and not this lint alone.

use proc_macro2::{Delimiter, Spacing, TokenStream, TokenTree};
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

/// What a token-level lint structurally cannot check, printed by `--help` so the gaps are
/// visible to whoever is trusting the exit code.
///
/// Condensed for the CLI; the module docs above carry the reasoning. Keep the two in step.
pub const KNOWN_GAPS: &str = "\
WHAT THIS CANNOT SEE (it lexes; it does not expand, resolve or type-check):
    macro-expanded tokens    a proc macro can synthesise `f64` after this lint has run.
                             `include!`, `env!` and build scripts are rejected, so the
                             cheap ways in are shut; the rest needs a dependency, and
                             those are allow-listed.
    dependency types         `blindside_content::Table` may alias `HashMap`. Only the three
                             crates above are scanned; blindside-content is an allowed
                             dependency of all of them and is not itself linted. And only
                             NAMES are checked: what `fixed` resolves to is settled by
                             Cargo.lock and any [patch] table, neither of which is read.
    what a cast operates on  `x as usize` is a pointer cast only if `x` is a pointer, and
                             the type is not in the token stream. Rejecting every integer
                             cast would cry wolf, so the COMMON ways of getting a raw
                             address are rejected instead: `*const`/`*mut`, `as_ptr`,
                             `addr_of`, `transmute`, `NonNull`. Others compile and pass --
                             a fn item `as usize`, `&raw const`, `as_ptr_range()`,
                             `alloc(..) as usize`, `transmute_copy`. An address-derived
                             value is a review item, not a lint item.
    `{:p}` spelled indirectly
                             the pointer format spec is caught only when it is spelled
                             `{:p}` inside one literal. Pieces joined by `concat!`, or a
                             string escape such as `{:\\x70}`, are not seen.
    a hostile manifest       Cargo.toml is read by a small hand-written reader. A `\\\"`
                             escape inside an earlier string, or a UTF-8 BOM before the
                             first header, blinds it to everything after -- a `[lib]`
                             path, a build script, a `package = ..` rename. This lint
                             guards against an honest author's accidents; a hostile
                             author is what code review is for.
    an allowed name at another source
                             `blindside-content = { path = \"../elsewhere\" }` names an
                             allowed dependency; what lives at that path is not read.
    a renamed or glob root   `use std as sys; sys::thread::spawn(..)`, `use std::*;
                             thread::spawn(..)`, `use std::fmt::*; Pointer::fmt(..)`.
                             Every path check here matches the spelled `<root>::<name>`.
                             Catching these means banning root renames and glob imports,
                             a rule DETERMINISM.md does not state.
    rules 6-8                iteration by stable ID, IDs not derived from name hashes,
                             justified `unsafe`. `BTreeMap<NameHash, _>` reads perfectly
                             and is still non-deterministic. The desync canary catches
                             those; this lint cannot.
";

/// Which DETERMINISM.md rule a finding violates.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Rule {
    /// Rule 1: no `f32`/`f64`, fixed-point only.
    Float,
    /// Rule 2: no `HashMap`/`HashSet` (unordered iteration).
    HashCollection,
    /// Rule 2/3: std's hashers, which are process-seeded or version-unstable.
    Hasher,
    /// Rule 3: no wall clock (`std::time`, `SystemTime`, `Instant`).
    WallClock,
    /// Rule 3: no address-derived values (raw pointers, `transmute`, `{:p}`).
    Address,
    /// Rule 3: no process or environment reads.
    Environment,
    /// Rule 4: no `rand`; RNG is counter-based and stateless.
    Rand,
    /// Rule 5: no threading inside a tick (`std::thread`, `rayon`).
    Thread,
    /// ARCHITECTURE.md: dependency tree must stay auditable.
    Dependency,
    /// Code linked into the crate from where this lint does not look.
    HiddenSource,
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
            Rule::Hasher => {
                "rule 2/3: std hashers are seeded per process (RandomState) or unstable \
                 across std versions (DefaultHasher); hash with blake3"
            }
            Rule::WallClock => "rule 3: no SystemTime/Instant/std::time",
            Rule::Address => "rule 3: no address-derived values; an address differs per run",
            Rule::Environment => {
                "rule 3: no process or environment reads; the machine is not a sim input"
            }
            Rule::Rand => "rule 4: no rand; RNG is draw(seed, tick, entity_id, purpose_id)",
            Rule::Thread => "rule 5: no threading inside a tick",
            Rule::Dependency => {
                "dependency tree: constrained crates may only depend on the allow-list"
            }
            Rule::HiddenSource => {
                "lint scope: code this lint would not read (the root is src/lib.rs, \
                 modules are .rs files under src/, there is no build script)"
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

/// Identifiers banned wherever they appear, whatever path leads to them.
const BANNED_IDENTS: [(&str, Rule); 19] = [
    ("f32", Rule::Float),
    ("f64", Rule::Float),
    ("HashMap", Rule::HashCollection),
    ("HashSet", Rule::HashCollection),
    ("SystemTime", Rule::WallClock),
    ("Instant", Rule::WallClock),
    ("rand", Rule::Rand),
    ("rayon", Rule::Thread),
    // std's hashers reach non-determinism without ever naming a HashMap. `RandomState` is
    // seeded from the OS once per process, so it answers differently on every run;
    // `DefaultHasher`'s algorithm is documented as unstable between std versions, so it
    // answers differently on a different toolchain. Replays outlive both. The state hash
    // is blake3 (PHASE-0-HARNESS.md).
    ("DefaultHasher", Rule::Hasher),
    ("RandomState", Rule::Hasher),
    ("SipHasher", Rule::Hasher),
    ("SipHasher13", Rule::Hasher),
    // Everything below yields a raw address or reinterprets one. Addresses differ on every
    // run, so any value derived from one desyncs. The lint cannot tell whether `x as usize`
    // casts a pointer (see KNOWN_GAPS), so it rejects the ways of getting a pointer rather
    // than trying to recognise the cast.
    ("as_ptr", Rule::Address),
    ("as_mut_ptr", Rule::Address),
    ("addr_of", Rule::Address),
    ("addr_of_mut", Rule::Address),
    ("into_raw", Rule::Address),
    ("transmute", Rule::Address),
    ("NonNull", Rule::Address),
];

/// `<root>::<module>` path prefixes that are banned regardless of what follows. Matched
/// both in a plain path (`std::time::Instant`) and across a braced use tree, where the
/// root sits outside the group (`use std::{time}`).
const BANNED_PATHS: [(&str, &str, Rule); 11] = [
    ("std", "time", Rule::WallClock),
    ("core", "time", Rule::WallClock),
    ("std", "thread", Rule::Thread),
    ("core", "thread", Rule::Thread),
    ("std", "ptr", Rule::Address),
    ("core", "ptr", Rule::Address),
    ("std", "process", Rule::Environment),
    ("std", "env", Rule::Environment),
    ("collections", "hash_map", Rule::Hasher),
    ("collections", "hash_set", Rule::Hasher),
    // `fmt::Pointer::fmt(&x, f)` writes an address without a format string. The bare
    // identifier is not banned: a VM is entitled to a type called `Pointer`.
    ("fmt", "Pointer", Rule::Address),
];

/// Macros banned at the invocation site, i.e. the identifier followed by `!`. Matching the
/// bare identifier would flag every local variable called `env`.
const BANNED_MACROS: [(&str, Rule); 3] = [
    ("include", Rule::HiddenSource),
    ("env", Rule::Environment),
    ("option_env", Rule::Environment),
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
    scan_stream(file, stream, None, &mut out);
    out
}

/// `use_prefix` is the path prefix in effect for this stream: `Some("std")` when the stream
/// is the `{...}` of `use std::{...}`, `None` everywhere else. It applies only at the start
/// of a comma-separated segment, which is where a use tree resumes the path.
fn scan_stream(file: &Path, stream: TokenStream, use_prefix: Option<&str>, out: &mut Vec<Finding>) {
    let tokens: Vec<TokenTree> = stream.into_iter().collect();
    // True at the first token and after every top-level `,`.
    let mut segment_start = true;
    for (i, tt) in tokens.iter().enumerate() {
        match tt {
            TokenTree::Group(g) => {
                if g.delimiter() == Delimiter::Bracket && follows_hash(&tokens, i) {
                    scan_attribute(file, g.stream(), out);
                } else {
                    let inner = match g.delimiter() {
                        Delimiter::Brace => brace_use_prefix(&tokens, i, use_prefix, segment_start),
                        _ => None,
                    };
                    scan_stream(file, g.stream(), inner.as_deref(), out);
                }
            }
            TokenTree::Ident(id) => {
                let written = id.to_string();
                let name = unraw(&written);
                let rule = banned_ident(name)
                    .or_else(|| banned_macro(&tokens, i, name))
                    .or_else(|| banned_path_tail(&tokens, i, name))
                    .or_else(|| match (segment_start, use_prefix) {
                        (true, Some(prefix)) => banned_pair(prefix, name),
                        _ => None,
                    });
                if let Some(rule) = rule {
                    out.push(finding(file, id.span(), &written, rule));
                }
            }
            TokenTree::Literal(lit) => {
                let text = lit.to_string();
                if is_float_literal(&text) && !is_tuple_index(&tokens, i) {
                    out.push(finding(file, lit.span(), &text, Rule::Float));
                }
                if let Some(spec) = pointer_format_spec(&text) {
                    out.push(finding(file, lit.span(), &spec, Rule::Address));
                }
            }
            TokenTree::Punct(p) => {
                // `*const T` / `*mut T`: a raw pointer type, and the usual first half of
                // `&x as *const _ as usize`. `const` and `mut` are keywords, so this pair
                // is never a multiplication -- bar the inline const block `x * const { 1 }`,
                // which sim code has no reason to write.
                if p.as_char() == '*' {
                    if let Some(TokenTree::Ident(next)) = tokens.get(i + 1) {
                        let n = next.to_string();
                        if n == "const" || n == "mut" {
                            out.push(finding(file, p.span(), &format!("*{n}"), Rule::Address));
                        }
                    }
                }
            }
        }
        segment_start = matches!(tt, TokenTree::Punct(p) if p.as_char() == ',');
    }
}

/// The body of a `#[...]` / `#![...]` attribute. Three attributes get special treatment;
/// everything else is scanned like any other token stream.
fn scan_attribute(file: &Path, body: TokenStream, out: &mut Vec<Finding>) {
    let tokens: Vec<TokenTree> = body.clone().into_iter().collect();
    let name = match tokens.first() {
        Some(TokenTree::Ident(id)) => unraw(&id.to_string()).to_string(),
        _ => {
            scan_stream(file, body, None, out);
            return;
        }
    };
    match name.as_str() {
        // `///` and `//!` arrive here as `#[doc = "..."]`. Prose: a doc comment that quotes
        // `{:p}` is not a pointer read, so the literal scan is not applied to it.
        "doc" => {}
        "path" => check_path_attribute(file, &tokens, out),
        // `cfg_attr(<predicate>, <attr>, <attr>, ..)`: each attribute after the predicate
        // is checked as if written on its own, so wrapping `path` in a `cfg_attr` -- or in
        // a `cfg_attr` inside a `cfg_attr` -- is not a way round check_path_attribute.
        "cfg_attr" => match tokens.get(1) {
            Some(TokenTree::Group(args)) => {
                let mut segments = split_on_commas(args.stream()).into_iter();
                if let Some(predicate) = segments.next() {
                    scan_stream(file, predicate, None, out);
                }
                for attr in segments {
                    scan_attribute(file, attr, out);
                }
            }
            _ => scan_stream(file, body, None, out),
        },
        _ => scan_stream(file, body, None, out),
    }
}

/// Split a stream on its top-level commas. Groups are single tokens here, so a comma
/// inside `all(a, b)` does not split.
fn split_on_commas(stream: TokenStream) -> Vec<TokenStream> {
    let mut segments = vec![TokenStream::new()];
    for tt in stream {
        if matches!(&tt, TokenTree::Punct(p) if p.as_char() == ',') {
            segments.push(TokenStream::new());
        } else if let Some(last) = segments.last_mut() {
            last.extend(std::iter::once(tt));
        }
    }
    segments
}

/// `r#f64` and `f64` name the same type: raw identifiers exist only so that keywords can be
/// used as names. Match on the unescaped form, or every banned token has a free alias.
fn unraw(written: &str) -> &str {
    written.strip_prefix("r#").unwrap_or(written)
}

fn banned_ident(name: &str) -> Option<Rule> {
    BANNED_IDENTS
        .iter()
        .find(|(n, _)| *n == name)
        .map(|(_, r)| *r)
        .or_else(|| name.starts_with("rand_").then_some(Rule::Rand))
}

fn banned_pair(root: &str, name: &str) -> Option<Rule> {
    BANNED_PATHS
        .iter()
        .find(|(r, m, _)| *r == root && *m == name)
        .map(|(_, _, rule)| *rule)
}

/// Banned when `tokens[i]` is a macro invocation: the identifier followed by `!`.
fn banned_macro(tokens: &[TokenTree], i: usize, name: &str) -> Option<Rule> {
    let bang = matches!(tokens.get(i + 1), Some(TokenTree::Punct(p)) if p.as_char() == '!');
    if !bang {
        return None;
    }
    BANNED_MACROS
        .iter()
        .find(|(n, _)| *n == name)
        .map(|(_, r)| *r)
}

/// If `tokens[i]` (named `name`) is the tail of `<root> :: <name>` for a banned pair,
/// return that pair's rule.
fn banned_path_tail(tokens: &[TokenTree], i: usize, name: &str) -> Option<Rule> {
    banned_pair(&path_root_before(tokens, i)?, name)
}

/// The identifier of a `<root> ::` immediately preceding `tokens[i]`, unescaped.
fn path_root_before(tokens: &[TokenTree], i: usize) -> Option<String> {
    if i < 3 {
        return None;
    }
    let is_colon = |t: &TokenTree| matches!(t, TokenTree::Punct(p) if p.as_char() == ':');
    if !(is_colon(&tokens[i - 1]) && is_colon(&tokens[i - 2])) {
        return None;
    }
    match &tokens[i - 3] {
        TokenTree::Ident(id) => Some(unraw(&id.to_string()).to_string()),
        _ => None,
    }
}

/// The path prefix that applies inside a brace group, when that group is the `{...}` of a
/// use tree: `use std::{time, thread}` gives `std` to both segments. A group that itself
/// opens a segment inherits the enclosing prefix, so `use std::{{thread}}` is not a way
/// round it either.
fn brace_use_prefix(
    tokens: &[TokenTree],
    i: usize,
    outer: Option<&str>,
    segment_start: bool,
) -> Option<String> {
    if let Some(root) = path_root_before(tokens, i) {
        return Some(root);
    }
    if segment_start {
        return outer.map(str::to_string);
    }
    None
}

/// True when `tokens[i]` is the `[...]` of an attribute: `#[..]` or `#![..]`.
fn follows_hash(tokens: &[TokenTree], i: usize) -> bool {
    let punct =
        |k: usize, c: char| matches!(tokens.get(k), Some(TokenTree::Punct(p)) if p.as_char() == c);
    if i >= 1 && punct(i - 1, '#') {
        return true;
    }
    i >= 2 && punct(i - 1, '!') && punct(i - 2, '#')
}

/// `#[path = "..."]` moves a module's file. This lint walks `<crate>/src` and reads the
/// `.rs` files in it, so a value that leaves `src`, or names a file with any other
/// extension, links code into a constrained crate that the walk never reads. A `.rs` value
/// inside `src` is fine: the walk finds those files whether or not a module declaration
/// names them. `tokens` is the attribute body, starting at the `path` identifier.
fn check_path_attribute(file: &Path, tokens: &[TokenTree], out: &mut Vec<Finding>) {
    let TokenTree::Ident(key) = &tokens[0] else {
        return;
    };
    let value: Vec<String> = tokens.iter().skip(2).map(ToString::to_string).collect();
    let written = value.join(" ");
    let is_eq = matches!(tokens.get(1), Some(TokenTree::Punct(p)) if p.as_char() == '=');
    // Anything but `path = "<one literal>"` is unreadable here -- `path = concat!(..)`, say
    // -- and unreadable is treated as escaping. The lint must not guess in the direction of
    // "probably fine".
    let readable = match (is_eq, value.as_slice()) {
        (true, [lit]) => string_literal_value(lit),
        _ => None,
    };
    let hidden = match readable {
        Some(p) => path_leaves_src(&p) || !p.ends_with(".rs"),
        None => true,
    };
    if hidden {
        out.push(finding(
            file,
            key.span(),
            &format!("#[path = {written}]"),
            Rule::HiddenSource,
        ));
    }
}

/// The text of a string literal token: `"a/b.rs"` -> `a/b.rs`, `r#"a"#` -> `a`. Only the
/// escapes a path can plausibly contain are undone; anything else returns `None`, and the
/// caller treats the attribute as unreadable rather than as harmless.
fn string_literal_value(token: &str) -> Option<String> {
    if let Some(rest) = token.strip_prefix('r') {
        let hashes = rest.len() - rest.trim_start_matches('#').len();
        let inner = rest[hashes..].strip_prefix('"')?;
        let close = format!("\"{}", "#".repeat(hashes));
        return Some(inner.strip_suffix(&close)?.to_string());
    }
    let body = token.strip_prefix('"')?.strip_suffix('"')?;
    let mut text = String::new();
    let mut chars = body.chars();
    while let Some(c) = chars.next() {
        if c != '\\' {
            text.push(c);
            continue;
        }
        match chars.next()? {
            '\\' => text.push('\\'),
            '"' => text.push('"'),
            _ => return None,
        }
    }
    Some(text)
}

/// True when a `#[path]` value can reach outside the crate's `src` directory: absolute, or
/// containing a `..` component. Windows separators and drive letters count.
fn path_leaves_src(p: &str) -> bool {
    let norm = p.replace('\\', "/");
    if norm.starts_with('/') {
        return true;
    }
    let b = norm.as_bytes();
    if b.len() >= 2 && b[1] == b':' && b[0].is_ascii_alphabetic() {
        return true; // C:/elsewhere/x.rs, C:elsewhere/x.rs
    }
    norm.split('/').any(|seg| seg == "..")
}

/// True when the literal at `tokens[i]` is a tuple index, not a number: `t.0.1` lexes as
/// Ident, `.`, Literal("0.1"). The `.` before a tuple index stands alone. In `..0.5` the
/// `.` before the literal is the second half of `..`, and the first half is Joint -- so a
/// check that only looked one token back took the end of every range for an index.
fn is_tuple_index(tokens: &[TokenTree], i: usize) -> bool {
    let dot = |k: usize| match tokens.get(k) {
        Some(TokenTree::Punct(p)) if p.as_char() == '.' => Some(p.spacing()),
        _ => None,
    };
    if i < 1 || dot(i - 1) != Some(Spacing::Alone) {
        return false;
    }
    !(i >= 2 && dot(i - 2) == Some(Spacing::Joint))
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

/// The first `{..:..p}` placeholder in a string literal token, if any: a format spec whose
/// type is `p` prints an address. `{{` is an escaped brace and is skipped. The type is the
/// last character of the spec, and no other part of a spec (fill needs an align after it,
/// width and precision end in a digit, `$` or `*`) can end in `p`, so this does not fire on
/// `{:>8}`, `{:#x}` or `{:p<5}`. Non-format strings that happen to contain `{:p}` are the
/// false positive; doc comments are exempted upstream, and that leaves prose in a `&str`
/// constant, which sim code has little reason to hold.
fn pointer_format_spec(token: &str) -> Option<String> {
    if !token.contains('"') {
        return None; // numeric or char literal
    }
    let chars: Vec<char> = token.chars().collect();
    let mut i = 0;
    while i < chars.len() {
        if chars[i] != '{' {
            i += 1;
            continue;
        }
        if chars.get(i + 1) == Some(&'{') {
            i += 2;
            continue;
        }
        let close = chars[i..].iter().position(|&c| c == '}')? + i;
        let inner: String = chars[i + 1..close].iter().collect();
        if let Some(colon) = inner.find(':') {
            if inner[colon + 1..].ends_with('p') {
                return Some(chars[i..=close].iter().collect());
            }
        }
        i = close + 1;
    }
    None
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

/// Check the crate's layout ([`check_layout`]), then walk `<crate_dir>/src` and scan every
/// `.rs` file, in sorted path order.
pub fn scan_crate_sources(crate_dir: &Path) -> Vec<Finding> {
    let mut out = check_layout(crate_dir);
    let src = crate_dir.join("src");
    let mut files = Vec::new();
    collect_rs_files(&src, &mut files);
    files.sort();
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
// Crate layout: is src/**/*.rs really the whole crate?
// ---------------------------------------------------------------------------------------

/// Everything the source walk assumes about where a crate's code is, checked against
/// `Cargo.toml` and the directory. Runs on every invocation, not only with `--check-all`:
/// a lint that scanned the wrong files would be worse than no lint.
///
/// - `[lib] path` / `[[bin]] path` move a target's root anywhere at all. Rather than follow
///   the value and everything it reaches, a constrained crate's root is `src/lib.rs`, full
///   stop, and the key is rejected whatever it says. Simpler, and honest about what the
///   walk covers.
/// - A build script runs arbitrary code before the crate compiles: it can emit `cfg`s,
///   link native libraries, or write source (which then needs the rejected `include!` to
///   reach it, but the point stands). Nothing in Phase 0 needs one, so `build.rs` and
///   `[package] build = ".."` are both rejected; `build = false` is fine.
/// - `src/lib.rs` must exist, or the walk has no crate root to speak of.
pub fn check_layout(crate_dir: &Path) -> Vec<Finding> {
    let manifest_path = crate_dir.join("Cargo.toml");
    let mut out = Vec::new();
    match std::fs::read_to_string(&manifest_path) {
        Ok(text) => {
            for item in toml_items(&text) {
                let TomlItem::KeyValue {
                    line,
                    table,
                    key,
                    value,
                } = item
                else {
                    continue;
                };
                let full: Vec<&str> = table.iter().chain(&key).map(String::as_str).collect();
                let relocated_root = match full.as_slice() {
                    ["lib", "path"] | ["bin", "path"] => true,
                    ["lib"] | ["bin"] => has_key_anywhere(&value, "path"),
                    _ => false,
                };
                let build_script = match full.as_slice() {
                    ["package", "build"] => value != "false",
                    ["package"] => inline_table_get(&value, "build").is_some_and(|v| v != "false"),
                    _ => false,
                };
                if relocated_root || build_script {
                    out.push(Finding {
                        file: manifest_path.clone(),
                        line,
                        column: 1,
                        token: format!("{} = {value}", full.join(".")),
                        rule: Rule::HiddenSource,
                    });
                }
            }
        }
        Err(e) => out.push(Finding {
            file: manifest_path.clone(),
            line: 0,
            column: 0,
            token: format!("read error: {e}"),
            rule: Rule::Unparseable,
        }),
    }
    let build_rs = crate_dir.join("build.rs");
    if build_rs.exists() {
        out.push(Finding {
            file: build_rs,
            line: 0,
            column: 0,
            token: "build.rs".to_string(),
            rule: Rule::HiddenSource,
        });
    }
    let lib_rs = crate_dir.join("src").join("lib.rs");
    if !lib_rs.is_file() {
        out.push(Finding {
            file: lib_rs,
            line: 0,
            column: 0,
            token: "missing; the crate root must be src/lib.rs".to_string(),
            rule: Rule::HiddenSource,
        });
    }
    out
}

// ---------------------------------------------------------------------------------------
// Manifest (Cargo.toml) reading
// ---------------------------------------------------------------------------------------

/// A line of a manifest that matters: a table header, or a `key = value` under one.
/// Deliberately not a TOML parser; the lint has no third-party dependencies beyond the
/// lexer. It knows enough TOML to not be fooled by the spellings Cargo accepts for the
/// same thing: `[a.b]` + `c = 1`, `[a]` + `b.c = 1`, `a.b.c = 1`, `a = { b = { c = 1 } }`.
#[derive(Clone, Debug, PartialEq, Eq)]
enum TomlItem {
    Header {
        line: usize,
        /// `[target.'cfg(unix)'.dependencies]` -> ["target", "cfg(unix)", "dependencies"];
        /// `[[bin]]` -> ["bin"].
        table: Vec<String>,
    },
    KeyValue {
        line: usize,
        table: Vec<String>,
        /// Dotted key, split: `fixed.package` -> ["fixed", "package"].
        key: Vec<String>,
        /// Raw value text, comment stripped and trimmed. A multi-line array is joined.
        value: String,
    },
}

fn toml_items(manifest: &str) -> Vec<TomlItem> {
    let mut items = Vec::new();
    let mut table: Vec<String> = Vec::new();
    let mut lines = manifest.lines().enumerate();
    while let Some((idx, raw)) = lines.next() {
        let line = strip_toml_comment(raw).trim().to_string();
        if line.is_empty() {
            continue;
        }
        if line.starts_with('[') {
            let header = line.trim_start_matches('[').trim_end_matches(']').trim(); // also [[bin]]
            table = split_toml_key(header);
            items.push(TomlItem::Header {
                line: idx + 1,
                table: table.clone(),
            });
            continue;
        }
        let Some(eq) = find_unquoted(&line, '=') else {
            continue;
        };
        let key = split_toml_key(line[..eq].trim());
        let mut value = line[eq + 1..].trim().to_string();
        // An array may close on a later line. Swallow those lines, or the `]` that closes it
        // reads as a table header and ends the section early -- hiding whatever follows.
        let mut depth = bracket_depth(&value);
        while depth > 0 {
            let Some((_, next)) = lines.next() else {
                break;
            };
            let next = strip_toml_comment(next).trim();
            value.push(' ');
            value.push_str(next);
            depth += bracket_depth(next);
        }
        items.push(TomlItem::KeyValue {
            line: idx + 1,
            table: table.clone(),
            key,
            value,
        });
    }
    items
}

/// The characters of `s` that sit outside single or double quotes, each with its byte
/// offset and its nesting depth in `[]`/`{}` at that point.
fn unquoted(s: &str) -> Vec<(usize, char, usize)> {
    let mut out = Vec::new();
    let mut in_str: Option<char> = None;
    let mut depth = 0usize;
    for (i, c) in s.char_indices() {
        match in_str {
            Some(q) if c == q => in_str = None,
            Some(_) => {}
            None if c == '"' || c == '\'' => in_str = Some(c),
            None => {
                if c == ']' || c == '}' {
                    depth = depth.saturating_sub(1);
                }
                out.push((i, c, depth));
                if c == '[' || c == '{' {
                    depth += 1;
                }
            }
        }
    }
    out
}

fn strip_toml_comment(line: &str) -> &str {
    match unquoted(line).iter().find(|(_, c, _)| *c == '#') {
        Some((i, _, _)) => &line[..*i],
        None => line,
    }
}

/// First `needle` in `s` outside quotes and outside any bracket or brace.
fn find_unquoted(s: &str, needle: char) -> Option<usize> {
    unquoted(s)
        .into_iter()
        .find(|(_, c, d)| *c == needle && *d == 0)
        .map(|(i, _, _)| i)
}

/// `[` minus `]` outside quotes: positive while an array is still open.
fn bracket_depth(s: &str) -> i32 {
    unquoted(s)
        .iter()
        .map(|(_, c, _)| match c {
            '[' => 1,
            ']' => -1,
            _ => 0,
        })
        .sum()
}

/// Split a dotted key or table header on `.` outside quotes, unquoting each segment:
/// `target.'cfg(unix)'.dependencies` -> ["target", "cfg(unix)", "dependencies"].
fn split_toml_key(key: &str) -> Vec<String> {
    split_top_level(key, '.')
        .into_iter()
        .map(|seg| unquote(seg.trim()))
        .collect()
}

/// Split on `sep` outside quotes and outside `[]`/`{}`.
fn split_top_level(s: &str, sep: char) -> Vec<&str> {
    let mut parts = Vec::new();
    let mut start = 0;
    for (i, c, depth) in unquoted(s) {
        if c == sep && depth == 0 {
            parts.push(&s[start..i]);
            start = i + c.len_utf8();
        }
    }
    parts.push(&s[start..]);
    parts
}

/// `"x"` or `'x'` -> `x`; anything else unchanged.
fn unquote(s: &str) -> String {
    let s = s.trim();
    for q in ['"', '\''] {
        if let Some(inner) = s.strip_prefix(q).and_then(|r| r.strip_suffix(q)) {
            return inner.to_string();
        }
    }
    s.to_string()
}

/// The entries of an inline table value `{ a = 1, b = "x" }`, as (key, raw value) pairs.
/// `None` when the value is not an inline table.
fn inline_table_entries(value: &str) -> Option<Vec<(String, String)>> {
    let body = value.trim().strip_prefix('{')?.strip_suffix('}')?;
    let mut out = Vec::new();
    for part in split_top_level(body, ',') {
        let Some(eq) = find_unquoted(part, '=') else {
            continue;
        };
        out.push((
            unquote(part[..eq].trim()),
            part[eq + 1..].trim().to_string(),
        ));
    }
    Some(out)
}

fn inline_table_get(value: &str, key: &str) -> Option<String> {
    inline_table_entries(value)?
        .into_iter()
        .find(|(k, _)| k == key)
        .map(|(_, v)| v)
}

/// True when `key =` appears anywhere in `value` outside quotes, at any nesting depth:
/// `[{ name = "x", path = "y" }]` has `path`. Used where the exact shape does not matter
/// because any occurrence is rejected.
fn has_key_anywhere(value: &str, key: &str) -> bool {
    let text: String = unquoted(value).iter().map(|(_, c, _)| *c).collect();
    let mut from = 0;
    while let Some(pos) = text[from..].find(key) {
        let at = from + pos;
        let before_ok = !text[..at]
            .chars()
            .next_back()
            .is_some_and(|c| c.is_alphanumeric() || c == '_' || c == '-');
        let after = text[at + key.len()..].trim_start();
        if before_ok && after.starts_with('=') {
            return true;
        }
        from = at + key.len();
    }
    false
}

/// A dependency declared in a manifest, with the line it was declared on.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DeclaredDependency {
    /// The name on the left of `=` (or in the `[<kind>.<key>]` header): what the crate
    /// calls it. Not necessarily what it is.
    pub key: String,
    /// `package = "..."`, when present: the crate actually pulled in. Cargo lets a manifest
    /// call `rand` `blake3`, and the allow-list is a list of packages, not of local names.
    pub package: Option<String>,
    /// `workspace = true`: the entry defers to `[workspace.dependencies]` in the workspace
    /// root, and `package` (if any) lives there.
    pub workspace: bool,
    pub line: usize,
    /// `dependencies`, `build-dependencies`, `dev-dependencies`, or `workspace` for an
    /// entry of `[workspace.dependencies]`.
    pub kind: String,
}

impl DeclaredDependency {
    /// The package this entry names, as far as this manifest alone can tell.
    pub fn crate_name(&self) -> &str {
        self.package.as_deref().unwrap_or(&self.key)
    }
}

/// Where in a full key path (`table` segments followed by `key` segments) a dependency
/// name sits, and under which kind. `[target.<cfg>.dependencies]` is skipped over;
/// `workspace.dependencies` is kind `workspace`.
fn dependency_position(full: &[String]) -> Option<(String, usize)> {
    let mut i = 0;
    if full.first().map(String::as_str) == Some("target") {
        i = 2;
    }
    let kind = match full.get(i).map(String::as_str) {
        Some("workspace") if full.get(i + 1).map(String::as_str) == Some("dependencies") => {
            i += 1;
            "workspace"
        }
        Some(k @ ("dependencies" | "build-dependencies" | "dev-dependencies")) => k,
        _ => return None,
    };
    Some((kind.to_string(), i + 1))
}

/// Collect every dependency a manifest declares, in every spelling Cargo accepts, and read
/// its `package` rename and `workspace = true` marker.
pub fn declared_dependencies(manifest: &str) -> Vec<DeclaredDependency> {
    let mut out: Vec<DeclaredDependency> = Vec::new();
    // Index of the entry for (kind, key), created at `line` if this is its first mention.
    fn entry(out: &mut Vec<DeclaredDependency>, kind: &str, key: &str, line: usize) -> usize {
        match out.iter().position(|d| d.kind == kind && d.key == key) {
            Some(i) => i,
            None => {
                out.push(DeclaredDependency {
                    key: key.to_string(),
                    package: None,
                    workspace: false,
                    line,
                    kind: kind.to_string(),
                });
                out.len() - 1
            }
        }
    }
    // What one dependency's value or field says about it.
    fn apply(dep: &mut DeclaredDependency, field: Option<&str>, value: &str) {
        match field {
            None => {
                if let Some(p) = inline_table_get(value, "package") {
                    dep.package = Some(unquote(&p));
                }
                if inline_table_get(value, "workspace").as_deref() == Some("true") {
                    dep.workspace = true;
                }
            }
            Some("package") => dep.package = Some(unquote(value)),
            Some("workspace") => dep.workspace = value == "true",
            _ => {}
        }
    }
    for item in toml_items(manifest) {
        match item {
            TomlItem::Header { line, table } => {
                let Some((kind, n)) = dependency_position(&table) else {
                    continue;
                };
                if let (Some(key), true) = (table.get(n), table.len() == n + 1) {
                    entry(&mut out, &kind, key, line);
                }
            }
            TomlItem::KeyValue {
                line,
                table,
                key,
                value,
            } => {
                let full: Vec<String> = table.iter().chain(&key).cloned().collect();
                let Some((kind, n)) = dependency_position(&full) else {
                    continue;
                };
                match full.get(n) {
                    Some(dep_key) => {
                        let i = entry(&mut out, &kind, dep_key, line);
                        apply(&mut out[i], full.get(n + 1).map(String::as_str), &value);
                    }
                    // `dependencies = { fixed = "1", .. }`: the table itself, inline.
                    None => {
                        for (dep_key, v) in inline_table_entries(&value).unwrap_or_default() {
                            let i = entry(&mut out, &kind, &dep_key, line);
                            apply(&mut out[i], None, &v);
                        }
                    }
                }
            }
        }
    }
    out
}

/// Something `--check-all` wants a human to see that is not a failure.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ManifestWarning {
    pub line: usize,
    pub message: String,
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct ManifestReport {
    pub findings: Vec<Finding>,
    pub warnings: Vec<ManifestWarning>,
}

/// Check `<crate_dir>/Cargo.toml` against [`ALLOWED_DEPENDENCIES`], by package name.
/// `[dev-dependencies]` are warnings (they never reach shipped sim code), as is a
/// `workspace = true` entry when no ancestor manifest declares a workspace to resolve it
/// against -- Cargo could not build that crate either, so nothing is being hidden, but the
/// name could not be checked and the output says so.
pub fn check_manifest(crate_dir: &Path) -> ManifestReport {
    let manifest_path = crate_dir.join("Cargo.toml");
    let mut report = ManifestReport::default();
    let text = match std::fs::read_to_string(&manifest_path) {
        Ok(t) => t,
        Err(e) => {
            report.findings.push(Finding {
                file: manifest_path,
                line: 0,
                column: 0,
                token: format!("read error: {e}"),
                rule: Rule::Unparseable,
            });
            return report;
        }
    };
    let deps = declared_dependencies(&text);
    let workspace = if deps.iter().any(|d| d.workspace) {
        find_workspace_manifest(crate_dir).and_then(|path| {
            let text = std::fs::read_to_string(&path).ok()?;
            let entries: Vec<DeclaredDependency> = declared_dependencies(&text)
                .into_iter()
                .filter(|d| d.kind == "workspace")
                .collect();
            Some((path, entries))
        })
    } else {
        None
    };
    for dep in deps {
        if dep.kind == "workspace" {
            continue; // the crate is itself a workspace root; not a dependency of it
        }
        let name = if dep.workspace {
            match &workspace {
                None => {
                    report.warnings.push(ManifestWarning {
                        line: dep.line,
                        message: format!(
                            "`{}` is `workspace = true` but no ancestor Cargo.toml has a \
                             [workspace] table, so the package it names cannot be checked here",
                            dep.key
                        ),
                    });
                    continue;
                }
                Some((ws_path, entries)) => match entries.iter().find(|w| w.key == dep.key) {
                    Some(w) => w.crate_name().to_string(),
                    None => {
                        report.findings.push(Finding {
                            file: manifest_path.clone(),
                            line: dep.line,
                            column: 1,
                            token: format!(
                                "{} (workspace = true, but {} does not declare it)",
                                dep.key,
                                ws_path.display()
                            ),
                            rule: Rule::Dependency,
                        });
                        continue;
                    }
                },
            }
        } else {
            dep.crate_name().to_string()
        };
        if ALLOWED_DEPENDENCIES.contains(&name.as_str()) {
            continue;
        }
        if dep.kind == "dev-dependencies" {
            report.warnings.push(ManifestWarning {
                line: dep.line,
                message: format!(
                    "dev-dependency `{name}` is not on the allow-list ({}); allowed for \
                     tests only",
                    ALLOWED_DEPENDENCIES.join(", ")
                ),
            });
            continue;
        }
        let token = if name == dep.key {
            format!("{name} ({})", dep.kind)
        } else {
            format!("{name} (as `{}`, {})", dep.key, dep.kind)
        };
        report.findings.push(Finding {
            file: manifest_path.clone(),
            line: dep.line,
            column: 1,
            token,
            rule: Rule::Dependency,
        });
    }
    report
}

// ---------------------------------------------------------------------------------------
// Workspace root discovery
// ---------------------------------------------------------------------------------------

/// The nearest `Cargo.toml` at or above `start` that declares a workspace: a `[workspace]`
/// or `[workspace.*]` table, or a `workspace.* = ..` key. This is how Cargo finds the root
/// when `package.workspace` is not set, which no crate here sets.
pub fn find_workspace_manifest(start: &Path) -> Option<PathBuf> {
    let mut dir = Some(start.to_path_buf());
    while let Some(d) = dir {
        let manifest = d.join("Cargo.toml");
        if let Ok(text) = std::fs::read_to_string(&manifest) {
            let declares = toml_items(&text).iter().any(|item| {
                let head = match item {
                    TomlItem::Header { table, .. } => table.first(),
                    TomlItem::KeyValue { table, key, .. } => table.first().or(key.first()),
                };
                head.map(String::as_str) == Some("workspace")
            });
            if declares {
                return Some(manifest);
            }
        }
        dir = d.parent().map(Path::to_path_buf);
    }
    None
}

/// Find the workspace root: walk up from `start` looking for a `Cargo.toml` that declares
/// a workspace; fall back to the root this binary was compiled in.
pub fn find_workspace_root(start: &Path) -> PathBuf {
    find_workspace_manifest(start)
        .and_then(|m| m.parent().map(Path::to_path_buf))
        .unwrap_or_else(|| Path::new(env!("CARGO_MANIFEST_DIR")).join("..").join(".."))
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
        assert!(scan("fn f(t: ((u8,u8),u8)) -> u8 { t.0 .1 }").is_empty());
    }

    #[test]
    fn range_end_is_not_a_tuple_index() {
        // `..` lexes as two `.` puncts, so the end of a range sits after a `.` just like a
        // tuple index does. The first half of `..` is Joint; a tuple-index `.` never is.
        assert_eq!(scan("fn f() { let _ = ..0.5; }")[0].2, "0.5");
        assert_eq!(scan("fn f() { let _ = 0..0.5; }")[0].2, "0.5");
        assert_eq!(scan("fn f() { let _ = ..=0.5; }")[0].2, "0.5");
        assert_eq!(scan("fn f(x: (u8, u8)) { let _ = x.0..0.5; }")[0].2, "0.5");
        // Integer ranges are still fine.
        assert!(scan("fn f() { for _ in 0..10 {} let _ = ..=5; }").is_empty());
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
    fn braced_use_trees_carry_the_root_into_every_segment() {
        // `use std::{thread, time};` -- the root sits outside the group, so a check that
        // only matched a flat `<root> :: <name>` sequence saw neither module.
        let f = scan("use std::{thread, time};");
        assert_eq!(f.len(), 2, "{f:?}");
        assert_eq!(f[0].3, Rule::Thread);
        assert_eq!(f[1].3, Rule::WallClock);
        assert_eq!(scan("use std::{time::Duration};")[0].3, Rule::WallClock);
        assert_eq!(scan("use std::{{thread}};")[0].3, Rule::Thread);
        assert_eq!(scan("use ::std::{env};")[0].3, Rule::Environment);
        // Our own braced imports are untouched: only banned <root>::<module> pairs match.
        assert!(scan("use crate::{Fx, Sim, world::World};").is_empty());
    }

    #[test]
    fn raw_identifiers_are_unescaped_before_matching() {
        assert_eq!(scan("pub struct S { pub x: r#f64 }")[0].3, Rule::Float);
        assert_eq!(scan("use r#rand::Rng;")[0].3, Rule::Rand);
        assert_eq!(scan("use r#std::r#thread::spawn;")[0].3, Rule::Thread);
        // Reported as written, so the token quoted in the finding is real source text.
        assert_eq!(scan("pub struct S { pub x: r#f64 }")[0].2, "r#f64");
    }

    #[test]
    fn pointer_format_specs_are_read_out_of_string_literals() {
        assert_eq!(
            scan("fn f(x: &u8) -> String { format!(\"{:p}\", x) }")[0].2,
            "{:p}"
        );
        assert_eq!(
            scan("fn f(x: &u8) -> String { format!(\"{x:#p}\") }")[0].2,
            "{x:#p}"
        );
        assert_eq!(
            scan("fn f(x: &u8) -> String { format!(\"{0:>16p}\", x) }")[0].2,
            "{0:>16p}"
        );
        assert_eq!(scan("const S: &str = r\"{:p}\";")[0].3, Rule::Address);
        // Escaped braces print the text `{:p}`; they read nothing.
        assert!(scan("const S: &str = \"{{:p}}\";").is_empty());
        // Other specs, and a `p` that is a fill character rather than the type.
        assert!(
            scan("const S: &str = \"{:?} {:#x} {:>8} {:p<5} {:08.3} {name} {:.*} {:>w$}\";")
                .is_empty()
        );
        // Doc comments are prose.
        assert!(scan("/// never write `{:p}` here\nfn f() {}").is_empty());
        assert!(scan("//! `{:p}` is banned\nfn f() {}").is_empty());
        // The trait path is caught; a type of our own called Pointer is not.
        assert_eq!(scan("use std::fmt::Pointer;")[0].3, Rule::Address);
        assert_eq!(scan("use std::fmt::{Pointer, Debug};")[0].3, Rule::Address);
        assert!(scan("pub struct Pointer(pub u32);").is_empty());
    }

    #[test]
    fn path_attribute_is_checked_through_cfg_attr_and_for_extension() {
        assert_eq!(
            scan("#[path = \"../x.rs\"] mod m;")[0].2,
            "#[path = \"../x.rs\"]"
        );
        assert_eq!(
            scan("#[cfg_attr(all(), path = \"../x.rs\")] mod m;")[0].2,
            "#[path = \"../x.rs\"]"
        );
        assert_eq!(
            scan(
                "#[cfg_attr(any(), cfg_attr(all(), allow(dead_code), path = \"../x.rs\"))] mod m;"
            )[0]
            .3,
            Rule::HiddenSource
        );
        assert_eq!(
            scan("#[path = \"gen.inc\"] mod m;")[0].3,
            Rule::HiddenSource
        );
        assert_eq!(scan("#[path = \"GEN.RS\"] mod m;")[0].3, Rule::HiddenSource);
        // A value the lint cannot read is not assumed harmless.
        assert_eq!(
            scan("#[path = concat!(\"a\", \".rs\")] mod m;")[0].3,
            Rule::HiddenSource
        );
        // Inside src, a .rs file, in either spelling: fine.
        assert!(scan("#[path = \"sub/mod.rs\"] mod m;").is_empty());
        assert!(scan("#[cfg_attr(unix, path = \"sub/unix.rs\")] mod m;").is_empty());
        assert!(scan("#[cfg(feature = \"std\")] mod m;").is_empty());
    }

    #[test]
    fn string_literal_forms_are_decoded_or_refused() {
        assert_eq!(
            string_literal_value("\"a/b.rs\"").as_deref(),
            Some("a/b.rs")
        );
        assert_eq!(
            string_literal_value("\"a\\\\b.rs\"").as_deref(),
            Some("a\\b.rs")
        );
        assert_eq!(
            string_literal_value("r#\"../x.rs\"#").as_deref(),
            Some("../x.rs")
        );
        // An escape a path has no business containing: unreadable, so refused.
        assert_eq!(string_literal_value("\"a\\u{2e}\\u{2e}/x\""), None);
        assert_eq!(string_literal_value("42"), None);
    }

    #[test]
    fn path_escape_test_covers_both_separators() {
        assert!(!path_leaves_src("sub/mod.rs"));
        assert!(!path_leaves_src("mod.rs"));
        assert!(path_leaves_src("../../elsewhere/mod.rs"));
        assert!(path_leaves_src("sub\\..\\..\\x.rs"));
        assert!(path_leaves_src("/etc/x.rs"));
        assert!(path_leaves_src("C:/elsewhere/x.rs"));
    }

    fn deps(m: &str) -> Vec<(String, Option<String>, bool, String)> {
        declared_dependencies(m)
            .into_iter()
            .map(|d| (d.key, d.package, d.workspace, d.kind))
            .collect()
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
        assert_eq!(
            deps(m),
            vec![
                ("fixed".into(), None, false, "dependencies".into()),
                ("blake3".into(), None, false, "dependencies".into()),
                ("serde".into(), None, false, "dependencies".into()),
                ("libc".into(), None, false, "dependencies".into()),
                ("proptest".into(), None, false, "dev-dependencies".into()),
                ("ignored".into(), None, false, "workspace".into()),
            ]
        );
    }

    #[test]
    fn manifest_parser_reads_package_renames_in_every_spelling() {
        let m = r#"
dependencies.a = { package = "rand", version = "0.8" }
dependencies.b.package = "rand_pcg"

[dependencies]
c = { version = "0.8", package = 'rayon' }
d.package = "rand_core"
d.version = "0.6"

[dependencies.e]
version = "1"
package = "rand_chacha"

[build-dependencies]
f = { package = "rand", features = [
    "std",
] }
g = "1"
"#;
        assert_eq!(
            deps(m),
            vec![
                (
                    "a".into(),
                    Some("rand".into()),
                    false,
                    "dependencies".into()
                ),
                (
                    "b".into(),
                    Some("rand_pcg".into()),
                    false,
                    "dependencies".into()
                ),
                (
                    "c".into(),
                    Some("rayon".into()),
                    false,
                    "dependencies".into()
                ),
                (
                    "d".into(),
                    Some("rand_core".into()),
                    false,
                    "dependencies".into()
                ),
                (
                    "e".into(),
                    Some("rand_chacha".into()),
                    false,
                    "dependencies".into()
                ),
                (
                    "f".into(),
                    Some("rand".into()),
                    false,
                    "build-dependencies".into()
                ),
                ("g".into(), None, false, "build-dependencies".into()),
            ]
        );
        // The inline-table spelling of the whole section.
        assert_eq!(
            deps("dependencies = { h = { package = \"rand\" }, fixed = \"1\" }"),
            vec![
                (
                    "h".into(),
                    Some("rand".into()),
                    false,
                    "dependencies".into()
                ),
                ("fixed".into(), None, false, "dependencies".into()),
            ]
        );
    }

    #[test]
    fn manifest_parser_reads_workspace_inheritance() {
        let m = "[dependencies]\nfixed = { workspace = true }\n[dependencies.blake3]\nworkspace = true\n";
        assert_eq!(
            deps(m),
            vec![
                ("fixed".into(), None, true, "dependencies".into()),
                ("blake3".into(), None, true, "dependencies".into()),
            ]
        );
    }

    #[test]
    fn inline_table_and_key_helpers() {
        assert_eq!(
            inline_table_get("{ a = 1, b = { c = 2, d = \"x, y\" } }", "b").as_deref(),
            Some("{ c = 2, d = \"x, y\" }")
        );
        assert_eq!(inline_table_get("\"1\"", "a"), None);
        assert!(has_key_anywhere("[{ name = \"x\", path = \"y\" }]", "path"));
        assert!(!has_key_anywhere("{ name = \"path = x\" }", "path"));
        assert!(!has_key_anywhere("{ subpath = \"x\" }", "path"));
        assert_eq!(strip_toml_comment("a = \"#\" # c"), "a = \"#\" ");
        assert_eq!(
            split_toml_key("target.'cfg(unix)'.dependencies"),
            vec!["target", "cfg(unix)", "dependencies"]
        );
    }
}
