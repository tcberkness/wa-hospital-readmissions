#!/usr/bin/env bash
# Full refresh: pull from the CMS API, validate + load SQLite, run statistics.
set -euo pipefail
cd "$(dirname "$0")"
python3 src/fetch_cms.py
python3 src/build_db.py
python3 src/analysis.py
