//! blindside-content — data-driven definitions: sensors, modules, chassis, ancients.
//!
//! Phase 0: the content pack is empty, but the pack hash every replay carries
//! (DETERMINISM.md: "Replays carry a content pack hash"; ARCHITECTURE.md rule 2) is real
//! from day one. The function, its canonical byte order and the mismatch error exist now
//! so that the first content file changes a hash, not a file format, and so that a replay
//! recorded against one pack is refused by another instead of silently replaying wrong.
//!
//! This crate is inside blindside-sim's dependency tree, so docs/DETERMINISM.md rules 1-8
//! apply to every line of it. The one thing it does that the sim may not is read files:
//! `ContentPack::read_dir` is the loader, and the sim only ever sees the loaded pack.
//!
//! # What the hash covers -- and the open Phase 3 question
//!
//! `content_hash` is BLAKE3 over the *bytes of the data files*, not over parsed structs:
//! `CONTENT_SCHEMA`, then every file under the pack root in sorted relative-path order,
//! each with its path included (see [`ContentPack::hash`] for the exact layout). Bytes are
//! hashed as they are on disk; the repository's `.gitattributes` pins `content/**` to LF so
//! a Windows checkout hashes the same as Linux and macOS.
//!
//! DEFAULT (awaiting designer): the hash covers the WHOLE PACK's file bytes -- the reading
//! that cannot be wrong by omission, since anything that can change a match is in it. The
//! alternative, which BLD-63 decides before the content format is frozen, is to hash only
//! the season-enabled set of entries serialised canonically and sorted by stable ID, so
//! that shipping next season's content does not invalidate this season's replays
//! (ARCHITECTURE.md extension rule 5). Switching changes every fixture's `content_hash`,
//! which is why it is question 7 of `docs/HARNESS.md` section 1 rather than settled here.

#![deny(unsafe_code)]

use std::fmt;
use std::path::{Path, PathBuf};

/// Schema version of the content pack format. Bumped on any incompatible change; it is
/// the first thing the pack hash covers, so a bump changes every pack's hash.
pub const CONTENT_SCHEMA: u16 = 0;

/// Hash of the empty pack under `CONTENT_SCHEMA` 0: no entries at all. Golden value;
/// `empty_pack_hash_is_the_documented_constant` asserts it on every platform.
///
/// The empty pack is what Phase 0 ships. It is represented as *zero entries*, and a pack
/// root that does not exist on disk loads as the empty pack (`ContentPack::read_dir`), so
/// the repository needs no placeholder file under `content/` -- a placeholder would be an
/// entry, and would have to be hashed like one.
pub const EMPTY_PACK_HASH: [u8; 32] = [
    0x3d, 0xbd, 0x5a, 0x09, 0xe7, 0xa3, 0xcb, 0x05, 0x76, 0x55, 0x22, 0xff, 0x5d, 0x61, 0x87, 0x22,
    0xf3, 0xab, 0x77, 0x84, 0x97, 0x3a, 0x3e, 0x7c, 0x3b, 0x8a, 0x43, 0xc0, 0x95, 0x40, 0x4b, 0xa1,
];

/// One file of a content pack.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PackEntry {
    /// Path relative to the pack root, `/`-separated whatever the OS, no `.` or `..`
    /// segments. This is what is hashed, so it must not depend on where the pack sits.
    pub path: String,
    /// The file's bytes exactly as on disk.
    pub bytes: Vec<u8>,
}

/// A loaded content pack: its entries, sorted by path bytes. Construct through
/// [`ContentPack::from_entries`] or [`ContentPack::read_dir`]; both sort and validate, so
/// the hash never depends on the order files were found in.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ContentPack {
    entries: Vec<PackEntry>,
}

/// Why a pack could not be built.
#[derive(Debug)]
pub enum PackError {
    /// Two entries with the same relative path (a hash over them would be ambiguous).
    DuplicatePath(String),
    /// A path that is absolute, uses `\`, or contains an empty, `.` or `..` segment.
    InvalidPath(String),
    /// A file or directory name under the pack root that is not UTF-8.
    NonUtf8Path(PathBuf),
    /// The loader could not read the pack root or a file under it.
    Io {
        path: PathBuf,
        error: std::io::Error,
    },
}

impl fmt::Display for PackError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            PackError::DuplicatePath(p) => write!(f, "duplicate content path `{p}`"),
            PackError::InvalidPath(p) => write!(
                f,
                "invalid content path `{p}` (must be relative, `/`-separated, no `.`/`..`)"
            ),
            PackError::NonUtf8Path(p) => {
                write!(f, "content path is not UTF-8: {}", p.display())
            }
            PackError::Io { path, error } => write!(f, "cannot read {}: {error}", path.display()),
        }
    }
}

impl std::error::Error for PackError {}

impl ContentPack {
    /// The empty pack: zero entries. Its hash is [`EMPTY_PACK_HASH`].
    pub fn empty() -> ContentPack {
        ContentPack {
            entries: Vec::new(),
        }
    }

