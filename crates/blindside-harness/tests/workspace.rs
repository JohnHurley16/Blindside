//! Workspace invariants that Cargo will not enforce by itself (BLD-19, BLD-34), read out
//! of `cargo metadata`, the crate roots and -- for the last test -- `docs/HARNESS.md`.
//! These are the "load-bearing" constraints of ARCHITECTURE.md's crate layout: the sim's
//! dependency tree must stay auditable by reading one list, and that list must not move
//! under a `cargo update`. The document check is here for the same reason: a promise that
//! a grep indexes a section of prose is only true until someone forgets, and forgetting is
//! silent.

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};
use std::process::Command;

use serde_json::Value;

/// The crates docs/DETERMINISM.md constrains, plus blindside-content, which is in the
/// sim's dependency tree and held to the same rules by this repo's standing orders.
const CONSTRAINED: [&str; 4] = [
    "blindside-sim",
    "blindside-vm",
    "blindside-content",
    "blindside-gen",
];

/// The only workspace crates blindside-sim may depend on (ARCHITECTURE.md: "blindside-sim
/// depends only on blindside-vm and blindside-content").
const SIM_WORKSPACE_DEPS: [&str; 2] = ["blindside-vm", "blindside-content"];

/// Crates that must not appear anywhere in a constrained crate's resolved dependency
/// graph, dev-dependencies included (DETERMINISM.md rule 4; BLD-22; BLD-25).
const BANNED_PACKAGES: [&str; 3] = ["rand", "rayon", "libm"];

/// Every direct dependency blindside-harness is allowed to have, of any kind. The harness
/// is a headless tool: PHASE-0-HARNESS.md says it "runs a match to completion with no
/// renderer", and BLD-31 asks that `cargo tree -p blindside-harness` show no GUI, renderer
/// or audio dependency. Keeping the direct list closed is the cheap half of that; a new
/// dependency has to be added here deliberately.
const HARNESS_DIRECT_DEPS: [&str; 6] = [
    "blindside-sim",
    "blindside-content",
    "blake3",
    "clap",
    "serde",
    "serde_json",
    // dev-dependencies: trybuild (BLD-32) is added below, since dev deps are listed too.
];

/// The other half: names that would mean a window, a renderer or a sound card had arrived
/// anywhere in the harness's resolved graph. Substring-matched, because these ship as
/// families (`wgpu-core`, `winit-*`, `gdk-sys`).
const GUI_RENDERER_AUDIO: [&str; 16] = [
    "winit", "wgpu", "sdl2", "glutin", "glium", "egui", "iced", "gtk", "gdk", "cpal", "rodio",
    "godot", "bevy", "vulkano", "skia", "raylib",
];

fn workspace_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("..").join("..")
}

fn metadata() -> Value {
    let out = Command::new(env!("CARGO"))
        .args(["metadata", "--format-version", "1", "--locked"])
        .current_dir(workspace_root())
        .output()
        .expect("run cargo metadata");
    assert!(
        out.status.success(),
        "cargo metadata failed:\n{}",
        String::from_utf8_lossy(&out.stderr)
    );
    serde_json::from_slice(&out.stdout).expect("cargo metadata is JSON")
}

fn packages(meta: &Value) -> BTreeMap<String, &Value> {
    meta["packages"]
        .as_array()
        .unwrap()
        .iter()
        .map(|p| (p["name"].as_str().unwrap().to_string(), p))
        .collect()
}

fn workspace_member_names(meta: &Value) -> BTreeSet<String> {
    let by_id: BTreeMap<&str, &str> = meta["packages"]
        .as_array()
        .unwrap()
        .iter()
        .map(|p| (p["id"].as_str().unwrap(), p["name"].as_str().unwrap()))
        .collect();
    meta["workspace_members"]
        .as_array()
        .unwrap()
        .iter()
        .map(|id| by_id[id.as_str().unwrap()].to_string())
        .collect()
}

#[test]
fn blindside_sim_depends_on_no_workspace_crate_but_vm_and_content() {
    let meta = metadata();
    let members = workspace_member_names(&meta);
    let sim = packages(&meta)["blindside-sim"];
    for dep in sim["dependencies"].as_array().unwrap() {
        let name = dep["name"].as_str().unwrap();
        if members.contains(name) {
            assert!(
                SIM_WORKSPACE_DEPS.contains(&name),
                "blindside-sim depends on workspace crate `{name}` ({} dependency); \
                 ARCHITECTURE.md allows only {SIM_WORKSPACE_DEPS:?}",
                dep["kind"].as_str().unwrap_or("normal")
            );
        }
    }
}

