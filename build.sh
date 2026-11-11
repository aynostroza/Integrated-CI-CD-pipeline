#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo 'BUILD: checking Python syntax'
python3 -m compileall -q ci_lab/app ci_lab/webex_notify.py

# Stage only application source; omit caches, tests, credentials and repository files.
stage_dir=$(mktemp -d)
trap 'rm -rf "$stage_dir"' EXIT
cp ci_lab/app/calculator.py ci_lab/app/main.py "$stage_dir/"
mkdir -p ci_lab/dist
python3 -m zipapp "$stage_dir" -m 'main:main' -o ci_lab/dist/calculator.pyz

echo 'BUILD: smoke-testing packaged application: 2 + 3 = 5'
result=$(python3 ci_lab/dist/calculator.pyz add 2 3)
test "$result" = '5'
echo 'BUILD PASSED: ci_lab/dist/calculator.pyz'