    /// Build a pack from entries in any order. Sorted by path bytes here; duplicate or
    /// malformed paths are errors, not silently dropped.
    pub fn from_entries(mut entries: Vec<PackEntry>) -> Result<ContentPack, PackError> {
        for e in &entries {
            if !is_valid_relative_path(&e.path) {
                return Err(PackError::InvalidPath(e.path.clone()));
            }
        }
        entries.sort_by(|a, b| a.path.as_bytes().cmp(b.path.as_bytes()));
        for w in entries.windows(2) {
            if w[0].path == w[1].path {
                return Err(PackError::DuplicatePath(w[0].path.clone()));
            }
        }
        Ok(ContentPack { entries })
    }

    /// Load every regular file under `root`, recursively, as the pack. A `root` that does
    /// not exist is the empty pack. Directory read order is whatever the OS returns and is
    /// irrelevant: entries are sorted by path.
    ///
    /// Names beginning with `.` (`.gitkeep`, `.DS_Store`, editor swap files) are skipped at
    /// every level. A stray Finder file must not change the pack hash on one developer's
    /// machine; content is never named with a leading dot.
    pub fn read_dir(root: &Path) -> Result<ContentPack, PackError> {
        let mut entries = Vec::new();
        if root.is_dir() {
            walk(root, root, &mut entries)?;
        }
        ContentPack::from_entries(entries)
    }

    /// Entries in hashed (sorted-path) order.
    pub fn entries(&self) -> &[PackEntry] {
        &self.entries
    }

    /// The content pack hash. BLAKE3 over, in order:
    ///
    /// ```text
    /// u16 LE   CONTENT_SCHEMA
    /// u32 LE   entry count
    /// per entry, in ascending byte order of path:
    ///   u32 LE  path length in bytes,  path bytes (UTF-8, `/`-separated, relative)
    ///   u64 LE  data length in bytes,  data bytes
    /// ```
    ///
    /// Every field is length-prefixed, so no arrangement of paths and bytes can collide
    /// with another by shifting a boundary, and the path is hashed with the bytes, so
    /// moving a file changes the hash exactly as editing it does.
    pub fn hash(&self) -> [u8; 32] {
        let mut h = blake3::Hasher::new();
        h.update(&CONTENT_SCHEMA.to_le_bytes());
        h.update(&(self.entries.len() as u32).to_le_bytes());
        for e in &self.entries {
            h.update(&(e.path.len() as u32).to_le_bytes());
            h.update(e.path.as_bytes());
            h.update(&(e.bytes.len() as u64).to_le_bytes());
            h.update(&e.bytes);
        }
        *h.finalize().as_bytes()
    }
}

/// The content pack hash that goes into every replay (`MatchRecord::content_hash`). Same as
/// [`ContentPack::hash`]; exposed as a function so the call site reads as what it is.
pub fn content_hash(pack: &ContentPack) -> [u8; 32] {
    pack.hash()
}

/// Relative, `/`-separated, every segment non-empty and neither `.` nor `..`, no `\`.
fn is_valid_relative_path(p: &str) -> bool {
    !p.is_empty()
        && !p.starts_with('/')
        && !p.contains('\\')
        && p.split('/')
            .all(|seg| !seg.is_empty() && seg != "." && seg != "..")
}