#[test]
fn constrained_crates_pin_every_external_dependency_exactly() {
    let meta = metadata();
    let members = workspace_member_names(&meta);
    let pkgs = packages(&meta);
    for crate_name in CONSTRAINED {
        for dep in pkgs[crate_name]["dependencies"].as_array().unwrap() {
            let name = dep["name"].as_str().unwrap();
            if members.contains(name) {
                continue; // a path dependency inside the workspace
            }
            let req = dep["req"].as_str().unwrap();
            assert!(
                req.starts_with('='),
                "{crate_name}: dependency `{name}` is `{req}`; every external dependency of a \
                 constrained crate is pinned `=x.y.z` in [workspace.dependencies] (BLD-19)"
            );
        }
    }
}

/// Walk the resolved graph from each constrained crate and check no banned package is
/// reachable -- through any kind of dependency, dev-dependencies included.
#[test]
fn no_rand_family_crate_is_reachable_from_a_constrained_crate() {
    let meta = metadata();
    let nodes: BTreeMap<&str, &Value> = meta["resolve"]["nodes"]
        .as_array()
        .unwrap()
        .iter()
        .map(|n| (n["id"].as_str().unwrap(), n))
        .collect();
    let name_of: BTreeMap<&str, &str> = meta["packages"]
        .as_array()
        .unwrap()
        .iter()
        .map(|p| (p["id"].as_str().unwrap(), p["name"].as_str().unwrap()))
        .collect();
    let id_of: BTreeMap<&str, &str> = name_of.iter().map(|(id, n)| (*n, *id)).collect();
    for crate_name in CONSTRAINED {
        let mut seen = BTreeSet::new();
        let mut stack = vec![id_of[crate_name]];
        while let Some(id) = stack.pop() {
            if !seen.insert(id) {
                continue;
            }
            for dep in nodes[id]["dependencies"].as_array().unwrap() {
                stack.push(dep.as_str().unwrap());
            }
        }
        for id in seen {
            let name = name_of[id];
            assert!(
                !BANNED_PACKAGES.contains(&name) && !name.starts_with("rand_"),
                "`{name}` is reachable from {crate_name}"
            );
        }
    }
}

/// BLD-29: the two tooling gates exist and neither is a default feature. That is only the
/// declaration half; `feature_gates_are_absent_from_the_resolved_sets` below is the half
/// that matters, because Cargo unifies features per build.
#[test]
fn blindside_sim_default_features_are_empty_and_declare_the_gates() {
    let meta = metadata();
    let features = &packages(&meta)["blindside-sim"]["features"];
    assert_eq!(features["default"], serde_json::json!([]));
    assert!(features.get("diagnostics").is_some());
    assert!(features.get("inject-desync").is_some());
}

/// BLD-34: the constrained crate roots deny `unsafe_code`, so any `unsafe` is an explicit
/// `#[allow]` with a `// SAFETY:` line, which the determinism lint checks.
#[test]
fn constrained_crate_roots_deny_unsafe_code() {
    for crate_name in CONSTRAINED {
        let lib = workspace_root()
            .join("crates")
            .join(crate_name)
            .join("src")
            .join("lib.rs");
        let text = std::fs::read_to_string(&lib).unwrap();
        assert!(
            text.contains("#![deny(unsafe_code)]"),
            "{}: missing #![deny(unsafe_code)]",
            lib.display()
        );
    }
}

