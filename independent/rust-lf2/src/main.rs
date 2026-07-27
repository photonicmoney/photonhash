use photonhash_lf2_independent::verify_vectors;
use std::env;
use std::fs;
use std::process::ExitCode;

fn main() -> ExitCode {
    let path = env::args()
        .nth(1)
        .unwrap_or_else(|| "docs/launch-profile-lf2-vectors.txt".to_owned());
    let vectors = match fs::read_to_string(&path) {
        Ok(value) => value,
        Err(error) => {
            eprintln!("unable to read {path}: {error}");
            return ExitCode::FAILURE;
        }
    };
    match verify_vectors(&vectors) {
        Ok(report) => {
            println!("independent LF2-K8 vectors: PASS");
            println!(
                "matrix derivation: {:.3} s",
                report.derive_time.as_secs_f64()
            );
            println!(
                "{} cases: {:.3} s total, {:.3} ms/case",
                report.cases,
                report.evaluate_time.as_secs_f64(),
                report.evaluate_time.as_secs_f64() * 1000.0 / report.cases as f64
            );
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("independent LF2-K8 vectors: FAIL: {error}");
            ExitCode::FAILURE
        }
    }
}
