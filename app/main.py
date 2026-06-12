"""Main entry point for strava-activity-hide."""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import schedule

from app.config import load_config, resolve_paths
from app.strava_client import StravaClient
from app.rules import evaluate_rule, get_actions, apply_actions
from app.generator import generate_config
from app.auth_server import wait_for_code


STATE_PATH = None  # resolved at runtime


def load_state(state_path: str) -> dict:
    """Load persistent state (processed activity IDs)."""
    if Path(state_path).exists():
        with open(state_path, "r") as f:
            return json.load(f)
    return {}


def save_state(state: dict, state_path: str):
    """Save persistent state."""
    Path(state_path).parent.mkdir(parents=True, exist_ok=True)
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)


def process_activities(client: StravaClient, config: dict, state_path: str):
    """Fetch activities within the lookback window and apply rules to unprocessed ones."""
    settings = config.get("settings", {})
    dry_run = settings.get("dry_run", False)
    lookback_hours = settings.get("lookback_hours", 24)
    log_activity_fields = settings.get("log_activity_fields", False)
    rules = config.get("rules", [])

    state = load_state(state_path)
    processed_ids = set(state.get("processed_ids", []))

    # Always use the lookback window to catch late uploads
    after = int((datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).timestamp())

    print(f"\n[{datetime.now().isoformat()}] Checking for activities after {datetime.fromtimestamp(after).isoformat()}...")

    if dry_run:
        print("  (DRY RUN mode - no changes will be made)")

    try:
        activities = client.get_activities(after=after)
    except Exception as e:
        print(f"  ERROR fetching activities: {e}")
        return

    # Filter out already-processed activities
    new_activities = [a for a in activities if a["id"] not in processed_ids]

    if not new_activities:
        print("  No new activities found.")
        return

    print(f"  Found {len(new_activities)} new activit{'y' if len(new_activities) == 1 else 'ies'} ({len(activities)} total in window).")

    for activity in new_activities:
        # Fetch full activity details for rule evaluation
        try:
            full_activity = client.get_activity(activity["id"])
        except Exception as e:
            print(f"  ERROR fetching activity {activity['id']}: {e}")
            continue

        if log_activity_fields:
            print(f"\n  --- Activity fields (id={full_activity['id']}, name='{full_activity.get('name')}') ---")
            for key, value in sorted(full_activity.items()):
                print(f"    {key}: {value!r}")
            print("  ---")

        for rule in rules:
            if evaluate_rule(full_activity, rule):
                rule_name = rule.get("name", "Unnamed rule")
                print(f"  Rule '{rule_name}' matched activity '{full_activity.get('name')}' (id={full_activity['id']})")
                actions = get_actions(rule)
                performed = apply_actions(client, full_activity, actions, dry_run=dry_run)
                for desc in performed:
                    prefix = "[DRY RUN] " if dry_run else ""
                    print(f"    {prefix}{desc}")

        processed_ids.add(activity["id"])

    # Prune processed IDs older than the lookback window to prevent unbounded growth
    # We keep IDs for 2x the lookback to be safe
    state["processed_ids"] = list(processed_ids)
    state["last_pruned"] = int(datetime.now(timezone.utc).timestamp())
    save_state(state, state_path)


def do_auth(client: StravaClient):
    """Run the interactive OAuth2 flow."""
    port = 8000
    redirect_uri = f"http://localhost:{port}/callback"

    print("\n=== Strava OAuth2 Authentication ===")
    print(f"\nOpen this URL in your browser:\n")
    print(f"  {client.get_auth_url(redirect_uri)}")
    print(f"\nWaiting for callback on port {port}...")

    code = wait_for_code(port=port, timeout=120)

    if code:
        client.exchange_code(code)
        print("\nAuthentication successful! Tokens saved.")
    else:
        print("\nERROR: Timed out waiting for OAuth callback.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Strava Activity Hide - Auto-manage Strava activities")
    parser.add_argument("--generate-config", metavar="PATH", help="Generate example config YAML at the given path")
    parser.add_argument("--config", metavar="PATH", help="Path to config YAML file")
    parser.add_argument("--auth", action="store_true", help="Run OAuth2 authentication flow")
    parser.add_argument("--once", action="store_true", help="Run once and exit (no scheduling)")
    parser.add_argument("--dry-run", action="store_true", help="Override config: don't make changes")
    args = parser.parse_args()

    if args.generate_config:
        generate_config(args.generate_config)
        return

    config = load_config(args.config)
    config_path = args.config or os.environ.get("CONFIG_PATH", "/config/config.yaml")
    tokens_path, state_path = resolve_paths(config_path)

    if args.dry_run:
        config.setdefault("settings", {})["dry_run"] = True

    strava_cfg = config["strava"]
    client = StravaClient(
        client_id=strava_cfg["client_id"],
        client_secret=strava_cfg["client_secret"],
        tokens_path=tokens_path,
    )

    if args.auth:
        do_auth(client)
        return

    if not client.is_authenticated():
        print("ERROR: Not authenticated. Run with --auth first to connect your Strava account.")
        sys.exit(1)

    if args.once:
        process_activities(client, config, state_path)
        return

    # Scheduled mode
    interval = config.get("schedule", {}).get("interval_minutes", 15)
    print(f"Strava Activity Hide started. Checking every {interval} minutes.")
    print(f"Dry run: {config.get('settings', {}).get('dry_run', False)}")
    print(f"Rules loaded: {len(config.get('rules', []))}")

    # Run immediately on start
    process_activities(client, config, state_path)

    schedule.every(interval).minutes.do(process_activities, client, config, state_path)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
