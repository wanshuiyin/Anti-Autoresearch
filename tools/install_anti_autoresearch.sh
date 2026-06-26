#!/usr/bin/env bash
# Install the Anti-Autoresearch skills + workflow into a Claude Code skills dir.
#
# Usage:
#   ./tools/install_anti_autoresearch.sh                 # global → ~/.claude/skills
#   ./tools/install_anti_autoresearch.sh ./.claude/skills  # project-local
#
# The Python tools under tools/ are the deterministic spine the skills call via
# $(git rev-parse --show-toplevel); they are NOT copied into the skills dir.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-$HOME/.claude/skills}"

mkdir -p "$TARGET"
cp -R "$ROOT"/skills/*       "$TARGET"/
cp -R "$ROOT"/workflows/*    "$TARGET"/

n_skills=$(find "$ROOT/skills" -maxdepth 1 -mindepth 1 -type d | wc -l | tr -d ' ')
echo "✅ Installed Anti-Autoresearch → $TARGET"
echo "   $n_skills skills + the anti-autoresearch workflow"
echo
echo "   next:"
echo "     claude mcp add codex -- codex mcp-server     # wire the cross-model reviewer"
echo "     # then, in Claude Code:"
echo "     /anti-autoresearch <paper-dir>"
echo
echo "   (the deterministic core also runs standalone, zero-dep: python3 eval/run_eval.py)"
