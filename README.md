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

Note: for local dev, you do **not** need HACS at all (and you’ll avoid any GitHub download issues while iterating).

## Debugging UDP locally (captures real packets)

If you want to see exactly what Home Assistant is sending, you can run a local UDP listener and point your integration at it (set the Fluora Light host to your PC and port to `6767`, or choose another port).

```bash
python tools/udp_dump.py --port 6767
```

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
