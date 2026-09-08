//! The binary, end to end, on the files under examples/ -- including everything it has to
//! refuse. A file the CLI misreads is worse than one it rejects, because the Python side
//! cannot tell: it gets an answer either way.

use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

use serde_json::Value;

fn examples() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("examples")
}

fn example(name: &str) -> String {
    examples().join(name).to_string_lossy().into_owned()
}

/// Runs `induct` with the arguments and optional stdin; returns exit code, parsed stdout
/// (null when it is not JSON) and stderr.
fn induct(args: &[&str], stdin: Option<&str>) -> (i32, Value, String) {
    let mut child = Command::new(env!("CARGO_BIN_EXE_induct"))
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("induct starts");
    {
        let mut pipe = child.stdin.take().expect("stdin is piped");
        if let Some(text) = stdin {
            pipe.write_all(text.as_bytes())
                .expect("stdin accepts input");
        }
    }
    let output = child.wait_with_output().expect("induct finishes");
    let code = output.status.code().unwrap_or(-1);
    let stdout = String::from_utf8(output.stdout).expect("utf-8 stdout");
    let stderr = String::from_utf8(output.stderr).expect("utf-8 stderr");
    (
        code,
        serde_json::from_str(&stdout).unwrap_or(Value::Null),
        stderr,
    )
}

#[test]
fn induce_render_decide_and_diff_run_on_the_examples() {
    let blocks = example("blocks.json");
    let out = Path::new(env!("CARGO_TARGET_TMPDIR")).join("induced.json");
    let out = out.to_string_lossy().into_owned();

    let (demo1, demo2, demo3) = (
        example("demo-1.json"),
        example("demo-2.json"),
        example("demo-3.json"),
    );
    let (code, json, stderr) = induct(
        &[
            "induce", "--blocks", &blocks, "--out", &out, &demo1, &demo2, &demo3,
        ],
        None,
    );
    assert_eq!(code, 0, "{stderr}");
    assert_eq!(json["consistent"], Value::Bool(true));
    assert!(json["tree"].is_object());
    assert!(Path::new(&out).exists());

    let (code, json, stderr) = induct(&["render", &out, "--blocks", &blocks], None);
    assert_eq!(code, 0, "{stderr}");
    assert!(json["sentence"].as_str().unwrap().starts_with("If "));
    assert!(!json["lines"].as_array().unwrap().is_empty());

    let stop = std::fs::read_to_string(examples().join("stop.json")).unwrap();
    let tree = example("tree.json");
    let (code, json, stderr) = induct(&["decide", &tree, "--blocks", &blocks], Some(&stop));
    assert_eq!(code, 0, "{stderr}");
    assert!(json["action"].is_string());

    let (a, b) = (example("choices-a.json"), example("choices-b.json"));
    let (code, json, stderr) = induct(&["diff", "--blocks", &blocks, &a, &b], None);
    assert_eq!(code, 0, "{stderr}");
    assert!(json.get("first_difference").is_some());
}

#[test]
fn usage_and_io_errors_exit_two() {
    let (code, _, _) = induct(&[], None);
    assert_eq!(code, 2);
    let (code, json, stderr) = induct(
        &["render", "missing.json", "--blocks", "missing.json"],
        None,
    );
    assert_eq!(code, 2);
    assert_eq!(json, Value::Null);
    assert!(!stderr.is_empty());
}

/// Writes a file under the test target directory and returns its path.
fn scratch(name: &str, text: &str) -> String {
    let path = Path::new(env!("CARGO_TARGET_TMPDIR")).join(name);
    std::fs::write(&path, text).expect("the target directory is writable");
    path.to_string_lossy().into_owned()
}

/// Every refusal is the same shape: exit 2, one line on stderr, nothing on stdout.
fn refuses(what: &str, args: &[&str], stdin: Option<&str>) {
    let (code, json, stderr) = induct(args, stdin);
    assert_eq!(code, 2, "{what}: exited 0");
    assert_eq!(json, Value::Null, "{what}: wrote to stdout");
    assert_eq!(stderr.lines().count(), 1, "{what}: {stderr}");
}

