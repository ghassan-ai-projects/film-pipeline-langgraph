#!/usr/bin/env bash
# tmux-driven mock-mode demo for the Film Studio TUI.
# Creates a sample film, drives approval/generation, and captures the final
# studio state. Intended for human demos and smoke testing.
set -euo pipefail

SESSION="filmstudio"

# Clean up any leftover session.
tmux kill-session -t "$SESSION" 2>/dev/null || true

cleanup() {
  tmux kill-session -t "$SESSION" 2>/dev/null || true
}
trap cleanup EXIT

# Start the TUI detached. Use a screen-compatible TERM so Textual renders.
tmux new-session -d -s "$SESSION" -x 200 -y 50 \
  "export TERM=screen-256color; cd '$(pwd)' && uv run film-pipeline-tui"

wait_for() {
  local pattern=$1 timeout=${2:-30}
  local deadline=$((SECONDS + timeout))
  until tmux capture-pane -t "$SESSION" -p | grep -qE "$pattern"; do
    if (( SECONDS >= deadline )); then
      echo "TIMEOUT waiting for: $pattern" >&2
      tmux capture-pane -t "$SESSION" -p >&2
      return 1
    fi
    sleep 0.5
  done
}

wait_for "LANGGRAPH FILM STUDIO" 20

# Open the new-project modal and fill the form (F2 submits).
tmux send-keys -t "$SESSION" 'n'
sleep 1.5
tmux send-keys -t "$SESSION" "tmux-demo-$(date +%s)"
tmux send-keys -t "$SESSION" Tab
tmux send-keys -t "$SESSION" 'Tmux Demo'
tmux send-keys -t "$SESSION" Tab
tmux send-keys -t "$SESSION" 'A 20-second demo about a lost key found by moonlight.'
sleep 1
tmux send-keys -t "$SESSION" F2
sleep 8

# Approve through the pipeline until generation (mock mode needs ~7 approvals).
for _ in {1..8}; do
  tmux send-keys -t "$SESSION" 'a'
  sleep 4
done

# Run generation when we reach the generation stage.
tmux send-keys -t "$SESSION" 'g'
sleep 12

# Approve remaining phases (qc, post, delivery).
for _ in {1..6}; do
  tmux send-keys -t "$SESSION" 'a'
  sleep 4
done

# Show the Assets tab with the generated clips.
tmux send-keys -t "$SESSION" '3'
sleep 2

echo "--- captured studio pane (rows 2-22) ---"
tmux capture-pane -t "$SESSION" -p | sed -n '2,22p'
