"""Configuration loading and validation."""

import yaml
import os
import sys
from pathlib import Path


DEFAULT_CONFIG_PATH = "/config/config.yaml"
DEFAULT_TOKENS_PATH = "/config/tokens.json"
DEFAULT_STATE_PATH = "/config/state.json"


def resolve_paths(config_path: str) -> tuple[str, str]:
    """Resolve tokens and state paths relative to the config file when defaults aren't usable."""
    config_dir = str(Path(config_path).parent.resolve())
    tokens_path = os.environ.get("TOKENS_PATH", str(Path(config_dir) / "tokens.json"))
    state_path = os.environ.get("STATE_PATH", str(Path(config_dir) / "state.json"))
    return tokens_path, state_path


def load_config(path: str = None) -> dict:
    """Load and validate the YAML configuration file."""
    config_path = path or os.environ.get("CONFIG_PATH", DEFAULT_CONFIG_PATH)

    if not Path(config_path).exists():
        print(f"ERROR: Config file not found at {config_path}")
        print("Run with --generate-config to create a template.")
        sys.exit(1)

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    _validate_config(config)
    return config


def _validate_config(config: dict):
    """Validate required config fields."""
    required = ["strava"]
    for key in required:
        if key not in config:
            raise ValueError(f"Missing required config section: '{key}'")

    strava = config["strava"]
    for key in ["client_id", "client_secret"]:
        if key not in strava:
            raise ValueError(f"Missing required strava config: '{key}'")

    if "rules" not in config or not config["rules"]:
        print("WARNING: No rules defined in config. Nothing will be processed.")
