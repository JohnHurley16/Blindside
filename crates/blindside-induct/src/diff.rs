//! The first place two choice lists disagree. Choice lists are the actions a policy (or a
//! player) took at successive stops on the same seed; the ghost replay marks the first
//! difference.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Diff {
    pub first_difference: Option<usize>,
    pub a: Option<String>,
    pub b: Option<String>,
}

/// `first_difference` is the index of the first position where the lists differ, or where
/// one ends and the other does not; `a` and `b` are the choices at that index (`None` for
/// the list that has ended). All three are `None` when the lists are identical.
pub fn diff(a: &[String], b: &[String]) -> Diff {
    let shared = a.iter().zip(b).take_while(|(x, y)| x == y).count();
    if shared == a.len() && shared == b.len() {
        return Diff {
            first_difference: None,
            a: None,
            b: None,
        };
    }
    Diff {
        first_difference: Some(shared),
        a: a.get(shared).cloned(),
        b: b.get(shared).cloned(),
    }
}
