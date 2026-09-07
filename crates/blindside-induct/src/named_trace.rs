//! A trace together with the name the command line gave it. Step references carry that
//! name back out, verbatim.

use crate::trace::Trace;

#[derive(Debug, Clone, PartialEq)]
pub struct NamedTrace {
    pub name: String,
    pub trace: Trace,
}
