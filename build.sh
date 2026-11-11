#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo 'BUILD: checking Python syntax'
python3 -m compileall -q app sample_code.py webex_notify.py

# Stage only application source; omit caches, tests, credentials and repository files.
stage_dir=$(mktemp -d)
trap 'rm -rf "$stage_dir"' EXIT
cp app/calculator.py app/main.py "$stage_dir/"
mkdir -p dist
python3 -m zipapp "$stage_dir" -m 'main:main' -o dist/calculator.pyz

echo 'BUILD: smoke-testing packaged application: 2 + 3 = 5'
result=$(python3 dist/calculator.pyz add 2 3)
test "$result" = '5'
echo 'BUILD PASSED: dist/calculator.pyz'
