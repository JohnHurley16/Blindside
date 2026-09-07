//! A choice list: `{"choices": [action ids]}`, one entry per stop.

use std::fs;
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::blocks::BlockSet;
use crate::error::{Error, Result};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Choices {
    pub choices: Vec<String>,
}

impl Choices {
    pub fn load(path: &Path) -> Result<Self> {
        let text = fs::read_to_string(path).map_err(|e| Error::io(path, e))?;
        serde_json::from_str(&text).map_err(|e| Error::json(&path.display().to_string(), e))
    }

    /// Every choice must be an action in the block list. `name` is for the message only.
    pub fn validate(&self, blocks: &BlockSet, name: &str) -> Result<()> {
        for (index, id) in self.choices.iter().enumerate() {
            if blocks.action(id).is_none() {
                return Err(Error::input(format!(
                    "{name}: choice {index} is {id:?}, which is not in the block list"
                )));
            }
        }
        Ok(())
    }
}