fn walk(root: &Path, dir: &Path, out: &mut Vec<PackEntry>) -> Result<(), PackError> {
    let entries = std::fs::read_dir(dir).map_err(|error| PackError::Io {
        path: dir.to_path_buf(),
        error,
    })?;
    for entry in entries {
        let entry = entry.map_err(|error| PackError::Io {
            path: dir.to_path_buf(),
            error,
        })?;
        let path = entry.path();
        let name = entry.file_name();
        let name = name
            .to_str()
            .ok_or_else(|| PackError::NonUtf8Path(path.clone()))?;
        if name.starts_with('.') {
            continue;
        }
        if path.is_dir() {
            walk(root, &path, out)?;
        } else if path.is_file() {
            let rel = path
                .strip_prefix(root)
                .expect("walked path is under root")
                .components()
                .map(|c| {
                    c.as_os_str()
                        .to_str()
                        .map(str::to_string)
                        .ok_or_else(|| PackError::NonUtf8Path(path.clone()))
                })
                .collect::<Result<Vec<String>, PackError>>()?
                .join("/");
            let bytes = std::fs::read(&path).map_err(|error| PackError::Io {
                path: path.clone(),
                error,
            })?;
            out.push(PackEntry { path: rel, bytes });
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU32, Ordering};

    fn entry(path: &str, bytes: &[u8]) -> PackEntry {
        PackEntry {
            path: path.to_string(),
            bytes: bytes.to_vec(),
        }
    }

    /// A fresh temp directory per test, removed on drop. Named by process id and a counter
    /// (no wall clock: rule 3 applies to this crate's tests as much as its code).
    struct Scratch(PathBuf);

    impl Scratch {
        fn new(name: &str) -> Scratch {
            static N: AtomicU32 = AtomicU32::new(0);
            let dir = std::env::temp_dir().join(format!(
                "blindside-content-test-{}-{}-{name}",
                std::process::id(),
                N.fetch_add(1, Ordering::Relaxed)
            ));
            let _ = std::fs::remove_dir_all(&dir);
            Scratch(dir)
        }
        fn write(&self, rel: &str, bytes: &[u8]) {
            let p = self.0.join(rel);
            std::fs::create_dir_all(p.parent().unwrap()).unwrap();
            std::fs::write(p, bytes).unwrap();
        }
    }

    impl Drop for Scratch {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }

    #[test]
    fn empty_pack_hash_is_the_documented_constant() {
        assert_eq!(ContentPack::empty().hash(), EMPTY_PACK_HASH);
        assert_eq!(content_hash(&ContentPack::empty()), EMPTY_PACK_HASH);
        assert_eq!(
            ContentPack::from_entries(Vec::new()).unwrap().hash(),
            EMPTY_PACK_HASH
        );
    }

    #[test]
    fn a_missing_root_is_the_empty_pack_and_one_byte_changes_it() {
        // BLD-26: add a one-byte file to a (copy of the) pack; the hash must change.
        let s = Scratch::new("one-byte");
        assert!(!s.0.exists());
        let before = ContentPack::read_dir(&s.0).unwrap();
        assert_eq!(before.entries().len(), 0);
        assert_eq!(before.hash(), EMPTY_PACK_HASH);

        s.write("x", b"a");
        let after = ContentPack::read_dir(&s.0).unwrap();
        assert_eq!(after.entries().len(), 1);
        assert_eq!(after.entries()[0].path, "x");
        assert_ne!(after.hash(), EMPTY_PACK_HASH);

        // An existing but empty root is the empty pack too.
        let e = Scratch::new("empty-dir");
        std::fs::create_dir_all(&e.0).unwrap();
        assert_eq!(ContentPack::read_dir(&e.0).unwrap().hash(), EMPTY_PACK_HASH);
    }

    #[test]
    fn hash_is_independent_of_entry_order() {
        let a = ContentPack::from_entries(vec![
            entry("b/two.toml", b"2"),
            entry("a/one.toml", b"1"),
            entry("c.toml", b"3"),
        ])
        .unwrap();
        let b = ContentPack::from_entries(vec![
            entry("c.toml", b"3"),
            entry("a/one.toml", b"1"),
            entry("b/two.toml", b"2"),
        ])
        .unwrap();
        assert_eq!(a, b);
        assert_eq!(a.hash(), b.hash());
        let paths: Vec<&str> = a.entries().iter().map(|e| e.path.as_str()).collect();
        assert_eq!(paths, ["a/one.toml", "b/two.toml", "c.toml"]);
    }

    #[test]
    fn path_and_bytes_and_boundaries_all_matter() {
        let h = |v: Vec<PackEntry>| ContentPack::from_entries(v).unwrap().hash();
        let base = h(vec![entry("a", b"xy")]);
        assert_ne!(base, h(vec![entry("b", b"xy")]), "same bytes, other path");
        assert_ne!(base, h(vec![entry("a", b"xz")]), "same path, other bytes");
        assert_ne!(
            h(vec![entry("ab", b"c")]),
            h(vec![entry("a", b"bc")]),
            "length prefixes keep path/data boundaries distinct"
        );
        assert_ne!(
            h(vec![entry("a", b""), entry("b", b"")]),
            h(vec![entry("a", b"")]),
            "entry count is covered"
        );
    }

    #[test]
    fn read_dir_walks_nested_dirs_with_slash_paths_and_skips_dotfiles() {
        let s = Scratch::new("nested");
        s.write("sensors/sonar.toml", b"[sonar]\n");
        s.write("chassis.toml", b"[chassis]\n");
        s.write(".gitkeep", b"");
        s.write("sensors/.hidden", b"nope");
        let pack = ContentPack::read_dir(&s.0).unwrap();
        let paths: Vec<&str> = pack.entries().iter().map(|e| e.path.as_str()).collect();
        assert_eq!(paths, ["chassis.toml", "sensors/sonar.toml"]);
        assert_eq!(
            pack.hash(),
            ContentPack::from_entries(vec![
                entry("chassis.toml", b"[chassis]\n"),
                entry("sensors/sonar.toml", b"[sonar]\n"),
            ])
            .unwrap()
            .hash(),
            "a pack read from disk hashes like the same entries built in memory"
        );
    }

    #[test]
    fn malformed_and_duplicate_paths_are_errors() {
        for bad in ["", "/abs", "a\\b", "a//b", "./a", "a/../b", "a/."] {
            assert!(
                matches!(
                    ContentPack::from_entries(vec![entry(bad, b"")]),
                    Err(PackError::InvalidPath(_))
                ),
                "{bad:?} should be rejected"
            );
        }
        assert!(matches!(
            ContentPack::from_entries(vec![entry("a", b"1"), entry("a", b"2")]),
            Err(PackError::DuplicatePath(_))
        ));
    }
}
