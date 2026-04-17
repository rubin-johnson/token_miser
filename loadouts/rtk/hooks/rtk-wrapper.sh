#!/usr/bin/env bash
# Wrapper that ensures $HOME/.claude/bin is on PATH so rtk-rewrite.sh finds the bundled rtk.
export PATH="$HOME/.claude/bin:$PATH"
exec bash "$HOME/.claude/hooks/rtk-rewrite.sh"
