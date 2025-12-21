#!/usr/bin/env bash
set -eu

# ensure some preconditions
cd "$(dirname "$0")"
type uv
sw_vers

# install tmux-cron command
mkdir -p ~/.local/bin
uv_path=$(type -p uv)
sed "1s:/usr/bin/env uv:$uv_path:" tmux-cron | tee ~/.local/bin/tmux-cron >/dev/null
chmod +x ~/.local/bin/tmux-cron
~/.local/bin/tmux-cron -h

# install LaunchAgent plist
plist=io.github.netj.tmux-cron.plist
tmux_cron_path=$(realpath ~/.local/bin/tmux-cron)
sed "s:/usr/local/bin/tmux-cron:$tmux_cron_path:" "$plist" >~/Library/LaunchAgents/"$plist"
launchctl stop io.github.netj.tmux-cron 2>/dev/null || : ignored
launchctl unload ~/Library/LaunchAgents/"$plist" 2>/dev/null || : ignored
launchctl load -w ~/Library/LaunchAgents/"$plist"
