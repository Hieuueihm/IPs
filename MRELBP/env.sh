#!/bin/bash

# === Project Root Path ===
export PROJECT_ROOT=$(realpath "$(dirname "$BASH_SOURCE")")
echo $PROJECT_ROOT

echo "[✓] Environment set up. PROJECT_ROOT=$PROJECT_ROOT"
