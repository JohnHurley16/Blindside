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

/// Build a one-file crate in a fresh temp dir. Returns the crate dir; caller removes it.
fn temp_crate(name: &str, lib_rs: &str, manifest_deps: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "determinism-lint-test-{}-{}-{}",
        std::process::id(),
        name,
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir_all(dir.join("src")).unwrap();
    std::fs::write(dir.join("src/lib.rs"), lib_rs).unwrap();
    std::fs::write(
        dir.join("Cargo.toml"),
        format!(
            "[package]\nname = \"{name}\"\nversion = \"0.0.0\"\nedition = \"2021\"\n\n[dependencies]\n{manifest_deps}"
        ),
    )
    .unwrap();
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
    let dir = temp_crate("sim-copy", "", "");
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

#[test]
fn comments_strings_and_docs_do_not_false_positive() {
    let dir = temp_crate(
        "clean",
        "//! f64 HashMap std::time rand in a crate doc.\n\n/// `Instant` and `HashSet` in a doc comment.\n// f32 in a line comment\n/* SystemTime in a block comment */\npub const WHY: &str = \"f64 HashMap std::time::Instant rand rayon\";\n",
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
    // Without --check-all the manifest is not inspected.
    let out = bin().arg(&dir).output().expect("run lint");
    assert!(out.status.success(), "{}", stdout(&out));
    // With it, `rand` is a finding and `proptest` only a warning.
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
        text.contains("warning: dev-dependency `proptest`"),
        "{text}"
    );
    assert!(!text.contains("`proptest (dev-dependencies)` --"), "{text}");
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
