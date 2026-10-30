use photonhash_lf2_independent::{c20_block, verify_c20_vectors};
use std::{env, fs, process::ExitCode};

fn main() -> ExitCode {
    // New implementation's primitive test runs before any matrix derivation.
    let key = std::array::from_fn(|i| i as u8);
    let nonce = [0,0,0,9,0,0,0,0x4a,0,0,0,0];
    let expected = "10f1e7e4d13b5915500fdd1fa32071c4c7d1f4c733c068030422aa9ac3d46c4ed2826446079faa0914c2d705d98b02a2b5129cd1de164eb9cbd083e8a2503c4e";
    let actual: String = c20_block(&key,&nonce,1).iter().map(|b|format!("{b:02x}")).collect();
    if actual != expected {
        eprintln!("STOP: Rust RFC8439 primitive mismatch"); return ExitCode::from(40);
    }
    let Some(path) = env::args().nth(1) else { return ExitCode::from(2); };
    let text = match fs::read_to_string(&path) {
        Ok(text) => text, Err(error) => { eprintln!("{error}"); return ExitCode::from(2); }
    };
    match verify_c20_vectors(&text) {
        Ok(r) => {
            println!("{{\"type\":\"complete\",\"implementation\":\"Rust\",\"passed\":true,\"cases_measured\":{},\"derive_wall_s_measured_capped\":{},\"evaluate_wall_s_measured_capped\":{}}}",r.cases,r.derive_time.as_secs_f64(),r.evaluate_time.as_secs_f64());
            ExitCode::SUCCESS
        },
        Err(error) => { eprintln!("{error}"); ExitCode::from(40) }
    }
}
