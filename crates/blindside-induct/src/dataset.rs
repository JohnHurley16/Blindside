//! Every stop of every trace as a boolean vector over the block predicates, under one
//! parameter assignment. Conflicts and the tree search read this, never the traces.

use std::collections::BTreeMap;

use crate::blocks::BlockSet;
use crate::evaluate::predicate_value;
use crate::named_trace::NamedTrace;
use crate::params::Params;
use crate::search::Sample;
use crate::step_input::StepInput;
use crate::step_ref::StepRef;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DatasetStep {
    /// Position of the trace in the input list.
    pub trace_pos: usize,
    /// Index of the stop in that trace's `steps`.
    pub index: usize,
    /// One entry per block predicate, in block order. Absent predicates are false.
    pub vector: Vec<bool>,
    /// Index into the block list's actions.
    pub action: usize,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Dataset {
    /// In trace order, then stop order.
    pub steps: Vec<DatasetStep>,
}

impl Dataset {
    /// The traces must already be validated against `blocks`.
    pub fn build(blocks: &BlockSet, traces: &[NamedTrace], params: &Params) -> Dataset {
        let mut steps = Vec::new();
        for (trace_pos, named) in traces.iter().enumerate() {
            for (index, step) in named.trace.steps.iter().enumerate() {
                let input = StepInput::from(step);
                let vector = blocks
                    .predicates
                    .iter()
                    .map(|p| predicate_value(p, &input, params).unwrap_or(false))
                    .collect();
                let action = blocks.action_index(&step.action).expect(
                    "traces are validated against the block list before a dataset is built",
                );
                steps.push(DatasetStep {
                    trace_pos,
                    index,
                    vector,
                    action,
                });
            }
        }
        Dataset { steps }
    }

    pub fn step_ref(&self, position: usize, traces: &[NamedTrace]) -> StepRef {
        let step = &self.steps[position];
        StepRef {
            trace: traces[step.trace_pos].name.clone(),
            index: step.index,
        }
    }

    /// The distinct vectors with their action, in vector order. Only meaningful when the
    /// dataset has no conflicts; otherwise the first action seen wins.
    pub fn samples(&self) -> Vec<Sample> {
        let mut seen: BTreeMap<&[bool], usize> = BTreeMap::new();
        for step in &self.steps {
            seen.entry(step.vector.as_slice()).or_insert(step.action);
        }
        seen.into_iter()
            .map(|(vector, action)| Sample {
                vector: vector.to_vec(),
                action,
            })
            .collect()
    }
}
