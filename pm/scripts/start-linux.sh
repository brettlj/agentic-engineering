#!/usr/bin/env bash
# Platform-specific wrapper — delegates to shared script.
set -euo pipefail
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/start.sh"
