#!/usr/bin/env sh
set -eu

# Migrations/imports are one-shot release jobs, never API startup work.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
