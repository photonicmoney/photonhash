//! Independently structured LF2-K8 implementation.
//!
//! This crate deliberately uses RustCrypto SHAKE256 and iterator/chunk based
//! matrix evaluation rather than translating the portable C control flow.
//! It is non-consensus admission evidence.

use sha3::Shake256;
use sha3::digest::{ExtendableOutput, Update, XofReader};
use std::collections::HashMap;
use std::time::{Duration, Instant};

pub const N: usize = 4096;
pub const PASSES: usize = 8;
pub const DIGEST_LEN: usize = 32;

const MATRIX_TAG: &[u8] = b"LASER/PhotonHash/v1/matrix";
const VECTOR_TAG: &[u8] = b"LASER/PhotonHash/v1/vector";
const BANK_TAG: &[u8] = b"LASER/PhotonHash/launch-LF2/matrix";
const FINAL_TAG: &[u8] = b"LASER/PhotonHash/launch-LF2/final";
const BANK_TEST_TAG: &[u8] = b"PhotonHash/v0.4.0-shadow.1/test-bank";
const C20_VECTOR_TAG: &[u8] = b"LASER/PhotonHash/LF3-K8-C20-experiment.1/vector";
const C20_FINAL_TAG: &[u8] = b"LASER/PhotonHash/LF3-K8-C20-experiment.1/final";

// Direct RFC 8439 section 2.3 implementation; no C/CUDA code or FFI.
fn c20_quarter(s: &mut [u32; 16], a: usize, b: usize, c: usize, d: usize) {
    s[a] = s[a].wrapping_add(s[b]); s[d] = (s[d] ^ s[a]).rotate_left(16);
    s[c] = s[c].wrapping_add(s[d]); s[b] = (s[b] ^ s[c]).rotate_left(12);
    s[a] = s[a].wrapping_add(s[b]); s[d] = (s[d] ^ s[a]).rotate_left(8);
    s[c] = s[c].wrapping_add(s[d]); s[b] = (s[b] ^ s[c]).rotate_left(7);
}

pub fn c20_block(key: &[u8; 32], nonce: &[u8; 12], counter: u32) -> [u8; 64] {
    let mut initial = [0u32; 16];
    initial[..4].copy_from_slice(&[0x61707865, 0x3320646e, 0x79622d32, 0x6b206574]);
    for (word, bytes) in initial[4..12].iter_mut().zip(key.chunks_exact(4)) {
        *word = u32::from_le_bytes(bytes.try_into().unwrap());
    }
    initial[12] = counter;
    for (word, bytes) in initial[13..].iter_mut().zip(nonce.chunks_exact(4)) {
        *word = u32::from_le_bytes(bytes.try_into().unwrap());
    }
    let mut state = initial;
    for _ in 0..10 {
        for [a,b,c,d] in [[0,4,8,12],[1,5,9,13],[2,6,10,14],[3,7,11,15],
                          [0,5,10,15],[1,6,11,12],[2,7,8,13],[3,4,9,14]] {
            c20_quarter(&mut state,a,b,c,d);
        }
    }
    let mut result = [0u8; 64];
    for ((destination, word), original) in result.chunks_exact_mut(4).zip(state).zip(initial) {
        destination.copy_from_slice(&word.wrapping_add(original).to_le_bytes());
    }
    result
}

fn shake(parts: &[&[u8]], length: usize) -> Vec<u8> {
    let mut state = Shake256::default();
    for part in parts {
        state.update(part);
    }
    let mut reader = state.finalize_xof();
    let mut output = vec![0u8; length];
    reader.read(&mut output);
    output
}

fn array32(bytes: Vec<u8>) -> [u8; DIGEST_LEN] {
    bytes.try_into().expect("internal SHAKE length")
}

fn signed_nibbles(packed: &[u8]) -> Vec<i8> {
    packed
        .iter()
        .flat_map(|byte| [((byte & 15) as i8) - 8, ((byte >> 4) as i8) - 8])
        .collect()
}

#[derive(Clone, Debug)]
pub struct Matrix {
    entries: Vec<i8>,
    pub seed: [u8; 64],
    pub checksum: [u8; DIGEST_LEN],
}

impl Matrix {
    fn derive(parent: &[u8; DIGEST_LEN]) -> Self {
        let seed: [u8; 64] = shake(&[MATRIX_TAG, parent], 64)
            .try_into()
            .expect("matrix seed length");
        let packed = shake(&[&seed], N * N / 2);
        let checksum = array32(shake(&[&packed], DIGEST_LEN));
        let entries = signed_nibbles(&packed);
        Self {
            entries,
            seed,
            checksum,
        }
    }

