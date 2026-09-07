//! The one error type. Every variant is a usage or input problem and maps to exit code 2
//! at the command line; the algorithm itself cannot fail.

use std::fmt;
use std::path::Path;

/// Anything that stops a command before it can answer.
#[derive(Debug)]
pub enum Error {
    /// A file (or stdin) could not be read, or a file could not be written.
    Io {
        path: String,
        source: std::io::Error,
    },
    /// A file or stdin held JSON that does not match the contract.
    Json {
        path: String,
        source: serde_json::Error,
    },
    /// The input parsed but says something the contract forbids.
    Input(String),
}

impl Error {
    pub fn io(path: &Path, source: std::io::Error) -> Self {
        Error::Io {
            path: path.display().to_string(),
            source,
        }
    }

    pub fn json(path: &str, source: serde_json::Error) -> Self {
        Error::Json {
            path: path.to_string(),
            source,
        }
    }

    pub fn input(message: impl Into<String>) -> Self {
        Error::Input(message.into())
    }
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::Io { path, source } => write!(f, "{path}: {source}"),
            Error::Json { path, source } => write!(f, "{path}: {source}"),
            Error::Input(message) => write!(f, "{message}"),
        }
    }
}

impl std::error::Error for Error {}

pub type Result<T> = std::result::Result<T, Error>;
