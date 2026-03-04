#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .

echo "Installed ResearchClaw in editable mode."
echo "Run: source .venv/bin/activate && researchclaw --help"