    fn rows(&self) -> impl Iterator<Item = &[i8]> {
        self.entries.chunks_exact(N)
    }
}

#[derive(Debug)]
pub struct MatrixBank {
    pub matrices: Vec<Matrix>,
}

impl MatrixBank {
    pub fn evaluate_c20(&self, header: &[u8], nonce: u64) -> Attempt {
        assert_eq!(self.matrices.len(), PASSES);
        let h = array32(shake(&[C20_VECTOR_TAG, header, &nonce.to_le_bytes()], DIGEST_LEN));
        let packed: Vec<u8> = (1..=32).flat_map(|counter| c20_block(&h, &[0u8;12], counter)).collect();
        let x = signed_nibbles(&packed);
        let mut folded = vec![0u8; N/2];
        for matrix in &self.matrices {
            for (r, row) in matrix.rows().enumerate() {
                let sum: i32 = row.iter().zip(&x)
                    .map(|(&a,&b)| i32::from(a)*i32::from(b)).sum();
                let q = (((sum + 262144) as u32 >> 9) & 15) as u8;
                folded[r/2] ^= q << (4*(r%2));
            }
        }
        let digest = array32(shake(&[C20_FINAL_TAG, &h, &folded], DIGEST_LEN));
        Attempt { h, folded, digest }
    }

    pub fn derive(parent: &[u8; DIGEST_LEN]) -> Self {
        let matrices = (0..PASSES)
            .map(|pass| {
                if pass == 0 {
                    Matrix::derive(parent)
                } else {
                    let index = (pass as u32).to_le_bytes();
                    let derived_parent = array32(shake(&[BANK_TAG, parent, &index], DIGEST_LEN));
                    Matrix::derive(&derived_parent)
                }
            })
            .collect();
        Self { matrices }
    }

    pub fn evaluate(&self, header: &[u8], nonce: u64) -> Attempt {
        assert_eq!(self.matrices.len(), PASSES);
        let nonce_bytes = nonce.to_le_bytes();
        let h = array32(shake(&[VECTOR_TAG, header, &nonce_bytes], DIGEST_LEN));
        let packed_x = shake(&[&h], N / 2);
        let x = signed_nibbles(&packed_x);
        let mut folded = vec![0u8; N / 2];

        for matrix in &self.matrices {
            for (row_index, row) in matrix.rows().enumerate() {
                let dot = row
                    .iter()
                    .zip(&x)
                    .map(|(&coefficient, &value)| i32::from(coefficient) * i32::from(value))
                    .sum::<i32>();
                let bucket = (((dot + 64 * N as i32) as u32 >> 9) & 15) as u8;
                let destination = &mut folded[row_index / 2];
                *destination ^= if row_index & 1 == 0 {
                    bucket
                } else {
                    bucket << 4
                };
            }
        }

        let digest = array32(shake(&[FINAL_TAG, &h, &folded], DIGEST_LEN));
        Attempt { h, folded, digest }
    }
}

#[derive(Debug, PartialEq, Eq)]
pub struct Attempt {
    pub h: [u8; DIGEST_LEN],
    pub folded: Vec<u8>,
    pub digest: [u8; DIGEST_LEN],
}

#[derive(Debug)]
pub struct VerificationReport {
    pub derive_time: Duration,
    pub evaluate_time: Duration,
    pub cases: usize,
}

fn decode_hex(text: &str) -> Result<Vec<u8>, String> {
    if text.len() % 2 != 0 {
        return Err("odd-length hex string".into());
    }
    (0..text.len())
        .step_by(2)
        .map(|offset| {
            u8::from_str_radix(&text[offset..offset + 2], 16).map_err(|error| error.to_string())
        })
        .collect()
}

fn parse_fields(text: &str) -> HashMap<String, String> {
    text.lines()
        .filter_map(|line| line.split_once('='))
        .map(|(key, value)| (key.to_owned(), value.to_owned()))
        .collect()
}

fn field_bytes(fields: &HashMap<String, String>, key: &str) -> Result<Vec<u8>, String> {
    let value = fields.get(key).ok_or_else(|| format!("missing {key}"))?;
    decode_hex(value)
}

