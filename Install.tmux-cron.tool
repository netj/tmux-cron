#!/usr/bin/env bash
set -eu

# ensure some preconditions
cd "$(dirname "$0")"
type uv
sw_vers

# install homebrew to /etc/paths.d/ such that macOS path_helper includes the path
brew_bin=$(type -p brew); brew_bin=$(dirname "$brew_bin")
test "$(cat /etc/paths.d/10-homebrew)" = "$brew_bin" ||
    sudo tee /etc/paths.d/10-homebrew <<<"$brew_bin"

mkdir -p ~/.local/bin
# install exec-path_helper command that helps with
{
    echo '#!/bin/sh'
    echo 'set -eu; eval "$(/usr/libexec/path_helper)"; exec "$@"'
} >~/.local/bin/exec-path_helper
chmod +x ~/.local/bin/exec-path_helper

# install tmux-cron command
path_helper=$(PATH=~/.local/bin:"$PATH"; type -p exec-path_helper)
sed "1s:#!.* uv:#!/usr/bin/env -S $path_helper uv:" tmux-cron.py | tee ~/.local/bin/tmux-cron >/dev/null
chmod +x ~/.local/bin/tmux-cron
~/.local/bin/tmux-cron -h

# install LaunchAgent plist
plist=io.github.netj.tmux-cron.plist
tmux_cron_path=$(realpath ~/.local/bin/tmux-cron)
sed "s:/usr/local/bin/tmux-cron:$tmux_cron_path:" "$plist" >~/Library/LaunchAgents/"$plist"
launchctl stop io.github.netj.tmux-cron 2>/dev/null || : ignored
launchctl unload ~/Library/LaunchAgents/"$plist" 2>/dev/null || : ignored
launchctl load -w ~/Library/LaunchAgents/"$plist"
