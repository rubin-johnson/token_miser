#!/usr/bin/env bash
# Notify when Claude Code needs input.
# Sends terminal bell (taskbar flash) + Windows balloon notification.

set -euo pipefail

HOOK_INPUT=$(cat)
MESSAGE=$(echo "$HOOK_INPUT" | jq -r '.message // "Ready for input"')

# Terminal bell - instant taskbar flash in Windows Terminal
printf '\a'

# Windows balloon notification (background so hook returns fast)
powershell.exe -NoProfile -Command "
  Add-Type -AssemblyName System.Windows.Forms
  \$n = New-Object System.Windows.Forms.NotifyIcon
  \$n.Icon = [System.Drawing.SystemIcons]::Information
  \$n.Visible = \$true
  \$n.ShowBalloonTip(5000, 'Claude Code', '$MESSAGE', 'Info')
  Start-Sleep -Seconds 2
  \$n.Dispose()
" >/dev/null 2>&1 &

exit 0
