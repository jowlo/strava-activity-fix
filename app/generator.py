"""YAML config file generator."""

import yaml


EXAMPLE_CONFIG = {
    "strava": {
        "client_id": "YOUR_CLIENT_ID",
        "client_secret": "YOUR_CLIENT_SECRET",
    },
    "schedule": {
        "interval_minutes": 15,
    },
    "settings": {
        "dry_run": True,
        "lookback_hours": 24,
    },
    "rules": [
        {
            "name": "Hide Zwift activities",
            "description": "Hide all activities uploaded from Zwift",
            "match": "all",
            "conditions": [
                {
                    "field": "external_id",
                    "operator": "contains",
                    "value": "zwift",
                }
            ],
            "actions": ["hide"],
        },
        {
            "name": "Delete short rides",
            "description": "Delete cycling activities shorter than 1km",
            "match": "all",
            "conditions": [
                {
                    "field": "sport_type",
                    "operator": "eq",
                    "value": "Ride",
                },
                {
                    "field": "distance",
                    "operator": "lt",
                    "value": 1000,
                },
            ],
            "actions": ["delete"],
        },
        {
            "name": "Rename indoor activities",
            "description": "Prefix indoor trainer activities",
            "match": "all",
            "conditions": [
                {
                    "field": "trainer",
                    "operator": "eq",
                    "value": True,
                },
            ],
            "actions": [
                {
                    "type": "update",
                    "fields": {
                        "hide_from_home": True,
                    },
                }
            ],
        },
        {
            "name": "Mute Garmin auto-uploads",
            "description": "Mute activities from Garmin device data origin",
            "match": "all",
            "conditions": [
                {
                    "field": "device_name",
                    "operator": "contains",
                    "value": "Garmin",
                },
            ],
            "actions": ["mute"],
        },
    ],
}


def generate_config(output_path: str):
    """Generate an example config YAML file."""
    with open(output_path, "w") as f:
        f.write("# Strava Activity Hide - Configuration\n")
        f.write("# See README.md for full documentation of available fields and operators.\n\n")
        yaml.dump(EXAMPLE_CONFIG, f, default_flow_style=False, sort_keys=False)
    print(f"Generated example config at: {output_path}")
