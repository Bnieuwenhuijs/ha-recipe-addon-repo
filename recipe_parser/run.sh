#!/usr/bin/with-contenv bashio
set -e
echo "[recipe-parser] Starting..."
exec python3 /app/recipe_parser.py
