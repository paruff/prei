#!/usr/bin/env bash
# scripts/graphify-update.sh
#
# Manual script to update the graphify knowledge graph after code changes.
# Runs AST-only rebuild (fast, no LLM needed) — same as the post-commit hook.
#
# Usage:
#   ./scripts/graphify-update.sh              # rebuild code graph from changed files
#   ./scripts/graphify-update.sh --full       # full semantic re-extraction (slow, needs API key)
#   ./scripts/graphify-update.sh --force      # overwrite even if graph shrinks
#   ./scripts/graphify-update.sh --status     # check hook status
#
# Dependencies: graphify (pip install graphifyy), git

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# ── helpers ──────────────────────────────────────────────────────────
info()  { printf "  \033[1;34m→\033[0m %s\n" "$*"; }
ok()    { printf "  \033[1;32m✔\033[0m %s\n" "$*"; }
warn()  { printf "  \033[1;33m!\033[0m %s\n" "$*"; }
err()   { printf "  \033[1;31m✖\033[0m %s\n" "$*"; }

# ── detect graphify python ───────────────────────────────────────────
detect_graphify_python() {
    local PYTHON=""

    # 1. Check pinned path from hook install
    if [ -f "$REPO_ROOT/.venv/bin/python3" ]; then
        "$REPO_ROOT/.venv/bin/python3" -c "import graphify" 2>/dev/null && PYTHON="$REPO_ROOT/.venv/bin/python3"
    fi

    # 2. Check .graphify_python
    if [ -z "$PYTHON" ] && [ -f "graphify-out/.graphify_python" ]; then
        local FROM_FILE
        FROM_FILE=$(<"graphify-out/.graphify_python" tr -d '[:space:]')
        if [ -n "$FROM_FILE" ] && [ -x "$FROM_FILE" ]; then
            "$FROM_FILE" -c "import graphify" 2>/dev/null && PYTHON="$FROM_FILE"
        fi
    fi

    # 3. Check PATH
    if [ -z "$PYTHON" ]; then
        if command -v python3 >/dev/null 2>&1 && python3 -c "import graphify" 2>/dev/null; then
            PYTHON="python3"
        elif command -v python >/dev/null 2>&1 && python -c "import graphify" 2>/dev/null; then
            PYTHON="python"
        fi
    fi

    if [ -z "$PYTHON" ]; then
        err "graphify is not installed."
        info "Install it: pip install graphifyy  or  uv tool install graphifyy"
        exit 1
    fi

    echo "$PYTHON"
}

# ── main ─────────────────────────────────────────────────────────────
main() {
    local mode="incremental"
    local force_flag=""

    for arg in "$@"; do
        case "$arg" in
            --full)     mode="full"     ;;
            --force)    force_flag="--force" ;;
            --status)   mode="status"   ;;
            -h|--help)
                echo "Usage: $0 [--full|--force|--status]"
                echo ""
                echo "  (no flag)   Incremental code-only rebuild (fast, same as post-commit hook)"
                echo "  --full      Full semantic re-extraction (needs GEMINI_API_KEY or LLM)"
                echo "  --force     Force rebuild even if graph would shrink"
                echo "  --status    Check whether graphify hooks are installed"
                exit 0
                ;;
        esac
    done

    # ── status mode ─────────────────────────────────────────────────
    if [ "$mode" = "status" ]; then
        info "Graphify hook status:"
        graphify hook status 2>&1 || warn "Run 'graphify hook install' to install hooks"
        info "Graphify-out:"
        if [ -d "graphify-out" ]; then
            ok "graphify-out/ exists ($(du -sh graphify-out/ 2>/dev/null | cut -f1))"
            if [ -f "graphify-out/graph.json" ]; then
                local NODES EDGES
                NODES=$("$(detect_graphify_python)" -c "
import json; d=json.load(open('graphify-out/graph.json')); print(len(d.get('nodes',[])))
" 2>/dev/null || echo "?")
                EDGES=$("$(detect_graphify_python)" -c "
import json; d=json.load(open('graphify-out/graph.json'))
links = d.get('links') or d.get('edges') or []
print(len(links))
" 2>/dev/null || echo "?")
                ok "graph.json: $NODES nodes, $EDGES edges"
            else
                warn "graph.json not found — run rebuild first"
            fi
        else
            warn "graphify-out/ does not exist — run 'graphify .' first"
        fi
        exit 0
    fi

    # ── full rebuild mode ──────────────────────────────────────────
    if [ "$mode" = "full" ]; then
        info "Running full semantic re-extraction (may take several minutes)..."
        graphify update . "$force_flag" 2>&1 || {
            err "Full update failed."
            info "Try: graphify update . $force_flag"
            exit 1
        }
        ok "Full update complete."
        exit 0
    fi

    # ── incremental code-only rebuild ──────────────────────────────
    PYTHON="$(detect_graphify_python)"
    info "Using: $PYTHON"

    # Get changed files since last commit
    CHANGED=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || git diff --name-only HEAD 2>/dev/null || true)
    if [ -z "$CHANGED" ]; then
        info "No changed files detected. Rebuilding from all tracked code..."
        CHANGED=$(git ls-files '*.py' '*.js' '*.ts' '*.go' '*.rs' '*.java' 2>/dev/null || true)
    fi

    CODE_CHANGED=$(echo "$CHANGED" | grep -v '^graphify-out/' | grep -E '\.(py|js|ts|go|rs|java)$' || true)

    if [ -z "$CODE_CHANGED" ]; then
        info "No code files changed — nothing to rebuild."
        exit 0
    fi

    info "Rebuilding graph from $(echo "$CODE_CHANGED" | wc -l | tr -d ' ') changed file(s)..."
    echo "$CODE_CHANGED" > /tmp/graphify-changed.txt

    # Run the graphify update via Python
    export GRAPHIFY_FORCE="${force_flag:+1}"
    export GRAPHIFY_CHANGED="$CODE_CHANGED"

    "$PYTHON" -c "
import sys, os
from pathlib import Path
from graphify.watch import _rebuild_code

root = Path('$REPO_ROOT')
changed_paths = [Path(f.strip()) for f in os.environ.get('GRAPHIFY_CHANGED', '').strip().splitlines() if f.strip()]
_rebuild_code(root, changed_paths=changed_paths, force=bool(os.environ.get('GRAPHIFY_FORCE', '')))
" 2>&1

    ok "Graph rebuild complete."
    info "graph.json and GRAPH_REPORT.md updated in graphify-out/"
}

main "$@"
