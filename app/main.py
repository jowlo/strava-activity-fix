"""Main entry point for strava-activity-hide."""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import schedule

from app.config import load_config
from app.strava_client import StravaClient
from app.rules import evaluate_rule, get_actions, apply_actions
from app.generator import generate_config
from app.auth_server import wait_for_code


STATE_PATH = os.environ.get("STATE_PATH", "/config/state.json")


def load_state() -> dict:
    """Load persistent state (last check timestamp)."""
    if Path(STATE_PATH).exists():
        with open(STATE_PATH, "r") as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    """Save persistent state."""
    Path(STATE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def process_activities(client: StravaClient, config: dict):
    """Fetch new activities and apply rules."""
    settings = config.get("settings", {})
    dry_run = settings.get("dry_run", False)
    lookback_hours = settings.get("lookback_hours", 24)
    rules = config.get("rules", [])

    state = load_state()
    last_check = state.get("last_check")

    # Determine the 'after' timestamp
    if last_check:
        after = int(last_check)
    else:
        after = int((datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).timestamp())

    now_ts = int(datetime.now(timezone.utc).timestamp())

    print(f"\n[{datetime.now().isoformat()}] Checking for activities after {datetime.fromtimestamp(after).isoformat()}...")

    if dry_run:
        print("  (DRY RUN mode - no changes will be made)")

    try:
        activities = client.get_activities(after=after)
    except Exception as e:
        print(f"  ERROR fetching activities: {e}")
        return

    if not activities:
        print("  No new activities found.")
        state["last_check"] = now_ts
        save_state(state)
        return

    print(f"  Found {len(activities)} new activit{'y' if len(activities) == 1 else 'ies'}.")

    for activity in activities:
        # Fetch full activity details for rule evaluation
        try:
            full_activity = client.get_activity(activity["id"])
        except Exception as e:
            print(f"  ERROR fetching activity {activity['id']}: {e}")
            continue

        for rule in rules:
            if evaluate_rule(full_activity, rule):
                rule_name = rule.get("name", "Unnamed rule")
                print(f"  Rule '{rule_name}' matched activity '{full_activity.get('name')}' (id={full_activity['id']})")
                actions = get_actions(rule)
                performed = apply_actions(client, full_activity, actions, dry_run=dry_run)
                for desc in performed:
                    prefix = "[DRY RUN] " if dry_run else ""
                    print(f"    {prefix}{desc}")

    state["last_check"] = now_ts
    save_state(state)


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

    if args.dry_run:
        config.setdefault("settings", {})["dry_run"] = True

    strava_cfg = config["strava"]
    client = StravaClient(
        client_id=strava_cfg["client_id"],
        client_secret=strava_cfg["client_secret"],
    )

    if args.auth:
        do_auth(client)
        return

    if not client.is_authenticated():
        print("ERROR: Not authenticated. Run with --auth first to connect your Strava account.")
        sys.exit(1)

    if args.once:
        process_activities(client, config)
        return

    # Scheduled mode
    interval = config.get("schedule", {}).get("interval_minutes", 15)
    print(f"Strava Activity Hide started. Checking every {interval} minutes.")
    print(f"Dry run: {config.get('settings', {}).get('dry_run', False)}")
    print(f"Rules loaded: {len(config.get('rules', []))}")

    # Run immediately on start
    process_activities(client, config)

    schedule.every(interval).minutes.do(process_activities, client, config)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
