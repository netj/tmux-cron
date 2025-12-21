# tmux-cron

A tmux-based cron scheduler that runs your scheduled tasks in organized tmux panes, making them visible and interactive.

## What is tmux-cron?

`tmux-cron` is an alternative to traditional cron that runs scheduled jobs inside a tmux session. Each job runs in its own pane, organized by frequency (startup, daily/hourly, weekly, monthly+). This makes it easy to see what's running, check logs, and interact with your scheduled tasks.

Jobs are automatically launched at system startup via a macOS LaunchAgent.

### Why?

Modern macOS versions restrict cron from running scripts due to privacy and security policies, resulting in errors like:

```
bash: /Users/me/some/where/script.sh: Operation not permitted
```

By running jobs through a LaunchAgent instead of cron, tmux-cron bypasses these restrictions while providing better visibility and control over your scheduled tasks.

## Features

- **Visual scheduling**: All cron jobs visible in organized tmux panes
- **Frequency-based organization**: Jobs grouped by how often they run (startup, daily/hourly, weekly, monthly+)
- **Auto-launch at startup**: Runs via macOS LaunchAgent
- **Standard cron syntax**: Use familiar cron expressions and `@reboot`, `@hourly`, etc.
- **Environment variable support**: Define `ENV=value` in your crontab

## Installation

### Prerequisites

- macOS
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [tmux](https://github.com/tmux/tmux)
- [Homebrew](https://brew.sh/) (for path setup)

### Install

Run the installer:

```bash
./Install.tmux-cron.tool
```

This will:
1. Install `tmux-cron` to `~/.local/bin/tmux-cron`
2. Set up a LaunchAgent to auto-start at login
3. Configure PATH via `/etc/paths.d/` for Homebrew

## Migrating from cron

The easiest way to migrate your existing crontab to tmux-cron:

```bash
tmux-cron --migrate-from-crontab
```

### Manual migration (alternative)

If you prefer to edit while migrating:

```bash
crontab -l | pbcopy
tmux-cron -e  # :r!pbpaste in vim
crontab -r
```

## Usage

### Edit your tmux-cron schedule

```bash
tmux-cron -e
```

Opens your crontab in `$EDITOR` (defaults to nano). Example crontab:

```cron
# Environment variables
MAILTO=you@example.com  # XXX email from chatty jobs not supported yet

# Run at startup
@reboot echo 'Mac Started'

# Run every 5 minutes
*/5 * * * * /path/to/frequent-task.sh

# Run weekly on Sunday
0 0 * * 0 /path/to/weekly-backup.sh

# Standard cron syntax also works
0 9 * * 1-5 /path/to/weekday-morning.sh
```

### View current schedule

```bash
tmux-cron -l
```

### Attach to running session

```bash
tmux-cron -a
# or just:
tmux-cron
```

### Migrate from crontab

```bash
tmux-cron --migrate-from-crontab
```

### Session layout

Jobs are organized into tmux windows by frequency:
- **startup**: `@reboot` jobs
- **daily-hourly**: Frequent jobs (≤ daily)
- **weekly**: Occasional jobs (weekly range)
- **monthly-plus**: Rare jobs (monthly or less frequent)
- **misc**: Jobs that don't fit other categories

## Configuration

- **Crontab**: `~/.tmux-cron/crontab`
- **Session config**: `~/.tmux-cron/session.yaml`
- **Environment bridge**: `~/.tmux-cron/bridge.sh`
- **LaunchAgent**: `~/Library/LaunchAgents/io.github.netj.tmux-cron.plist`

## How it works

1. You edit `~/.tmux-cron/crontab` using standard cron syntax
2. tmux-cron parses the crontab and generates a tmuxp YAML configuration
3. Each job runs in its own pane using [croniter](https://github.com/kiorky/croniter) for scheduling
4. The LaunchAgent ensures the tmux session starts at login

## Known Issues

- `MAILTO=` and emailing the stdout/stderr from jobs to the user is not supported yet.

## License

MIT
