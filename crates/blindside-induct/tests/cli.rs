//! The binary, end to end, on the files under examples/.

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
