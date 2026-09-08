//! Reading JSON the way a contract should be read.
//!
//! `serde` is generous by default in ways that matter here, because the files this crate
//! reads are written by another process and a file that is quietly misread is worse than one
//! that is rejected. Three generosities are closed:
//!
//! - a struct will deserialise from a JSON *array*, positionally, so `[]` parses as a step
//!   with no readings at all and a trace can be written as a bare list. Every document this
//!   crate reads is an object, and so is everything the contract nests inside one, so
//!   [`from_str`] insists on that at the top and [`objects`] and [`object`] insist on it at
//!   the places the contract nests a struct;
//! - a repeated key in a JSON object is accepted, last one winning, so two `"predicates"`
//!   maps in one stop silently discard the first. [`from_str`] walks the whole document and
//!   refuses any object that repeats a key;
//! - a field that is not in the contract is ignored, so a typo in a field name reads as the
//!   field's default. Every type here carries `deny_unknown_fields`.
//!
//! What this cannot reach is a type's own laxity: see `tree::Node`, which is hand-written for
//! the same reasons.

use std::collections::BTreeSet;
use std::fmt;

use serde::de::{self, DeserializeOwned, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Deserializer};

use crate::error::{Error, Result};

/// Parses one document: an object, with no key repeated anywhere inside it. `name` names the
/// source in any message.
pub fn from_str<T: DeserializeOwned>(text: &str, name: &str) -> Result<T> {
    serde_json::from_str::<Document>(text).map_err(|e| Error::json(name, e))?;
    serde_json::from_str::<T>(text).map_err(|e| Error::json(name, e))
}

/// A `deserialize_with` for a field holding a list of structs: every element must be a JSON
/// object, never a positional array.
pub fn objects<'de, D, T>(deserializer: D) -> std::result::Result<Vec<T>, D::Error>
where
    D: Deserializer<'de>,
    T: DeserializeOwned,
{
    let values = Vec::<serde_json::Value>::deserialize(deserializer)?;
    values.into_iter().map(from_object).collect()
}

/// The same for a field holding one optional struct.
pub fn object<'de, D, T>(deserializer: D) -> std::result::Result<Option<T>, D::Error>
where
    D: Deserializer<'de>,
    T: DeserializeOwned,
{
    match Option::<serde_json::Value>::deserialize(deserializer)? {
        Some(value) => from_object(value).map(Some),
        None => Ok(None),
    }
}

fn from_object<T: DeserializeOwned, E: de::Error>(
    value: serde_json::Value,
) -> std::result::Result<T, E> {
    if !value.is_object() {
        return Err(E::invalid_type(
            de::Unexpected::Other("a JSON array"),
            &"a JSON object",
        ));
    }
    T::deserialize(value).map_err(E::custom)
}

/// The whole document: an object whose every nested object repeats no key.
struct Document;

impl<'de> Deserialize<'de> for Document {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> std::result::Result<Self, D::Error> {
        deserializer.deserialize_map(Walk)?;
        Ok(Document)
    }
}

/// Any JSON value at all, walked only to check its objects.
struct Anything;

impl<'de> Deserialize<'de> for Anything {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> std::result::Result<Self, D::Error> {
        deserializer.deserialize_any(Walk)
    }
}

struct Walk;

impl<'de> Visitor<'de> for Walk {
    type Value = Anything;

    fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("a JSON object")
    }

    fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> std::result::Result<Anything, A::Error> {
        let mut seen: BTreeSet<String> = BTreeSet::new();
        while let Some(key) = map.next_key::<String>()? {
            map.next_value::<Anything>()?;
            if !seen.insert(key.clone()) {
                return Err(de::Error::custom(format!("duplicate key {key:?}")));
            }
        }
        Ok(Anything)
    }

    fn visit_seq<A: SeqAccess<'de>>(self, mut seq: A) -> std::result::Result<Anything, A::Error> {
        while seq.next_element::<Anything>()?.is_some() {}
        Ok(Anything)
    }

    fn visit_bool<E: de::Error>(self, _: bool) -> std::result::Result<Anything, E> {
        Ok(Anything)
    }

    fn visit_i64<E: de::Error>(self, _: i64) -> std::result::Result<Anything, E> {
        Ok(Anything)
    }

    fn visit_u64<E: de::Error>(self, _: u64) -> std::result::Result<Anything, E> {
        Ok(Anything)
    }

    fn visit_f64<E: de::Error>(self, _: f64) -> std::result::Result<Anything, E> {
        Ok(Anything)
    }

    fn visit_str<E: de::Error>(self, _: &str) -> std::result::Result<Anything, E> {
        Ok(Anything)
    }

    fn visit_unit<E: de::Error>(self) -> std::result::Result<Anything, E> {
        Ok(Anything)
    }

    fn visit_none<E: de::Error>(self) -> std::result::Result<Anything, E> {
        Ok(Anything)
    }

    fn visit_some<D: Deserializer<'de>>(
        self,
        deserializer: D,
    ) -> std::result::Result<Anything, D::Error> {
        deserializer.deserialize_any(Walk)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeMap;

    #[derive(Debug, Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Thing {
        #[serde(default)]
        values: BTreeMap<String, u32>,
    }

    fn parse(text: &str) -> Result<Thing> {
        from_str(text, "thing")
    }

    #[test]
    fn an_object_parses() {
        let thing = parse(r#"{"values": {"a": 1}}"#).expect("an object parses");
        assert_eq!(thing.values["a"], 1);
    }

    #[test]
    fn a_positional_array_does_not() {
        assert!(parse("[]").is_err());
        assert!(parse(r#"[{"a": 1}]"#).is_err());
    }

    #[test]
    fn a_repeated_key_does_not_at_any_depth() {
        assert!(parse(r#"{"values": {"a": 1}, "values": {}}"#).is_err());
        assert!(parse(r#"{"values": {"a": 1, "a": 2}}"#).is_err());
    }

    #[test]
    fn a_field_the_contract_does_not_have_does_not() {
        assert!(parse(r#"{"values": {}, "bogus": 1}"#).is_err());
    }
}
