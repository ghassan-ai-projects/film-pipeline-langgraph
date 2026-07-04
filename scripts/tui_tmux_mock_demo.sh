#!/usr/bin/env bash
# tmux-driven mock-mode TUI demo.
# Creates a sample film in the cockpit, drives approval/generation, and
# captures the final Ops tab. This script is intentionally interactive-ish
# (tmux + Textual) and is meant for human demos, not CI.
set -euo pipefail

SESSION="filmtui"

# Clean up any leftover session.
tmux kill-session -t "$SESSION" 2>/dev/null || true

# Start the legacy TUI detached. Use a screen-compatible TERM so Textual renders.
tmux new-session -d -s "$SESSION" \
  "export TERM=screen-256color; cd '$(pwd)' && uv run python -m film_pipeline.tui.cockpit"

cleanup() {
  tmux kill-session -t "$SESSION" 2>/dev/null || true
}
trap cleanup EXIT

sleep 2

# Open command palette and create a sample project.
tmux send-keys -t "$SESSION" '/'
sleep 0.5
tmux send-keys -t "$SESSION" 'create tmux-demo | Tmux Demo | A 20-second demo about a lost key found by moonlight.'
sleep 0.5
tmux send-keys -t "$SESSION" Enter
sleep 6

# Approve phases until we hit generation (mock runtime usually needs ~7 approvals).
for _ in {1..8}; do
  tmux send-keys -t "$SESSION" 'a' 'a'
  sleep 4
done

# Run the generation batch.
tmux send-keys -t "$SESSION" '3'
sleep 1
tmux send-keys -t "$SESSION" 'G'
sleep 12

# Approve the remaining phases (qc, post, delivery).
for _ in {1..5}; do
  tmux send-keys -t "$SESSION" 'a' 'a'
  sleep 4
done

# Visit the required tabs.
tmux send-keys -t "$SESSION" '5'
sleep 1
tmux send-keys -t "$SESSION" '4'
sleep 1
tmux send-keys -t "$SESSION" '8'
sleep 1
tmux send-keys -t "$SESSION" '9'
sleep 1

# Show the final cockpit state.
echo "--- captured TUI pane (rows 4-22) ---"
tmux capture-pane -t "$SESSION" -p | sed -n '4,22p'
