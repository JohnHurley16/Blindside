//! Integration tests: run the real binary against (a) the real workspace and (b) throwaway
//! crates in a temp directory carrying one deliberate violation each.

use std::path::{Path, PathBuf};
use std::process::{Command, Output};

fn bin() -> Command {
    Command::new(env!("CARGO_BIN_EXE_determinism-lint"))
}

fn workspace_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("..").join("..")
}

fn stdout(o: &Output) -> String {
    String::from_utf8_lossy(&o.stdout).into_owned()
}

/// A fresh, empty temp directory. Caller removes it.
fn temp_dir(name: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "determinism-lint-test-{}-{}-{}",
        std::process::id(),
        name,
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

/// Write `content` at `dir/rel`, creating directories on the way.
fn write(dir: &Path, rel: &str, content: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, content).unwrap();
}

/// Build a one-file crate in a fresh temp dir. Returns the crate dir; caller removes it.
fn temp_crate(name: &str, lib_rs: &str, manifest_deps: &str) -> PathBuf {
    let dir = temp_dir(name);
    write(&dir, "src/lib.rs", lib_rs);
    write(
        &dir,
        "Cargo.toml",
        &format!(
            "[package]\nname = \"{name}\"\nversion = \"0.0.0\"\nedition = \"2021\"\n\n[dependencies]\n{manifest_deps}"
        ),
    );
    dir
}

#[test]
fn real_workspace_passes_with_check_all() {
    let out = bin()
        .arg("--root")
        .arg(workspace_root())
        .arg("--check-all")
        .output()
        .expect("run lint");
    let text = stdout(&out);
    assert!(
        out.status.success(),
        "lint should pass on the real workspace:\n{text}{}",
        String::from_utf8_lossy(&out.stderr)
    );
    assert!(
        text.contains("determinism-lint: OK -- 3 crate(s) clean"),
        "{text}"
    );
    // The real crates inherit `fixed` and `blake3` from the workspace root; inside the
    // workspace that resolves, so there is nothing to warn about.
    assert!(!text.contains("warning:"), "{text}");
}