pub fn verify_vectors(text: &str) -> Result<VerificationReport, String> {
    let fields = parse_fields(text);
    if fields.get("n").map(String::as_str) != Some("4096")
        || fields.get("passes").map(String::as_str) != Some("8")
    {
        return Err("vector profile does not match frozen LF2-K8".into());
    }
    let parent: [u8; DIGEST_LEN] = field_bytes(&fields, "parent")?
        .try_into()
        .map_err(|_| "parent length".to_owned())?;
    let header = field_bytes(&fields, "header80")?;

    let started = Instant::now();
    let bank = MatrixBank::derive(&parent);
    let derive_time = started.elapsed();
    for (pass, matrix) in bank.matrices.iter().enumerate() {
        let seed = field_bytes(&fields, &format!("matrix[{pass}].seed"))?;
        let checksum = field_bytes(&fields, &format!("matrix[{pass}].checksum"))?;
        if seed != matrix.seed || checksum != matrix.checksum {
            return Err(format!("matrix metadata mismatch at pass {pass}"));
        }
    }

    let evaluation_started = Instant::now();
    let mut cases = 0usize;
    loop {
        let header_key = format!("case[{cases}].header");
        let Some(header_kind) = fields.get(&header_key) else {
            break;
        };
        let nonce = fields
            .get(&format!("case[{cases}].nonce"))
            .ok_or_else(|| format!("missing nonce for case {cases}"))?
            .parse::<u64>()
            .map_err(|error| error.to_string())?;
        let case_header: &[u8] = match header_kind.as_str() {
            "empty" => &[],
            "header80" => &header,
            other => return Err(format!("unknown header kind {other}")),
        };
        let attempt = bank.evaluate(case_header, nonce);
        let expected_h = field_bytes(&fields, &format!("case[{cases}].h_in"))?;
        let expected_folded = field_bytes(&fields, &format!("case[{cases}].folded"))?;
        let expected_digest = field_bytes(&fields, &format!("case[{cases}].digest"))?;
        if expected_h != attempt.h {
            return Err(format!("h mismatch in case {cases}"));
        }
        if expected_folded != attempt.folded {
            return Err(format!("fold mismatch in case {cases}"));
        }
        if expected_digest != attempt.digest {
            return Err(format!("digest mismatch in case {cases}"));
        }
        cases += 1;
    }
    if cases == 0 {
        return Err("no cases found".into());
    }
    Ok(VerificationReport {
        derive_time,
        evaluate_time: evaluation_started.elapsed(),
        cases,
    })
}

pub fn verify_c20_vectors(text: &str) -> Result<VerificationReport, String> {
    let fields = parse_fields(text);
    if fields.get("profile").map(String::as_str) != Some("LF3-K8-C20-experiment.1")
        || fields.get("n").map(String::as_str) != Some("4096")
        || fields.get("passes").map(String::as_str) != Some("8") {
        return Err("C20 experiment profile mismatch".into());
    }
    let count = fields.get("cases").ok_or("missing case count")?
        .parse::<usize>().map_err(|e| e.to_string())?;
    if count < 64 { return Err("fewer than the required 64 vectors".into()); }
    let mut previous_parent = None;
    let mut bank = None;
    let mut derive_time = Duration::ZERO;
    let mut evaluate_time = Duration::ZERO;
    for case in 0..count {
        let prefix = format!("case[{case}]");
        let parent: [u8;32] = field_bytes(&fields,&format!("{prefix}.parent"))?
            .try_into().map_err(|_| "parent length")?;
        if previous_parent != Some(parent) {
            // Release the previous bank before deriving its replacement.
            drop(bank.take());
            let started = Instant::now();
            bank = Some(MatrixBank::derive(&parent));
            derive_time += started.elapsed();
            previous_parent = Some(parent);
        }
        let header = field_bytes(&fields,&format!("{prefix}.header"))?;
        let nonce = fields.get(&format!("{prefix}.nonce")).ok_or("missing nonce")?
            .parse::<u64>().map_err(|e| e.to_string())?;
        let started = Instant::now();
        let actual = bank.as_ref().unwrap().evaluate_c20(&header,nonce);
        evaluate_time += started.elapsed();
        for (field,bytes) in [("h",actual.h.as_slice()),("fold",actual.folded.as_slice()),("digest",actual.digest.as_slice())] {
            if field_bytes(&fields,&format!("{prefix}.{field}"))? != bytes {
                return Err(format!("STOP: implementation mismatch: {field}, case {case}"));
            }
        }
        if case%32 == 31 { println!("C20 full-fold progress: {} measured cases",case+1); }
    }
    Ok(VerificationReport { derive_time, evaluate_time, cases:count })
}

