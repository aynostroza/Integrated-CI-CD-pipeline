#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo 'TEST: running Python unit tests (including mocked Webex API tests)'
python3 -m unittest discover -s tests -t . -v
echo 'ALL PYTHON UNIT TESTS PASSED'