/// BLD-31: the headless runner stays headless. Both halves of "`cargo tree -p
/// blindside-harness` shows no GUI, renderer or audio dependency": the direct list is
/// closed, and nothing in the resolved graph is named like a window, a renderer or a sound
/// card. (The other half of that bullet -- that the crate never reaches `World` -- is
/// proved at compile time in `tests/world_unreachable.rs`, which is stronger than a grep:
/// `World` appears in this crate only in prose and in one message string.)
#[test]
fn the_harness_has_no_gui_renderer_or_audio_dependency() {
    let meta = metadata();
    let pkgs = packages(&meta);
    let mut allowed: BTreeSet<&str> = HARNESS_DIRECT_DEPS.iter().copied().collect();
    allowed.insert("trybuild");
    for dep in pkgs["blindside-harness"]["dependencies"]
        .as_array()
        .unwrap()
    {
        let name = dep["name"].as_str().unwrap();
        assert!(
            allowed.contains(name),
            "blindside-harness gained the direct dependency `{name}`; add it to \
             HARNESS_DIRECT_DEPS on purpose, and only if a headless tool needs it"
        );
    }

    let nodes: BTreeMap<&str, &Value> = meta["resolve"]["nodes"]
        .as_array()
        .unwrap()
        .iter()
        .map(|n| (n["id"].as_str().unwrap(), n))
        .collect();
    let name_of: BTreeMap<&str, &str> = meta["packages"]
        .as_array()
        .unwrap()
        .iter()
        .map(|p| (p["id"].as_str().unwrap(), p["name"].as_str().unwrap()))
        .collect();
    let harness_id = name_of
        .iter()
        .find(|(_, n)| **n == "blindside-harness")
        .map(|(id, _)| *id)
        .unwrap();
    let mut seen = BTreeSet::new();
    let mut stack = vec![harness_id];
    while let Some(id) = stack.pop() {
        if !seen.insert(id) {
            continue;
        }
        for dep in nodes[id]["dependencies"].as_array().unwrap() {
            stack.push(dep.as_str().unwrap());
        }
    }
    for id in seen {
        let name = name_of[id];
        for banned in GUI_RENDERER_AUDIO {
            assert!(
                !name.contains(banned),
                "`{name}` is reachable from blindside-harness; the headless runner has \
                 no renderer (PHASE-0-HARNESS.md)"
            );
        }
    }
}

/// BLD-29, the half that matters: Cargo unifies features per package across one build
/// invocation, so a gate being `default = []` proves nothing on its own. For every crate
/// named in `ci/no-tooling-features.txt`, the feature set Cargo actually resolves for it
/// must mention neither `diagnostics` nor `inject-desync`.
///
/// `cargo tree -e features -p <crate>` is the resolver's own answer, dev-dependency edges
/// included, which is why it is asked rather than reasoning from the manifests. CI runs
/// the same check (`.github/workflows/determinism.yml`, job `feature-gates`); it is here
/// too so the dev machine fails before the push does.
#[test]
fn feature_gates_are_absent_from_the_resolved_sets() {
    let list = workspace_root().join("ci").join("no-tooling-features.txt");
    let text = std::fs::read_to_string(&list).unwrap_or_else(|e| panic!("{}: {e}", list.display()));
    let crates: Vec<&str> = text
        .lines()
        .map(|l| l.split('#').next().unwrap().trim())
        .filter(|l| !l.is_empty())
        .collect();
    assert!(
        crates.contains(&"blindside-sim"),
        "{} must name blindside-sim",
        list.display()
    );
    for crate_name in crates {
        let out = Command::new(env!("CARGO"))
            .args(["tree", "-e", "features", "--locked", "-p", crate_name])
            .current_dir(workspace_root())
            .output()
            .unwrap_or_else(|e| panic!("cargo tree -p {crate_name}: {e}"));
        assert!(
            out.status.success(),
            "cargo tree -p {crate_name} failed:\n{}",
            String::from_utf8_lossy(&out.stderr)
        );
        let tree = String::from_utf8_lossy(&out.stdout);
        for gate in ["diagnostics", "inject-desync"] {
            let needle = format!("feature \"{gate}\"");
            assert!(
                !tree.contains(&needle),
                "`{gate}` is in the resolved feature set of {crate_name}; a tooling gate \
                 has escaped into a crate that must ship without it (BLD-29). Build \
                 hash-producing and shippable targets with `-p <crate>`, never \
                 `--workspace`."
            );
        }
    }
}

/// The marker every value guessed without a designer answer carries, and the string
/// `docs/HARNESS.md` §1 tells the reader to grep for.
const DEFAULT_MARKER: &str = "DEFAULT (awaiting designer)";

