#!/usr/bin/env bash
# AI Daily 入口：委托给 scripts/collect.py
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 scripts/collect.py
