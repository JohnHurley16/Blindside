//! Pinned cases for the choice-list diff.

use blindside_induct::diff::{diff, Diff};

fn list(items: &[&str]) -> Vec<String> {
    items.iter().map(|s| s.to_string()).collect()
}

fn same() -> Diff {
    Diff {
        first_difference: None,
        a: None,
        b: None,
    }
}

fn at(index: usize, a: Option<&str>, b: Option<&str>) -> Diff {
    Diff {
        first_difference: Some(index),
        a: a.map(str::to_string),
        b: b.map(str::to_string),
    }
}

#[test]
fn identical_lists_have_no_difference() {
    assert_eq!(diff(&list(&["x", "y"]), &list(&["x", "y"])), same());
    assert_eq!(diff(&list(&[]), &list(&[])), same());
}

#[test]
fn the_first_differing_index_and_both_choices_are_reported() {
    assert_eq!(
        diff(&list(&["x", "x", "y"]), &list(&["x", "z", "y"])),
        at(1, Some("x"), Some("z"))
    );
    assert_eq!(
        diff(&list(&["x"]), &list(&["y"])),
        at(0, Some("x"), Some("y"))
    );
}

#[test]
fn a_list_that_ends_early_differs_at_its_length() {
    assert_eq!(
        diff(&list(&["x", "y"]), &list(&["x"])),
        at(1, Some("y"), None)
    );
    assert_eq!(
        diff(&list(&["x"]), &list(&["x", "y"])),
        at(1, None, Some("y"))
    );
    assert_eq!(diff(&list(&[]), &list(&["x"])), at(0, None, Some("x")));
}
