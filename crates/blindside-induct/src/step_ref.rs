//! A reference to one stop of one trace, as the command line reports it: the trace's name
//! as given, and the stop's index in that trace's `steps`.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct StepRef {
    pub trace: String,
    pub index: usize,
}
