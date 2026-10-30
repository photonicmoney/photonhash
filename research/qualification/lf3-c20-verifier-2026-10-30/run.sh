#!/bin/bash
# Opt-in reproduction on a separate research machine; no Laser integration.
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
repo=$(cd -- "$here/../../.." && pwd)
if [[ ${LF3_RESEARCH_ACK:-} != 1 || $# != 1 ]];then
 echo 'Usage: LF3_RESEARCH_ACK=1 bash run.sh /absolute/results/directory'
 exit 2
fi
case "$1" in /*) ;; *) echo 'Results directory must be absolute';exit 2;; esac
if [[ -e "$1" ]];then echo 'Refusing existing results directory';exit 2;fi
mkdir -p "$1/build" "$1/evidence" "$1/build/sanitized"
export LF3_REPRO_ROOT="$1" OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1
cd -- "$1"
flags=(-O3 -std=c11 -Wall -Wextra -Werror -fopenmp -I"$repo/include" -I"$here/reference/include" -I"$here/src")
for path in "$repo/src/photonhash.c" "$repo/src/photonhash_launch.c" "$here"/reference/src/*.c "$here/src/bank_openssl.c";do
 gcc "${flags[@]}" -c "$path" -o "build/$(basename "${path%.c}").o"
done
gcc "${flags[@]}" "$here/src/bank_conformance.c" build/*.o -lcrypto -o build/conformance
timeout --signal=TERM --kill-after=5 180 build/conformance "$repo/research/qualification/lf3-c20-2026-10-30/c20-experiment-vectors.txt" > evidence/bank-conformance.jsonl 2>&1
gcc "${flags[@]}" "$here/src/cpu_bench.c" build/*.o -lcrypto -o build/cpu_bench
timeout --signal=TERM --kill-after=5 180 build/cpu_bench > evidence/cpu-bench.jsonl 2>&1
gcc "${flags[@]}" "$here/src/admission_lab.c" "$here/src/admission_test.c" build/*.o -lcrypto -o build/admission_test
timeout --signal=TERM --kill-after=5 90 build/admission_test > evidence/admission-test.jsonl 2>&1
python3 "$here/src/test_telemetry_guard.py" > evidence/telemetry-fault-tests.log 2>&1
python3 "$here/src/analyze_cpu.py" > evidence/statistics-controller.log
san=(-O1 -g -std=c11 -Wall -Wextra -fopenmp -fsanitize=address,undefined -fno-omit-frame-pointer -I"$repo/include" -I"$here/reference/include" -I"$here/src")
for path in "$repo/src/photonhash.c" "$repo/src/photonhash_launch.c" "$here"/reference/src/*.c "$here/src/bank_openssl.c";do
 gcc "${san[@]}" -c "$path" -o "build/sanitized/$(basename "${path%.c}").o"
done
gcc "${san[@]}" "$here/src/admission_lab.c" "$here/src/admission_test.c" build/sanitized/*.o -lcrypto -o build/admission_sanitized
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 timeout --signal=TERM --kill-after=5 120 build/admission_sanitized > evidence/admission-sanitized.jsonl 2>&1
echo 'REPRODUCTION_COMPLETE; this does not qualify consensus or physical energy.'
