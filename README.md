# Strava Activity Hide

Self-hosted tool to automatically hide, mute, modify, or delete Strava activities based on configurable rules. Runs periodically via Docker.

## Quick Start

```bash
# 1. Generate config
uv run strava-activity-hide --generate-config ./config/config.yaml

# 2. Edit config with your Strava API credentials and rules
#    Get credentials at https://www.strava.com/settings/api

# 3. Authenticate (one-time)
uv run strava-activity-hide --config ./config/config.yaml --auth

# 4. Run with Docker
docker compose up -d
```

## Docker Deployment

```bash
mkdir config
cp config.example.yaml config/config.yaml
# Edit config/config.yaml with your credentials

docker compose up -d

# First-time auth (requires port 8000 accessible):
docker compose run --rm -p 8000:8000 strava-activity-hide --auth
```

## Configuration

### Strava API Setup

1. Go to https://www.strava.com/settings/api
2. Create an application
3. Set "Authorization Callback Domain" to `localhost`
4. Note your Client ID and Client Secret

### Config Structure

```yaml
strava:
  client_id: "12345"
  client_secret: "abc123..."

schedule:
  interval_minutes: 15       # How often to check for new activities

settings:
  dry_run: true              # true = log only, false = apply changes
  lookback_hours: 24         # How far back on each container start
  log_activity_fields: false # Log all activity fields (for rule development)

rules:
  - name: "Rule name"
    match: all               # "all" (AND) or "any" (OR)
    conditions:
      - field: <field_name>
        operator: <operator>
        value: <value>
    actions:
      - <action>
```

### Available Operators

| Operator | Description |
|----------|-------------|
| `eq` | Equal (default) |
| `ne` | Not equal |
| `gt` | Greater than |
| `ge` | Greater than or equal |
| `lt` | Less than |
| `le` | Less than or equal |
| `contains` | String contains |
| `not_contains` | String does not contain |
| `matches` | Regex match |
| `in` | Value in list |
| `not_in` | Value not in list |

### Available Actions

| Action | Description |
|--------|-------------|
| `hide` | Set `hide_from_home: true` |
| `mute` | Same as hide (mute from feed) |
| `delete` | Permanently delete the activity |
| `update` | Update arbitrary fields (specify `fields` map) |

### Activity Fields

Any field from the [Strava Activity object](https://developers.strava.com/docs/reference/#api-models-DetailedActivity) can be used. Common fields:

| Field | Type | Description |
|-------|------|-------------|
| `sport_type` | string | Activity type (Run, Ride, Swim, etc.) |
| `type` | string | Legacy activity type |
| `name` | string | Activity title |
| `distance` | float | Distance in meters |
| `moving_time` | int | Moving time in seconds |
| `elapsed_time` | int | Total time in seconds |
| `total_elevation_gain` | float | Elevation gain in meters |
| `trainer` | bool | Indoor trainer activity |
| `commute` | bool | Marked as commute |
| `device_name` | string | Recording device |
| `external_id` | string | External source ID (contains origin info) |
| `upload_id_str` | string | Upload identifier |
| `gear_id` | string | Gear/equipment ID |
| `average_speed` | float | Average speed in m/s |
| `max_speed` | float | Max speed in m/s |
| `average_heartrate` | float | Average HR |
| `max_heartrate` | float | Max HR |
| `start_latlng` | list | Start coordinates [lat, lng] |

Nested fields are supported with dot notation: `map.summary_polyline`.

### Rule Examples

```yaml
# Hide all virtual/indoor activities
- name: "Hide virtual rides"
  conditions:
    - field: sport_type
      operator: in
      value: ["VirtualRide", "VirtualRun"]
  actions: [hide]

# Delete activities with no GPS data shorter than 5 minutes
- name: "Delete accidental starts"
  match: all
  conditions:
    - field: distance
      operator: lt
      value: 100
    - field: elapsed_time
      operator: lt
      value: 300
  actions: [delete]

# Rename commute activities
- name: "Tag commutes"
  conditions:
    - field: commute
      operator: eq
      value: true
  actions:
    - type: update
      fields:
        name: "🚴 Commute"
```

## CLI Reference

```
uv run strava-activity-hide [OPTIONS]

Options:
  --generate-config PATH   Generate example config YAML
  --config PATH            Path to config file (default: /config/config.yaml)
  --auth                   Run OAuth2 authentication flow
  --once                   Run once and exit
  --dry-run                Override: don't apply changes
```

## Data Origin Filtering

To filter by data origin (e.g., Zwift, Garmin, Wahoo), use the `external_id` or `device_name` fields:

```yaml
# external_id often contains the source platform
- field: external_id
  operator: contains
  value: "zwift"

# device_name shows the recording device
- field: device_name
  operator: contains
  value: "Garmin"
```

## License

MIT