#[test]
fn f64_field_fails_and_names_the_line() {
    let dir = temp_crate(
        "bad-f64",
        "//! A doc comment mentioning f64 must not count.\npub struct Pos {\n    pub x: f64,\n}\n",
        "fixed = \"1\"\n",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    let expected = format!(
        "{}:3:12: `f64` -- rule 1",
        dir.join("src").join("lib.rs").display()
    );
    assert!(
        text.contains(&expected),
        "expected `{expected}` in:\n{text}"
    );
    assert!(
        text.contains("FAIL -- 1 finding(s) in 1 file(s) across 1 of 1 crate(s)"),
        "{text}"
    );
}

#[test]
fn f64_appended_to_a_copy_of_blindside_sim_fails() {
    // Acceptance criterion 5 in miniature: copy the real crate, append a float fn, lint.
    let src_crate = workspace_root().join("crates").join("blindside-sim");
    let dir = temp_dir("sim-copy");
    std::fs::remove_dir_all(&dir).unwrap();
    copy_dir(&src_crate, &dir);
    let lib = dir.join("src").join("lib.rs");
    let mut text = std::fs::read_to_string(&lib).unwrap();
    if !text.ends_with('\n') {
        text.push('\n');
    }
    let line_of_bad = text.lines().count() + 1;
    text.push_str("pub fn bad() -> f64 { 0.0 }\n");
    std::fs::write(&lib, text).unwrap();

    let out = bin()
        .arg("--check-all")
        .arg(&dir)
        .output()
        .expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(
        text.contains(&format!("{}:{line_of_bad}:17: `f64`", lib.display())),
        "{text}"
    );
    assert!(
        text.contains(&format!("{}:{line_of_bad}:23: `0.0`", lib.display())),
        "{text}"
    );
    // The copy sits outside any workspace, so its `workspace = true` entries cannot be
    // resolved. That is a warning, not a finding: the two findings are the f64 and the 0.0.
    assert!(
        text.contains("warning: `fixed` is `workspace = true` but no ancestor Cargo.toml"),
        "{text}"
    );
    assert!(text.contains("FAIL -- 2 finding(s)"), "{text}");
}

#[test]
fn hashmap_iteration_fails_and_names_the_line() {
    let dir = temp_crate(
        "bad-hashmap",
        "use std::collections::BTreeMap;\n\npub fn total(m: &std::collections::HashMap<u32, u32>) -> u32 {\n    m.values().sum()\n}\n",
        "",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    let lib = dir.join("src").join("lib.rs");
    assert!(
        text.contains(&format!("{}:3:36: `HashMap` -- rule 2", lib.display())),
        "{text}"
    );
}

#[test]
fn std_time_fails_and_names_the_line() {
    let dir = temp_crate(
        "bad-time",
        "pub fn now() -> u64 {\n    let t = std::time::Instant::now();\n    let _ = t;\n    0\n}\n",
        "",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    let lib = dir.join("src").join("lib.rs");
    // Both the `std::time` path and the `Instant` identifier are reported.
    assert!(
        text.contains(&format!("{}:2:18: `time` -- rule 3", lib.display())),
        "{text}"
    );
    assert!(
        text.contains(&format!("{}:2:24: `Instant` -- rule 3", lib.display())),
        "{text}"
    );
    assert!(text.contains("FAIL -- 2 finding(s)"), "{text}");
}

#[test]
fn rand_use_fails() {
    let dir = temp_crate("bad-rand", "use rand::Rng;\n", "");
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(text.contains(":1:5: `rand` -- rule 4"), "{text}");
}

// ---------------------------------------------------------------------------------------
// Evasions. Each of these compiles, breaks determinism, and was accepted by the lint
// before the check named in the test.
// ---------------------------------------------------------------------------------------

/// EVASION: the grouped/brace import form. The path root sits outside the group, so a
/// check that only matched a flat `<root> :: <name>` sequence saw neither module.
#[test]
fn braced_use_tree_does_not_hide_std_thread_and_time() {
    let dir = temp_crate(
        "evade-brace-import",
        "use std::{thread, time};\n\npub fn go() {\n    let _ = (thread::yield_now, time::Duration::from_secs(1));\n}\n",
        "",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(text.contains(":1:11: `thread` -- rule 5"), "{text}");
    assert!(text.contains(":1:19: `time` -- rule 3"), "{text}");
}

/// EVASION: process-randomised or version-unstable hashing, reached without ever naming
/// `HashMap`. `RandomState` is seeded from the OS once per process.
#[test]
fn std_hashers_are_rejected_without_naming_hashmap() {
    let dir = temp_crate(
        "evade-hasher",
        "use std::collections::hash_map::DefaultHasher;\nuse std::hash::{BuildHasher, Hasher, RandomState};\n\npub fn h(x: u64) -> u64 {\n    RandomState::new().hash_one(x)\n}\n\npub fn h2(x: u64) -> u64 {\n    let mut d = DefaultHasher::new();\n    d.write_u64(x);\n    d.finish()\n}\n",
        "",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(text.contains(":1:23: `hash_map` -- rule 2/3"), "{text}");
    assert!(
        text.contains(":1:33: `DefaultHasher` -- rule 2/3"),
        "{text}"
    );
    assert!(text.contains(":2:38: `RandomState` -- rule 2/3"), "{text}");
    // The `Hash` trait and a `Hasher` bound are not the problem and are not flagged.
    assert!(!text.contains("`Hasher`"), "{text}");
}

/// EVASION: pointer-to-integer casts, whose value differs on every run. The lint cannot
/// see that `p as usize` casts a pointer -- `p`'s type is not in the token stream -- so it
/// rejects the ways of obtaining a raw address instead.
#[test]
fn pointer_to_integer_cast_ingredients_are_rejected() {
    let dir = temp_crate(
        "evade-pointer",
        "pub fn a(x: &u8) -> usize {\n    x as *const u8 as usize\n}\n\npub fn b(v: &[u8]) -> usize {\n    v.as_ptr() as usize\n}\n\npub fn c(v: &mut [u8]) -> usize {\n    v.as_mut_ptr() as usize\n}\n\npub fn d(x: &u32) -> usize {\n    unsafe { std::mem::transmute::<&u32, usize>(x) }\n}\n",
        "",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(text.contains(":2:10: `*const` -- rule 3"), "{text}");
    assert!(text.contains(":6:7: `as_ptr` -- rule 3"), "{text}");
    assert!(text.contains(":10:7: `as_mut_ptr` -- rule 3"), "{text}");
    assert!(text.contains(":14:24: `transmute` -- rule 3"), "{text}");
}

/// EVASION: an address read through a format string. `format!("{:p}", x)` never names a
/// pointer type or a pointer method, and string literals used to be opaque to the lint.
/// `fmt::Pointer::fmt` writes the same address with no format string at all.
#[test]
fn pointer_format_spec_in_a_string_literal_is_rejected() {
    let dir = temp_crate(
        "evade-format-pointer",
        "use std::fmt;\n\npub fn addr(x: &u32) -> String {\n    format!(\"{:p}\", x)\n}\n\npub fn addr2(x: &u32) -> String {\n    format!(\"at {x:#p}\")\n}\n\npub fn w(x: &u32, f: &mut fmt::Formatter<'_>) -> fmt::Result {\n    fmt::Pointer::fmt(&x, f)\n}\n",
        "",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(text.contains(":4:13: `{:p}` -- rule 3"), "{text}");
    assert!(text.contains(":8:13: `{x:#p}` -- rule 3"), "{text}");
    assert!(text.contains(":12:10: `Pointer` -- rule 3"), "{text}");
    assert!(text.contains("FAIL -- 3 finding(s)"), "{text}");
}

/// EVASION: reading the machine. `std::process::id()` is a different number in every run,
/// and `std::env` / `env!` make the build environment part of the result.
#[test]
fn process_and_environment_reads_are_rejected() {
    let dir = temp_crate(
        "evade-process",
        "pub fn pid() -> u32 {\n    std::process::id()\n}\n\npub fn home() -> String {\n    std::env::var(\"HOME\").unwrap_or_default()\n}\n\npub fn built_at() -> &'static str {\n    env!(\"PATH\")\n}\n",
        "",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(text.contains(":2:10: `process` -- rule 3"), "{text}");
    assert!(text.contains(":6:10: `env` -- rule 3"), "{text}");
    assert!(text.contains(":10:5: `env` -- rule 3"), "{text}");
}

/// BLD-22, last bullet: `std::fs`, `std::io`, `std::net` and `std::env` in blindside-sim
/// must fail the check. `env` is rule 3 above; the other three are ARCHITECTURE.md's "no
/// I/O", which is not one of DETERMINISM.md's numbered rules but is the same failure -- a
/// sim that reads a file or a socket has an input its replay does not carry, so a replay
/// reproduces only on a machine where that file says the same thing. Loading is
/// blindside-content's job, and it hands the sim a pack that is already in memory.
///
/// `std::fmt` is deliberately NOT banned: a `Display` impl writes into a formatter, not to
/// a device, and every error type in the crate needs one.
#[test]
fn file_socket_and_stream_io_are_rejected() {
    let dir = temp_crate(
        "evade-io",
        "use std::io::Read;\n\npub fn slurp() -> Vec<u8> {\n    std::fs::read(\"content.toml\").unwrap()\n}\n\npub fn listen() -> std::net::SocketAddr {\n    \"127.0.0.1:0\".parse().unwrap()\n}\n\npub fn take<R: Read>(mut r: R) -> usize {\n    let mut buf = Vec::new();\n    r.read_to_end(&mut buf).unwrap()\n}\n\nimpl std::fmt::Display for Ok2 {\n    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {\n        f.write_str(\"fine\")\n    }\n}\n\npub struct Ok2;\n",
        "",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(text.contains(":1:10: `io` -- no I/O"), "{text}");
    assert!(text.contains(":4:10: `fs` -- no I/O"), "{text}");
    assert!(text.contains(":7:25: `net` -- no I/O"), "{text}");
    // Three findings, not four or five: the `std::fmt` impl and the `Read` bound are not
    // I/O, and a lint that cried wolf on `Display` would be turned off within a week.
    assert!(text.contains("FAIL -- 3 finding(s)"), "{text}");
}

/// EVASION: raw identifiers. `r#f64` is the same type as `f64`; the escape exists only so
/// keywords can be used as names, and it renamed every banned token for free.
#[test]
fn raw_identifiers_do_not_hide_banned_tokens() {
    let dir = temp_crate(
        "evade-raw-ident",
        "pub struct Pos {\n    pub x: r#f64,\n}\n\npub fn spawn() {\n    r#std::r#thread::spawn(|| ());\n}\n",
        "",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    // Reported as written, so the quoted token is text that exists in the file.
    assert!(text.contains(":2:12: `r#f64` -- rule 1"), "{text}");
    assert!(text.contains(":6:12: `r#thread` -- rule 5"), "{text}");
}

/// EVASION: the end of a range. `..0.5` lexes as `.`, `.`, `0.5`, and the tuple-index
/// carve-out (`t.0.1` is Ident, `.`, Literal("0.1")) took any literal after a `.` for an
/// index -- so a float written as a range bound passed rule 1, the rule CI has an
/// acceptance test for.
#[test]
fn range_end_float_is_not_mistaken_for_a_tuple_index() {
    let dir = temp_crate(
        "evade-range-float",
        "pub fn in_unit(x: u64) -> bool {\n    let r = 0..0.5;\n    let e = ..0.5;\n    r.contains(&(x as _)) && e.contains(&(x as _))\n}\n",
        "",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(text.contains(":2:16: `0.5` -- rule 1"), "{text}");
    assert!(text.contains(":3:15: `0.5` -- rule 1"), "{text}");
    assert!(text.contains("FAIL -- 2 finding(s)"), "{text}");
}

/// EVASION: linking source the lint never reads. It walks `<crate>/src`, so a `#[path]`
/// that leaves `src` -- or an `include!` -- puts unlinted code in a constrained crate.
#[test]
fn source_pulled_in_from_outside_src_is_rejected() {
    let dir = temp_crate(
        "evade-hidden-source",
        "#[path = \"../../elsewhere/mod.rs\"]\nmod sneaky;\n\ninclude!(\"../../also_sneaky.rs\");\n\n// A path that stays inside src/ is fine: the walk reads those files anyway.\n#[path = \"sub/mod.rs\"]\nmod sub;\n",
        "",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(
        text.contains(":1:3: `#[path = \"../../elsewhere/mod.rs\"]` -- lint scope"),
        "{text}"
    );
    assert!(text.contains(":4:1: `include` -- lint scope"), "{text}");
    assert!(text.contains("FAIL -- 2 finding(s)"), "{text}");
}

/// EVASION: `#[path]` behind `cfg_attr`. The bare-attribute check looked for a group of
/// exactly three tokens, `path = "..."`; wrapping it as `#[cfg_attr(all(), path = "..")]`
/// gave the group a different shape and the same effect.
#[test]
fn cfg_attr_wrapped_path_attribute_is_rejected() {
    let dir = temp_crate(
        "evade-cfg-attr-path",
        "#[cfg_attr(all(), path = \"../../elsewhere/real.rs\")]\nmod sneaky;\n\n#[cfg_attr(any(), cfg_attr(all(), allow(dead_code), path = \"../also.rs\"))]\nmod nested;\n\n#[cfg_attr(unix, path = \"sub/unix.rs\")]\nmod fine;\n",
        "",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(
        text.contains(":1:19: `#[path = \"../../elsewhere/real.rs\"]` -- lint scope"),
        "{text}"
    );
    assert!(
        text.contains(":4:53: `#[path = \"../also.rs\"]` -- lint scope"),
        "{text}"
    );
    assert!(text.contains("FAIL -- 2 finding(s)"), "{text}");
}

/// EVASION: `#[path = "gen.inc"]`. The value stays inside src/, so the escape check let it
/// through, but the walk collects only `*.rs`, so the file was never read.
#[test]
fn path_attribute_to_a_non_rs_file_is_rejected() {
    let dir = temp_crate(
        "evade-path-extension",
        "#[path = \"gen.inc\"]\nmod gen;\n\n#[path = \"GEN.RS\"]\nmod gen2;\n",
        "",
    );
    // Real code, in a file the walk does not open.
    write(&dir, "src/gen.inc", "pub fn bad() -> f64 { 0.0 }\n");
    write(&dir, "src/GEN.RS", "pub fn bad2() -> f64 { 0.0 }\n");
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(
        text.contains(":1:3: `#[path = \"gen.inc\"]` -- lint scope"),
        "{text}"
    );
    assert!(
        text.contains(":4:3: `#[path = \"GEN.RS\"]` -- lint scope"),
        "{text}"
    );
}

/// EVASION: `[lib] path = "real/lib.rs"` in Cargo.toml moves the crate root out of src/,
/// and a one-line decoy in src/ kept the "no .rs files" guard quiet. The lint scanned the
/// decoy and nothing else.
#[test]
fn lib_or_bin_path_relocating_the_crate_root_is_rejected() {
    let dir = temp_dir("evade-lib-path");
    write(&dir, "src/decoy.rs", "pub fn ok() {}\n");
    write(&dir, "real/lib.rs", "pub fn bad() -> f64 { 0.0 }\n");
    write(
        &dir,
        "Cargo.toml",
        "[package]\nname = \"evade-lib-path\"\nversion = \"0.0.0\"\nedition = \"2021\"\n\n[lib]\npath = \"real/lib.rs\"\n\n[dependencies]\n",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(
        text.contains("Cargo.toml:7:1: `lib.path = \"real/lib.rs\"` -- lint scope"),
        "{text}"
    );
    assert!(
        text.contains("lib.rs:0:0: `missing; the crate root must be src/lib.rs` -- lint scope"),
        "{text}"
    );

    // `[[bin]]` with a path, and the root-level inline spelling of `[lib]` (which TOML
    // only allows before the first header), are the same hole.
    let dir = temp_dir("evade-bin-path");
    write(&dir, "src/lib.rs", "pub fn ok() {}\n");
    write(
        &dir,
        "Cargo.toml",
        "lib = { path = \"real/lib.rs\" }\n\n[package]\nname = \"evade-bin-path\"\nversion = \"0.0.0\"\nedition = \"2021\"\n\n[[bin]]\nname = \"x\"\npath = \"real/main.rs\"\n",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(
        text.contains("Cargo.toml:1:1: `lib = { path = \"real/lib.rs\" }` -- lint scope"),
        "{text}"
    );
    assert!(
        text.contains("Cargo.toml:10:1: `bin.path = \"real/main.rs\"` -- lint scope"),
        "{text}"
    );
    assert!(text.contains("FAIL -- 2 finding(s)"), "{text}");
}

/// EVASION: a build script. `build.rs` was never scanned, and it runs before the crate
/// compiles -- emitting cfgs, linking native code, writing source. Rejected outright:
/// nothing in Phase 0 needs one, and scanning it would not cover what it does at runtime.
#[test]
fn build_script_is_rejected() {
    let dir = temp_crate("evade-build-rs", "pub fn ok() {}\n", "");
    write(
        &dir,
        "build.rs",
        "fn main() { println!(\"cargo:rustc-env=SEED={}\", std::process::id()); }\n",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(
        text.contains("build.rs:0:0: `build.rs` -- lint scope"),
        "{text}"
    );

    // The manifest key that points at a script by another name.
    let dir = temp_dir("evade-build-key");
    write(&dir, "src/lib.rs", "pub fn ok() {}\n");
    write(&dir, "gen.rs", "fn main() {}\n");
    write(
        &dir,
        "Cargo.toml",
        "[package]\nname = \"evade-build-key\"\nversion = \"0.0.0\"\nedition = \"2021\"\nbuild = \"gen.rs\"\n",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(
        text.contains("Cargo.toml:5:1: `package.build = \"gen.rs\"` -- lint scope"),
        "{text}"
    );

    // `build = false` is the opposite: it switches auto-detection off, and is fine.
    let dir = temp_dir("build-false");
    write(&dir, "src/lib.rs", "pub fn ok() {}\n");
    write(
        &dir,
        "Cargo.toml",
        "[package]\nname = \"build-false\"\nversion = \"0.0.0\"\nedition = \"2021\"\nbuild = false\n",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert!(out.status.success(), "{text}");
}

/// EVASION: `package = "rand"`. Cargo lets a manifest call a crate by any name; the
/// dependency check keyed on the local name and never read the package field, so
/// `blake3 = { package = "rand" }` was on the allow-list. Three spellings, one hole.
#[test]
fn renamed_package_dependency_is_checked_by_its_real_name() {
    let dir = temp_dir("evade-package-rename");
    write(&dir, "src/lib.rs", "pub fn ok() {}\n");
    write(
        &dir,
        "Cargo.toml",
        "dependencies.blindside-content = { package = \"rand_pcg\", version = \"0.3\" }\n\n[package]\nname = \"evade-package-rename\"\nversion = \"0.0.0\"\nedition = \"2021\"\n\n[dependencies]\nblake3 = { package = \"rand\", version = \"0.8\" }\nfixed.package = \"rand_chacha\"\nfixed.version = \"0.3\"\n\n[dependencies.blindside-vm]\nversion = \"1\"\npackage = \"rayon\"\n",
    );
    // Without --check-all the manifest's dependencies are not inspected (the layout is).
    let out = bin().arg(&dir).output().expect("run lint");
    assert!(out.status.success(), "{}", stdout(&out));
    let out = bin()
        .arg("--check-all")
        .arg(&dir)
        .output()
        .expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(
        text.contains(
            "Cargo.toml:1:1: `rand_pcg (as `blindside-content`, dependencies)` -- dependency tree"
        ),
        "{text}"
    );
    assert!(
        text.contains("Cargo.toml:9:1: `rand (as `blake3`, dependencies)` -- dependency tree"),
        "{text}"
    );
    assert!(
        text.contains(
            "Cargo.toml:10:1: `rand_chacha (as `fixed`, dependencies)` -- dependency tree"
        ),
        "{text}"
    );
    assert!(
        text.contains(
            "Cargo.toml:13:1: `rayon (as `blindside-vm`, dependencies)` -- dependency tree"
        ),
        "{text}"
    );
    assert!(text.contains("FAIL -- 4 finding(s)"), "{text}");
}

/// The fourth spelling of the same hole: `fixed = { workspace = true }` in the crate and
/// `fixed = { package = "rand" }` in the workspace root. Resolved the way Cargo resolves
/// it, through the nearest ancestor manifest that declares a workspace.
#[test]
fn workspace_inherited_dependency_is_resolved_to_its_package() {
    let ws = temp_dir("evade-workspace-rename");
    let member = ws.join("member");
    write(&member, "src/lib.rs", "pub fn ok() {}\n");
    write(
        &member,
        "Cargo.toml",
        "[package]\nname = \"member\"\nversion = \"0.0.0\"\nedition = \"2021\"\n\n[dependencies]\nfixed = { workspace = true }\nblake3.workspace = true\nmissing = { workspace = true }\n",
    );
    write(
        &ws,
        "Cargo.toml",
        "[workspace]\nmembers = [\n    \"member\",\n]\n\n[workspace.dependencies]\nfixed = { package = \"rand\", version = \"0.8\" }\nblake3 = \"1\"\n",
    );
    let out = bin()
        .arg("--check-all")
        .arg(&member)
        .output()
        .expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&ws).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(
        text.contains("Cargo.toml:7:1: `rand (as `fixed`, dependencies)` -- dependency tree"),
        "{text}"
    );
    // `blake3` resolves to blake3 and is fine; `missing` is not declared by the workspace.
    assert!(!text.contains("`blake3"), "{text}");
    assert!(
        text.contains("Cargo.toml:9:1: `missing (workspace = true, but "),
        "{text}"
    );
    assert!(text.contains("FAIL -- 2 finding(s)"), "{text}");

    // No workspace above: cannot be resolved, so it is said, and not counted as a finding
    // (Cargo could not build this crate either).
    let dir = temp_crate(
        "workspace-orphan",
        "pub fn ok() {}\n",
        "fixed = { workspace = true }\n",
    );
    let out = bin()
        .arg("--check-all")
        .arg(&dir)
        .output()
        .expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert!(out.status.success(), "{text}");
    assert!(
        text.contains("Cargo.toml:7:1: warning: `fixed` is `workspace = true` but no ancestor Cargo.toml has a [workspace] table"),
        "{text}"
    );
}

/// The tightened checks must not fire on ordinary sim code. A lint that cries wolf gets
/// disabled, which costs more than the evasions it closed. Every idiom here is one the
/// checks above come close to: deterministic hashing next to the banned hashers, tuple
/// indexes and integer ranges next to the float-literal check, `env` as a name next to the
/// `env!` check, an in-src `#[path]` and a `cfg` next to the attribute checks, banned words
/// in a string next to the `{:p}` scan, and every allowed-dependency spelling next to the
/// rename check.
#[test]
fn tightened_checks_do_not_fire_on_ordinary_code() {
    let dir = temp_dir("clean-after-tightening");
    write(
        &dir,
        "src/lib.rs",
        "use std::collections::BTreeMap;\nuse std::hash::{Hash, Hasher};\nuse crate::{Fx, Tick};\n\n#[path = \"sub/mod.rs\"]\nmod sub;\nmod hash;\n\n#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]\npub struct AgentId(pub u32);\n\n#[cfg(feature = \"std\")]\npub struct Pointer(pub u32);\n\npub type Fx = u64;\npub struct Tick(pub u64);\n\npub fn count(m: &BTreeMap<AgentId, u32>) -> u32 {\n    m.len() as u32\n}\n\npub fn digest(bytes: &[u8]) -> [u8; 32] {\n    let mut h = blake3::Hasher::new();\n    h.update(bytes);\n    *h.finalize().as_bytes()\n}\n\npub fn feed<H: Hasher>(h: &mut H, id: AgentId) {\n    id.hash(h)\n}\n\npub fn scale(a: u64, b: u64) -> u64 {\n    a * b + a * 2\n}\n\npub fn nth(t: ((u8, u8), u8)) -> u8 {\n    t.0 .1\n}\n\npub fn first(t: ((u8, u8), u8)) -> u8 {\n    t.0.0\n}\n\npub fn ranges(n: u64) -> u64 {\n    let mut total = 0;\n    for i in 0..10 {\n        total += i;\n    }\n    let low = ..=5;\n    if low.contains(&n) && (0..=5).contains(&n) {\n        total += n;\n    }\n    total\n}\n\npub fn env_len(env: &str, environment: &[u8]) -> usize {\n    env.len() + environment.len()\n}\n\npub const WHY: &str = \"f64 HashMap std::time rand\";\npub const SPEC: &str = \"{{:p}} is an escaped brace; {:?} {:#x} {:>8} {:p<5} are not pointer specs\";\n",
    );
    write(&dir, "src/sub/mod.rs", "pub fn sub() {}\n");
    write(&dir, "src/hash.rs", "pub fn hash() {}\n");
    write(
        &dir,
        "Cargo.toml",
        "[package]\nname = \"clean-after-tightening\"\nversion = \"0.0.0\"\nedition = \"2021\"\nbuild = false\n\n[dependencies]\nfixed = \"1\"\nblake3 = { version = \"1\", default-features = false, features = [\n    \"std\",\n] }\nblindside-content.path = \"../blindside-content\"\n\n[dependencies.blindside-vm]\npath = \"../blindside-vm\"\n",
    );
    let out = bin()
        .arg("--check-all")
        .arg(&dir)
        .output()
        .expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert!(out.status.success(), "{text}");
    assert!(!text.contains("warning:"), "{text}");
}

/// The gaps are part of the product. If `--help` stops naming them, someone will read a
/// clean exit as "this crate is deterministic", which is not what was checked.
#[test]
fn help_and_summary_state_what_the_lint_cannot_see() {
    let out = bin().arg("--help").output().expect("run lint");
    let text = stdout(&out);
    assert!(text.contains("WHAT THIS CANNOT SEE"), "{text}");
    for gap in [
        "macro-expanded tokens",
        "dependency types",
        "what a cast operates on",
        "`{:p}` spelled indirectly",
        "a renamed or glob root",
        "a hostile manifest",
        "an allowed name at another source",
        "rules 6-8",
    ] {
        assert!(text.contains(gap), "--help is missing `{gap}`:\n{text}");
    }

    let out = bin()
        .arg("--root")
        .arg(workspace_root())
        .output()
        .expect("run lint");
    let summary = stdout(&out);
    assert!(
        summary.contains(
            "determinism-lint: token-level check; not seen: macro expansion, dependency \
             contents, most pointer casts, indirect `{:p}`, `use std as sys` / glob \
             roots, a hostile manifest, rules 6-8 (`--help` has the list)."
        ),
        "{summary}"
    );
}

#[test]
fn comments_strings_and_docs_do_not_false_positive() {
    let dir = temp_crate(
        "clean",
        "//! f64 HashMap std::time rand in a crate doc.\n\n/// `Instant` and `HashSet` in a doc comment, and `{:p}` too.\n// f32 in a line comment\n/* SystemTime in a block comment */\npub const WHY: &str = \"f64 HashMap std::time::Instant rand rayon\";\n",
        "fixed = \"1\"\n",
    );
    let out = bin()
        .arg("--check-all")
        .arg(&dir)
        .output()
        .expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert!(out.status.success(), "{text}");
}

#[test]
fn check_all_rejects_unexpected_dependency() {
    let dir = temp_crate(
        "bad-dep",
        "pub fn ok() {}\n",
        "fixed = \"1\"\nrand = \"0.8\"\n\n[dev-dependencies]\nproptest = \"1\"\n",
    );
    // Without --check-all the manifest's dependencies are not inspected.
    let out = bin().arg(&dir).output().expect("run lint");
    assert!(out.status.success(), "{}", stdout(&out));
    // With it, `rand` is a finding -- and so is the `proptest` dev-dependency: the
    // dependency check covers [dev-dependencies] too (BLD-25), so the rand ban is one
    // rule and tests take their randomness from blindside_sim::testing.
    let out = bin()
        .arg("--check-all")
        .arg(&dir)
        .output()
        .expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(
        text.contains("Cargo.toml:8:1: `rand (dependencies)` -- dependency tree"),
        "{text}"
    );
    assert!(
        text.contains("Cargo.toml:11:1: `proptest (dev-dependencies)` -- dependency tree"),
        "{text}"
    );
    assert!(!text.contains("warning:"), "{text}");
    assert!(text.contains("FAIL -- 2 finding(s)"), "{text}");
}

/// BLD-35 / BLD-21: the injection fixture's `HashMap` is exempt only inside an item that
/// carries `#[cfg(feature = "inject-desync")]`. Everything around it is still caught.
#[test]
fn inject_desync_cfg_exempts_hashmap_only_inside_the_gated_item() {
    let dir = temp_crate(
        "inject-exemption",
        concat!(
            "use std::collections::BTreeMap;\n",
            "\n",
            "/// The fixture: exempt.\n",
            "#[cfg(feature = \"inject-desync\")]\n",
            "pub fn inject() -> u64 {\n",
            "    let mut m: std::collections::HashMap<u64, u64> = std::collections::HashMap::new();\n",
            "    m.insert(1, 2);\n",
            "    m.keys().sum()\n",
            "}\n",
            "\n",
            "// Outside any gated item: caught (line 12).\n",
            "pub fn outside() -> usize {\n",
            "    let m: std::collections::HashMap<u64, u64> = std::collections::HashMap::new();\n",
            "    m.len()\n",
            "}\n",
            "\n",
            "// A gated MODULE is a path, not an item body: caught (line 20).\n",
            "#[cfg(feature = \"inject-desync\")]\n",
            "pub mod gated {\n",
            "    pub fn f() -> usize { std::collections::HashMap::<u64, u64>::new().len() }\n",
            "}\n",
            "\n",
            "// Another feature: caught (line 25).\n",
            "#[cfg(feature = \"other\")]\n",
            "pub fn other() -> usize { std::collections::HashSet::<u64>::new().len() }\n",
            "\n",
            "// The exemption is rule 2 only: a float in the fixture is caught (line 29).\n",
            "#[cfg(feature = \"inject-desync\")]\n",
            "pub fn floaty() -> f64 { 0.0 }\n",
            "\n",
            "// Two attributes, the cfg first: still the same item, still exempt.\n",
            "#[cfg(feature = \"inject-desync\")]\n",
            "#[allow(dead_code)]\n",
            "fn two_attrs(m: &std::collections::HashMap<u64, u64>) -> usize { m.len() }\n",
            "\n",
            "// A gated `use` ends at its `;`: exempt, and the next item is not (line 39).\n",
            "#[cfg(feature = \"inject-desync\")]\n",
            "use std::collections::HashMap as Fixture;\n",
            "pub fn after_use() -> usize { std::collections::HashMap::<u64, u64>::new().len() }\n",
            "\n",
            "pub fn fine(m: &BTreeMap<u64, u64>) -> usize { m.len() }\n",
        ),
        "",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(text.contains(":13:30: `HashMap` -- rule 2"), "{text}");
    assert!(text.contains(":13:68: `HashMap` -- rule 2"), "{text}");
    assert!(text.contains(":20:45: `HashMap` -- rule 2"), "{text}");
    assert!(text.contains(":25:45: `HashSet` -- rule 2"), "{text}");
    assert!(text.contains(":29:20: `f64` -- rule 1"), "{text}");
    assert!(text.contains(":29:26: `0.0` -- rule 1"), "{text}");
    assert!(text.contains(":39:49: `HashMap` -- rule 2"), "{text}");
    // Lines 6 (twice), 34 and 38 are the exempt ones.
    for exempt in [":6:", ":34:", ":38:"] {
        assert!(!text.contains(exempt), "exempt line reported:\n{text}");
    }
    assert!(text.contains("FAIL -- 7 finding(s)"), "{text}");

    // A file-level `#![cfg(feature = "inject-desync")]` is a module path in disguise and
    // exempts nothing.
    let dir = temp_crate(
        "inject-inner-cfg",
        "#![cfg(feature = \"inject-desync\")]\n\npub fn f() -> usize {\n    std::collections::HashMap::<u64, u64>::new().len()\n}\n",
        "",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(text.contains(":4:23: `HashMap` -- rule 2"), "{text}");
}

/// BLD-34: `unsafe` and `#[allow(unsafe_code)]` need a `// SAFETY:` line directly above;
/// a crate-wide allow is never a justification. The pass case and the fail case.
#[test]
fn unsafe_without_a_safety_line_fails_and_with_one_passes() {
    // Pass: every unsafe is justified. The SAFETY line sits above the attribute and is
    // shared by the `unsafe fn` under it; a multi-line comment block counts as long as one
    // of its lines is the SAFETY line.
    let dir = temp_crate(
        "unsafe-justified",
        concat!(
            "#![deny(unsafe_code)]\n",
            "\n",
            "// SAFETY: the pointer is derived from a live reference two lines up.\n",
            "#[allow(unsafe_code)]\n",
            "pub unsafe fn read(p: &u8) -> u8 {\n",
            "    *p\n",
            "}\n",
            "\n",
            "pub fn call() -> u8 {\n",
            "    let x = 7;\n",
            "    // Justification spans lines.\n",
            "    // SAFETY: `read` only dereferences the reference it is given.\n",
            "    #[allow(unsafe_code)]\n",
            "    let v = unsafe { read(&x) };\n",
            "    v\n",
            "}\n",
        ),
        "",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert!(out.status.success(), "{text}");

    // Fail: the same code with the SAFETY lines removed, and a blanket allow.
    let dir = temp_crate(
        "unsafe-unjustified",
        concat!(
            "#![allow(unsafe_code)]\n",
            "\n",
            "// Not a SAFETY line.\n",
            "#[allow(unsafe_code)]\n",
            "pub unsafe fn read(p: &u8) -> u8 {\n",
            "    *p\n",
            "}\n",
            "\n",
            "pub fn call() -> u8 {\n",
            "    let x = 7;\n",
            "    // SAFETY: this line is not directly above; code intervenes.\n",
            "    let y = x;\n",
            "    let v = unsafe { read(&y) };\n",
            "    v\n",
            "}\n",
        ),
        "",
    );
    let out = bin().arg(&dir).output().expect("run lint");
    let text = stdout(&out);
    std::fs::remove_dir_all(&dir).ok();
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(
        text.contains(":1:3: `#![allow(unsafe_code)]` -- rule 8"),
        "{text}"
    );
    assert!(
        text.contains(":4:2: `#[allow(unsafe_code)]` -- rule 8"),
        "{text}"
    );
    assert!(text.contains(":5:5: `unsafe` -- rule 8"), "{text}");
    assert!(text.contains(":13:13: `unsafe` -- rule 8"), "{text}");
    assert!(text.contains("FAIL -- 4 finding(s)"), "{text}");
}

#[test]
fn missing_crate_dir_is_a_usage_error() {
    let out = bin()
        .arg(std::env::temp_dir().join("does-not-exist-determinism-lint"))
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(2));
}

fn copy_dir(from: &Path, to: &Path) {
    std::fs::create_dir_all(to).unwrap();
    for entry in std::fs::read_dir(from).unwrap().flatten() {
        let p = entry.path();
        let dest = to.join(entry.file_name());
        if p.is_dir() {
            copy_dir(&p, &dest);
        } else {
            std::fs::copy(&p, &dest).unwrap();
        }
    }
}