#[test]
fn decide_refuses_what_induce_would_refuse() {
    let blocks = example("blocks.json");
    let tree = example("tree.json");
    let args = ["decide", &tree, "--blocks", &blocks];
    let cases = [
        // A struct will deserialise from a JSON array, positionally, so an empty list used to
        // read as a stop with nothing on it and decide something.
        ("an empty array", "[]"),
        ("an array of one object", r#"[{"predicates": {}}]"#),
        // Everything induce checks about a stop, decide checks too.
        (
            "a predicate that is not a block",
            r#"{"predicates": {"nonsense": true}, "raw": {}}"#,
        ),
        (
            "a reading for a predicate that is not a block",
            r#"{"predicates": {}, "raw": {"nonsense": 1.0}}"#,
        ),
        (
            "a field the contract does not have",
            r#"{"predicates": {}, "raw": {}, "tick": 5}"#,
        ),
        (
            "a repeated key",
            r#"{"predicates": {"carrying_cargo": true, "carrying_cargo": false}, "raw": {}}"#,
        ),
    ];
    for (what, stdin) in cases {
        refuses(what, &args, Some(stdin));
    }
}

#[test]
fn a_tree_that_is_two_things_at_once_is_refused_rather_than_half_read() {
    let blocks = example("blocks.json");
    // Read as an untagged enum this parses as the action, and the branch under it disappears.
    let both = scratch(
        "both-keys.json",
        r#"{"params": {}, "root": {"action": "take_branch", "predicate": "carrying_cargo",
             "yes": {"action": "take_branch"}, "no": {"action": "return_to_beacon"}}}"#,
    );
    refuses(
        "a node with both keys",
        &["render", &both, "--blocks", &blocks],
        None,
    );

    let half = scratch(
        "half-branch.json",
        r#"{"params": {}, "root": {"predicate": "carrying_cargo", "yes": {"action": "take_branch"}}}"#,
    );
    refuses(
        "a branch with one child",
        &["render", &half, "--blocks", &blocks],
        None,
    );

    let neither = scratch("empty-node.json", r#"{"params": {}, "root": {}}"#);
    refuses(
        "a node that is neither",
        &["render", &neither, "--blocks", &blocks],
        None,
    );

    let dup = scratch(
        "duplicate-param.json",
        r#"{"params": {"uncertainty_exceeds": {"theta": 1.0, "theta": 2.0}},
            "root": {"action": "take_branch"}}"#,
    );
    refuses(
        "a repeated parameter",
        &["render", &dup, "--blocks", &blocks],
        None,
    );
}

#[test]
fn a_trace_written_as_a_list_is_refused_at_every_depth() {
    let blocks = example("blocks.json");
    let out = Path::new(env!("CARGO_TARGET_TMPDIR"))
        .join("refused.json")
        .to_string_lossy()
        .into_owned();
    let step = r#"{"tick": 1, "junction": 0,
                   "predicates": {"unexplored_branch_exists": true},
                   "raw": {}, "action": "take_branch"}"#;
    let cases = [
        (
            "a trace as a positional array",
            format!(r#"[1, [], [], {{}}, [{step}], null]"#),
        ),
        (
            "a stop as a positional array",
            r#"{"seed": 1, "steps": [[1, 0, {"unexplored_branch_exists": true}, {},
                "take_branch"]]}"#
                .to_string(),
        ),
        (
            "an outcome as a positional array",
            format!(r#"{{"seed": 1, "steps": [{step}], "outcome": [true, 9, false]}}"#),
        ),
        (
            "a field the contract does not have",
            format!(r#"{{"seed": 1, "steps": [{step}], "bogus": 1}}"#),
        ),
        (
            "a repeated key inside a stop",
            r#"{"seed": 1, "steps": [{"tick": 1, "junction": 0,
                "predicates": {"unexplored_branch_exists": true, "unexplored_branch_exists": false},
                "raw": {}, "action": "take_branch"}]}"#
                .to_string(),
        ),
    ];
    for (what, text) in cases {
        let path = scratch("refused-trace.json", &text);
        refuses(
            what,
            &["induce", "--blocks", &blocks, "--out", &out, &path],
            None,
        );
    }
    assert!(
        !Path::new(&out).exists(),
        "a refused induction must not write a tree"
    );
}

