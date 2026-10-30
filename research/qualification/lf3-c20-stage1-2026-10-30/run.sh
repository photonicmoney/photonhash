#!/usr/bin/env bash
set -euo pipefail
if [[ "${LF3_RESEARCH_ACK:-}" != 1 ]]; then
  echo 'Set LF3_RESEARCH_ACK=1 only on an authorized isolated Linux research machine.' >&2
  exit 2
fi
if [[ $# != 1 ]]; then echo 'Usage: run.sh /absolute/new/results-directory' >&2; exit 2; fi
package_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec timeout --signal=TERM --kill-after=5 900 python3 "$package_dir/reproduce.py" "$1"