/// Workspace files a `DEFAULT (awaiting designer)` marker may live in: Rust sources and
/// manifests under `crates/` and `tools/`, plus the root `Cargo.toml` (the profile
/// decision lives there). Documents are deliberately not scanned -- `ARCHITECTURE.md`
/// carries a marker of its own, but that is prose *about* a decision, not the place the
/// decision is made, and §1 does not cite it as one. This file is skipped as well: it
/// spells the marker out in order to look for it.
fn files_carrying_a_default_marker(root: &Path) -> BTreeSet<String> {
    fn walk(dir: &Path, root: &Path, skip: &str, out: &mut BTreeSet<String>) {
        let entries = std::fs::read_dir(dir).unwrap_or_else(|e| panic!("{}: {e}", dir.display()));
        for entry in entries {
            let path = entry.expect("read a directory entry").path();
            let name = path
                .file_name()
                .unwrap_or_default()
                .to_string_lossy()
                .to_string();
            if path.is_dir() {
                // `target/` is build output, not authored source.
                if name != "target" {
                    walk(&path, root, skip, out);
                }
            } else if name.ends_with(".rs") || name.ends_with(".toml") {
                let rel = relative_slash_path(&path, root);
                if rel == skip {
                    continue;
                }
                let text = std::fs::read_to_string(&path).unwrap_or_default();
                if text.contains(DEFAULT_MARKER) {
                    out.insert(rel);
                }
            }
        }
    }

    let skip = file!().replace('\\', "/");
    let mut out = BTreeSet::new();
    let root_manifest = root.join("Cargo.toml");
    if std::fs::read_to_string(&root_manifest)
        .unwrap_or_default()
        .contains(DEFAULT_MARKER)
    {
        out.insert("Cargo.toml".to_string());
    }
    for dir in ["crates", "tools"] {
        walk(&root.join(dir), root, &skip, &mut out);
    }
    out
}

/// `crates\foo\src\bar.rs` -> `crates/foo/src/bar.rs`, so the comparison with a document
/// written in forward slashes holds on Windows too.
fn relative_slash_path(path: &Path, root: &Path) -> String {
    path.strip_prefix(root)
        .unwrap_or(path)
        .components()
        .map(|c| c.as_os_str().to_string_lossy().to_string())
        .collect::<Vec<_>>()
        .join("/")
}

/// The files `docs/HARNESS.md` §1 names on its `*Marked in:*` lines. Only the first
/// backticked span on each line is a marker site; the rest of the line is free to cite
/// a test or another document.
fn files_named_by_the_question_round(harness_md: &str) -> BTreeSet<String> {
    let section = harness_md
        .split_once("\n## 1.")
        .expect("HARNESS.md has a section 1")
        .1
        .split_once("\n## 2.")
        .expect("HARNESS.md has a section 2")
        .0;
    section
        .lines()
        .filter_map(|line| line.trim().strip_prefix("*Marked in:*"))
        .map(|rest| {
            let after = rest.split_once('`').expect("a backticked path").1;
            after
                .split_once('`')
                .expect("a closing backtick")
                .0
                .to_string()
        })
        .collect()
}

/// BLD-20 and BLD-39: `docs/HARNESS.md` §1 tells the reader that
/// `grep -rn "DEFAULT (awaiting designer)"` "is the live index of this section". That is a
/// claim about a document and a source tree staying in step, so it rots without a sound,
/// and it already had: the tick rate was defaulted in `runner.rs` under a plain doc
/// comment, so §1 named a file the grep did not return and `PHASE-0-READINESS.md` then
/// listed the tick rate among the questions with *no default at all* -- a silent pick, the
/// exact thing CLAUDE.md's "ask rather than invent" rule and the marker convention exist to
/// prevent.
///
/// Both directions matter. A marked file missing from §1 is a default the designer is
/// never asked about; a file in §1 with no marker is a question whose answer nobody can
/// find in the code. So this asserts set equality, by file.
#[test]
fn harness_default_markers_match_the_question_round() {
    let root = workspace_root();
    let harness_md = root.join("docs").join("HARNESS.md");
    let text = std::fs::read_to_string(&harness_md)
        .unwrap_or_else(|e| panic!("{}: {e}", harness_md.display()));

    let marked = files_carrying_a_default_marker(&root);
    let named = files_named_by_the_question_round(&text);

    let unasked: Vec<&String> = marked.difference(&named).collect();
    let unmarked: Vec<&String> = named.difference(&marked).collect();

    assert!(
        unasked.is_empty(),
        "these files carry a `{DEFAULT_MARKER}` marker but no `*Marked in:*` line in \
         docs/HARNESS.md §1 names them, so the default is not in the question round the \
         designer will answer: {unasked:?}"
    );
    assert!(
        unmarked.is_empty(),
        "docs/HARNESS.md §1 says these files carry a `{DEFAULT_MARKER}` marker and they do \
         not, so §1's claim that the grep is its live index is false: {unmarked:?}"
    );
    assert!(
        marked.len() >= 10,
        "only {} file(s) carry the marker; §1 has fifteen questions and thirteen defaults, \
         so this is almost certainly a broken scan rather than a tidy-up",
        marked.len()
    );
}