#[test]
fn a_block_list_and_a_choice_list_are_read_as_strictly() {
    let out = Path::new(env!("CARGO_TARGET_TMPDIR"))
        .join("refused-blocks.json")
        .to_string_lossy()
        .into_owned();
    let demo = example("demo-1.json");
    let positional = scratch(
        "positional-blocks.json",
        r#"{"predicates": [["carrying_cargo", "carrying"]], "actions": []}"#,
    );
    refuses(
        "a block written as a positional array",
        &["induce", "--blocks", &positional, "--out", &out, &demo],
        None,
    );

    // A block list that is complete for the example tree, except that the provisional
    // value sits on a predicate with no parameter for it to be a value of.
    let stray = scratch(
        "provisional-without-param.json",
        r#"{"predicates": [{"id": "unexplored_branch_exists", "label": "an unexplored branch here"},
                           {"id": "uncertainty_exceeds", "label": "lost", "param": "theta"},
                           {"id": "carrying_cargo", "label": "carrying", "provisional": 1.0}],
            "actions": [{"id": "take_branch", "label": "take a branch"},
                        {"id": "return_to_beacon", "label": "go back"}]}"#,
    );
    refuses(
        "a provisional value on a predicate with no param",
        &["render", &example("tree.json"), "--blocks", &stray],
        None,
    );

    let blocks = example("blocks.json");
    let choices = scratch(
        "extra-choices.json",
        r#"{"choices": ["take_branch"], "extra": 1}"#,
    );
    let other = example("choices-b.json");
    refuses(
        "a field the contract does not have",
        &["diff", "--blocks", &blocks, &choices, &other],
        None,
    );
}

/// The two Python-side fields the contract does allow, since `deny_unknown_fields` would
/// otherwise reject the block lists the Python side actually writes.
#[test]
fn the_block_lists_stage_and_provisional_fields_are_still_accepted() {
    let blocks = std::fs::read_to_string(examples().join("blocks.json")).unwrap();
    assert!(blocks.contains("\"stage\""), "the example must exercise it");
    assert!(
        blocks.contains("\"provisional\""),
        "the example must exercise it"
    );
    let out = Path::new(env!("CARGO_TARGET_TMPDIR"))
        .join("staged.json")
        .to_string_lossy()
        .into_owned();
    let (code, json, stderr) = induct(
        &[
            "induce",
            "--blocks",
            &example("blocks.json"),
            "--out",
            &out,
            &example("demo-2.json"),
        ],
        None,
    );
    assert_eq!(code, 0, "{stderr}");
    assert_eq!(json["consistent"], Value::Bool(true));
}

/// A tree carries values only for the predicates it tests, so `render` and `decide` must
/// take one with no entry for a parametric predicate it never asks about -- and `decide`
/// on a stop that carries a reading for that predicate must not need a threshold for it.
#[test]
fn a_tree_with_no_value_for_a_predicate_it_does_not_test_renders_and_decides() {
    let blocks = example("blocks.json");
    let tree = scratch(
        "untested-param.json",
        r#"{"params": {}, "root": {"predicate": "carrying_cargo",
             "yes": {"action": "return_to_beacon"}, "no": {"action": "take_branch"}}}"#,
    );
    let (code, json, stderr) = induct(&["render", &tree, "--blocks", &blocks], None);
    assert_eq!(code, 0, "{stderr}");
    assert_eq!(
        json["sentence"],
        "If carrying, go back. Otherwise take a branch."
    );
    assert!(!json["lines"].to_string().contains("theta"));

    // The example stop carries a raw reading for the parametric predicate.
    let stop = std::fs::read_to_string(examples().join("stop.json")).unwrap();
    assert!(stop.contains("\"raw\": {\"uncertainty_exceeds\""));
    let (code, json, stderr) = induct(&["decide", &tree, "--blocks", &blocks], Some(&stop));
    assert_eq!(code, 0, "{stderr}");
    assert_eq!(json["action"], "take_branch");
}
