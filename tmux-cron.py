#!/usr/bin/env uv run --script
# /// script
# dependencies = [
#   "croniter",
#   "pyyaml",
#   "tmuxp",
# ]
# ///

import os
import sys
import subprocess
import shutil
import tempfile
import shlex
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
BASE_DIR = Path.home() / ".tmux-cron"
CRONTAB_FILE = BASE_DIR / "crontab"
YAML_FILE = BASE_DIR / "session.yaml"
BRIDGE_SCRIPT = BASE_DIR / "bridge.sh"
SESSION_NAME = "tmux-cron"
SELF_PATH = os.path.abspath(__file__)

BASE_DIR.mkdir(parents=True, exist_ok=True)

def sh(cmd: str, **env_vars):
    current_env = os.environ.copy()
    current_env.update({k: str(v) for k, v in env_vars.items()})
    return subprocess.run(["bash", "-c", cmd], env=current_env, stdout=sys.stdout, stderr=sys.stderr)

def get_frequency_category(schedule):
    if schedule == "@reboot":
        return "startup"
    
    from croniter import croniter
    try:
        # Normalize aliases for the delta check
        lookup = {
            "@hourly": "0 * * * *", 
            "@daily": "0 0 * * *", 
            "@weekly": "0 0 * * 0", 
            "@monthly": "0 0 1 * *", 
            "@yearly": "0 0 1 1 *"
        }
        clean_sched = lookup.get(schedule, schedule)
        
        now = datetime.now()
        it = croniter(clean_sched, now)
        next_run = it.get_next(datetime)
        after_that = it.get_next(datetime)
        delta = after_that - next_run
        
        if delta <= timedelta(days=1):
            return "frequent"
        if delta <= timedelta(weeks=1):
            return "occasional"
        return "rare"
    except Exception:
        return "misc"

def generate_assets(lines, dry_run=False):
    import yaml
    
    # Initialize yaml_dict early to avoid UnboundLocalError
    yaml_dict = {"session_name": SESSION_NAME, "windows": []}
    
    categories = {
        "startup": {"name": "startup", "panes": []},
        "frequent": {"name": "daily-hourly", "panes": []},
        "occasional": {"name": "weekly", "panes": []},
        "rare": {"name": "monthly-plus", "panes": []},
        "misc": {"name": "misc", "panes": []}
    }
    
    env_lines = ["#!/bin/bash"]
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        
        # Environment variables
        if "=" in line and not line.startswith("@") and not line[0].isdigit() and "*" not in line.split('=')[0]:
            env_lines.append(f'export {line}')
            continue

        parts = line.split(maxsplit=5)
        if len(parts) < 2: continue
        
        schedule = parts[0]
        if schedule.startswith("@") and schedule != "@reboot":
            cat = get_frequency_category(schedule)
            command = " ".join(parts[1:])
        elif schedule == "@reboot":
            cat = "startup"
            command = " ".join(parts[1:])
        else:
            if len(parts) < 6: continue
            schedule, command = " ".join(parts[:5]), parts[5]
            cat = get_frequency_category(schedule)

        quoted_args = " ".join(shlex.quote(a) for a in ["--run", schedule, command])
        run_cmd = f'"$TMUX_CRON" {quoted_args}'
        categories[cat]["panes"].append(run_cmd)

    env_lines.append('exec "$@"')
    
    # Build the window structure
    class LiteralStr(str): pass
    yaml.add_representer(LiteralStr, lambda d, data: d.represent_scalar('tag:yaml.org,2002:str', data, style='|'))

    for cat_id in ["startup", "frequent", "occasional", "rare", "misc"]:
        cat = categories[cat_id]
        if cat["panes"]:
            yaml_dict["windows"].append({
                "window_name": cat["name"],
                "layout": "tiled",
                "panes": [LiteralStr(p) for p in cat["panes"]]
            })

    if not dry_run:
        BRIDGE_SCRIPT.write_text("\n".join(env_lines))
        BRIDGE_SCRIPT.chmod(0o755)
        with open(YAML_FILE, "w") as f:
            yaml.dump(yaml_dict, f, default_flow_style=False)
            
    return yaml_dict

def sync_and_launch(attach=True):
    if not CRONTAB_FILE.exists():
        print("No crontab found. Use 'tmux-cron -e' to create one.")
        return
    
    is_stale = not YAML_FILE.exists() or CRONTAB_FILE.stat().st_mtime > YAML_FILE.stat().st_mtime
    if is_stale:
        print("Crontab changed. Regenerating assets...")
        generate_assets(CRONTAB_FILE.read_text().splitlines())
        sh('tmux kill-session -t "$SESSION" 2>/dev/null', SESSION=SESSION_NAME)
    
    sh('tmux has-session -t "$SESSION" 2>/dev/null || TMUX_CRON="$SELF" uv run tmuxp load -d "$CONFIG"', 
       SESSION=SESSION_NAME, CONFIG=str(YAML_FILE), SELF=SELF_PATH)
    
    if attach:
        sh('tmux attach -t "$SESSION"', SESSION=SESSION_NAME)

def cron_runner(schedule, command):
    from croniter import croniter
    import time

    sh('tmux set-option -p -t "$TMUX_PANE" automatic-rename off')
    sys.stdout.write(f"\033c\033]2;{command[:50]}\007")
    sys.stdout.flush()

    def log(msg):
        timestamp = datetime.now().strftime('%Y-%m-%d %a %H:%M:%S')
        print(f"[{timestamp}] tmux-cron: {msg}")

    sh('reset; tmux clear-history -t "$TMUX_PANE"')
    log(f"scheduled job for {schedule}: {command}\n")

    def execute():
        log(f"starting job: {command}")
        sh('"$BRIDGE" bash -c "$CMD"', BRIDGE=str(BRIDGE_SCRIPT), CMD=command)
        log(f"finished job: {command}")

    if schedule == "@reboot":
        execute()
        while True: time.sleep(86400)

    iter = croniter(schedule, datetime.now())
    while True:
        next_run = iter.get_next(datetime)
        sleep_time = (next_run - datetime.now()).total_seconds()
        if sleep_time > 0:
            time.sleep(sleep_time)
        execute()

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sync_and_launch(attach=True)
    elif args[0] in ["-e", "--edit"]:
        if not CRONTAB_FILE.exists(): 
            CRONTAB_FILE.write_text("# @reboot echo 'Mac Started'\n# */5 * * * * echo 'Frequent'\n# 0 0 * * 0 echo 'Weekly'\n")
        with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as tmp:
            shutil.copyfile(CRONTAB_FILE, tmp.name)
            sh('${EDITOR:-nano} "$TARGET"', TARGET=tmp.name)
            try:
                with open(tmp.name, 'r') as f: 
                    generate_assets(f.readlines(), dry_run=True)
                shutil.copyfile(tmp.name, CRONTAB_FILE)
                sync_and_launch(attach=True)
            except Exception as e: 
                log(f"Error during crontab validation: {e}")
            finally: 
                os.unlink(tmp.name)
    elif args[0] in ["-l", "--list"]:
        print(CRONTAB_FILE.read_text() if CRONTAB_FILE.exists() else "Empty.")
    elif args[0] in ["-a", "--attach"]:
        sh('tmux attach -t "$SESSION"', SESSION=SESSION_NAME)
    elif args[0] == "--run" and len(args) == 3:
        cron_runner(args[1], args[2])
    else:
        print("Usage: tmux-cron [-e|-l|-a]")
