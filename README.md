# Fluora Light (Home Assistant Integration)

This is a custom Home Assistant integration to control **Fluora** lights over the local network.

## Local development (Docker)

Run Home Assistant locally with this repo’s `custom_components` mounted in, so edits take effect immediately on the next integration reload.

1. Create `config/` (already included here) and keep it in this repo for local-only config/state.
2. Start Home Assistant:

```bash
docker compose up
```

Then open `http://localhost:8123`, finish onboarding, and add the “Fluora Light” integration.

## Install (HACS)

1. In Home Assistant, go to HACS → Integrations → “Custom repositories”.
2. Add your GitHub repository URL and select category “Integration”.
3. Install “Fluora Light”.

## Install (manual)

Copy `custom_components/fluora_light` into your Home Assistant config directory:

`<config>/custom_components/fluora_light`

## Setup

In Home Assistant:

Settings → Devices & services → Add integration → “Fluora Light”

You’ll be prompted for:

- Name
- Hostname / IP address
- Port (default `6767`)

## Notes

This integration updates Home Assistant state based on commands sent to the light (it does not currently read back state from the device).
