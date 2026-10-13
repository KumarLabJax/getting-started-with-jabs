#!/usr/bin/env bash
# Double-click launcher for macOS (Finder runs .command files in Terminal).
cd "$(dirname "$0")/.." || exit 1
exec bash student_scripts/start_jabs.sh "$@"