fn shadow_parent(index: usize) -> [u8; DIGEST_LEN] {
    match index {
        0 => [0u8; DIGEST_LEN],
        1 => [0xffu8; DIGEST_LEN],
        2 => std::array::from_fn(|i| i as u8),
        3 => array32(shake(&[b"v0.4-shadow-parent-3"], DIGEST_LEN)),
        _ => unreachable!("four shadow cases"),
    }
}

fn shadow_header(index: usize) -> (&'static str, Vec<u8>) {
    match index {
        0 => ("empty", vec![]),
        1 => ("zero", vec![0]),
        2 => ("incrementing", (0..80).map(|i| i as u8).collect()),
        3 => (
            "affine131+17",
            (0..4096).map(|i| (i * 131 + 17) as u8).collect(),
        ),
        _ => unreachable!("four shadow cases"),
    }
}

fn bank_commitment(parent: &[u8; DIGEST_LEN], bank: &MatrixBank) -> [u8; DIGEST_LEN] {
    let mut parts: Vec<&[u8]> = vec![BANK_TEST_TAG, parent];
    for matrix in &bank.matrices {
        parts.push(&matrix.seed);
        parts.push(&matrix.checksum);
    }
    array32(shake(&parts, DIGEST_LEN))
}

pub fn verify_shadow_vectors(text: &str) -> Result<usize, String> {
    let fields = parse_fields(text);
    if fields.get("profile").map(String::as_str) != Some("LF2-K8")
        || fields.get("n").map(String::as_str) != Some("4096")
        || fields.get("passes").map(String::as_str) != Some("8")
        || fields.get("cases").map(String::as_str) != Some("4")
    {
        return Err("shadow vector profile metadata mismatch".into());
    }
    let nonces = [0, u64::MAX, 0x0123_4567_89ab_cdef, 1];
    for index in 0..4 {
        let parent = shadow_parent(index);
        let (kind, header) = shadow_header(index);
        if field_bytes(&fields, &format!("case[{index}].parent"))? != parent
            || fields
                .get(&format!("case[{index}].header"))
                .map(String::as_str)
                != Some(kind)
            || fields
                .get(&format!("case[{index}].header_len"))
                .map(String::as_str)
                != Some(header.len().to_string().as_str())
        {
            return Err(format!("shadow input mismatch in case {index}"));
        }
        let nonce = fields
            .get(&format!("case[{index}].nonce"))
            .ok_or_else(|| format!("missing nonce in case {index}"))?
            .parse::<u64>()
            .map_err(|error| error.to_string())?;
        if nonce != nonces[index] {
            return Err(format!("nonce mismatch in case {index}"));
        }
        let bank = MatrixBank::derive(&parent);
        let attempt = bank.evaluate(&header, nonce);
        let fold_digest = array32(shake(&[&attempt.folded], DIGEST_LEN));
        if field_bytes(&fields, &format!("case[{index}].bank_commitment"))?
            != bank_commitment(&parent, &bank)
            || field_bytes(&fields, &format!("case[{index}].h_in"))? != attempt.h
            || field_bytes(&fields, &format!("case[{index}].fold_digest"))? != fold_digest
            || field_bytes(&fields, &format!("case[{index}].digest"))? != attempt.digest
        {
            return Err(format!("shadow output mismatch in case {index}"));
        }
    }
    Ok(4)
}

#[cfg(test)]
mod tests {
    use super::*;

    const VECTORS: &str = include_str!("../../../docs/launch-profile-lf2-vectors.txt");

    #[test]
    fn independently_reproduces_frozen_vectors() {
        let report = verify_vectors(VECTORS).expect("frozen vectors");
        assert_eq!(report.cases, 4);
    }

    #[test]
    fn independently_reproduces_shadow_vectors() {
        const SHADOW: &str = include_str!("../../../docs/v0.4-shadow-vectors.txt");
        assert_eq!(verify_shadow_vectors(SHADOW).expect("shadow vectors"), 4);
    }

    #[test]
    fn little_endian_target_order_is_strict() {
        let zero = [0u8; DIGEST_LEN];
        let mut one = zero;
        one[0] = 1;
        assert!(u256_le_less(&zero, &one));
        assert!(!u256_le_less(&one, &one));
    }
}

pub fn u256_le_less(left: &[u8; DIGEST_LEN], right: &[u8; DIGEST_LEN]) -> bool {
    left.iter()
        .rev()
        .zip(right.iter().rev())
        .find_map(|(&a, &b)| (a != b).then_some(a < b))
        .unwrap_or(false)
}
