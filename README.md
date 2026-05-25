# OTA Backend (FastAPI + MongoDB Atlas + GridFS)

Production-ready OTA backend for ESP32-class devices.

## Features
- Public OTA check endpoint: `GET /smart_switch/check?mac=<mac>&ver=<semver>`
- Firmware binary storage in MongoDB GridFS
- Firmware metadata + rollout/overrides/device state in normal MongoDB collections
- Deterministic rollout percentage by MAC hash
- Admin API for release creation, firmware upload, enable/disable, rollout, overrides
- Admin auth with API key and/or JWT bearer token
- Rate limiting on public check endpoint
- Request logging with request ID
- Health endpoint: `GET /healthz`
- Render-ready deployment config

## Architecture
- **Collections**
  - `devices`: per-device state
  - `releases`: firmware release metadata
  - `device_overrides`: per-device pinned release
  - `audit_checks`: every OTA check audit trail
- **GridFS bucket** (default `firmware`)
  - stores `.bin` contents with metadata: `device_type`, `version`, `sha256`, `uploaded_at`, `filename`, `size`, `mime`

## Check Contract
`GET /smart_switch/check`
- No update:
```json
{"update_available": false}
```
- Update:
```json
{"update_available": true, "version": "1.2.0", "firmware_url": "https://..."}
```
- Extended fields may also include: `sha256`, `size`

## Decision Flow
1. Validate MAC + semver
2. Upsert/update device last-seen state
3. Blocked device => no update
4. Evaluate device override
5. Evaluate active release for `device_type`
6. Enforce release version > current version
7. Enforce deterministic rollout percentage by MAC hash
8. Return contract response
9. Write audit log

## Local Setup
1. Create venv and install:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```
2. Copy env:
```bash
cp .env.example .env
```
3. Fill `.env` with MongoDB Atlas credentials and secrets.
4. Run API:
```bash
uvicorn app.main:app --reload
```

## Test
```bash
pytest -q
```

## Seed Sample Data
Seeds one `smart_switch` device, one release, and one GridFS firmware object:
```bash
python scripts/seed.py
```

## Admin API
Use `X-API-Key: <ADMIN_API_KEY>` (or Bearer JWT).

### Create release
```bash
curl -X POST "$BASE/admin/releases" \
  -H "x-api-key: $ADMIN_API_KEY" \
  -H "content-type: application/json" \
  -d '{"device_type":"smart_switch","version":"1.2.0","rollout_percentage":20,"enabled":false}'
```

### Upload `.bin` to GridFS for release
```bash
curl -X POST "$BASE/admin/releases/<release_id>/firmware" \
  -H "x-api-key: $ADMIN_API_KEY" \
  -F "file=@./firmware.bin;type=application/octet-stream"
```

### Enable/disable release
```bash
curl -X PATCH "$BASE/admin/releases/<release_id>/enabled" \
  -H "x-api-key: $ADMIN_API_KEY" \
  -H "content-type: application/json" \
  -d '{"enabled":true}'
```

### Update rollout percentage
```bash
curl -X PATCH "$BASE/admin/releases/<release_id>/rollout" \
  -H "x-api-key: $ADMIN_API_KEY" \
  -H "content-type: application/json" \
  -d '{"rollout_percentage":35}'
```

### Upsert device override
```bash
curl -X PUT "$BASE/admin/overrides/smart_switch/AA:BB:CC:DD:EE:FF" \
  -H "x-api-key: $ADMIN_API_KEY" \
  -H "content-type: application/json" \
  -d '{"version":"1.2.0","reason":"pilot"}'
```

### Delete device override
```bash
curl -X DELETE "$BASE/admin/overrides/smart_switch/AA:BB:CC:DD:EE:FF" \
  -H "x-api-key: $ADMIN_API_KEY"
```

## Public OTA API
### Check for update
```bash
curl "$BASE/smart_switch/check?mac=AA:BB:CC:DD:EE:FF&ver=1.0.0"
```

### Download firmware
```bash
curl -L "$BASE/firmware/smart_switch/1.2.0/download?exp=<...>&sig=<...>" -o fw.bin
```

## Render Deployment
1. Push this repo to GitHub.
2. Create new Render Web Service from repo.
3. Render will detect `render.yaml`.
4. Set sensitive env vars in Render dashboard:
   - `MONGO_URI`
   - `ADMIN_API_KEY`
   - `SIGNED_URL_SECRET`
   - `PUBLIC_BASE_URL`
5. Deploy and verify:
```bash
curl https://<service>.onrender.com/healthz
```

## Index Bootstrap / Migrations
Indexes are created idempotently on startup via `ensure_indexes()`.
No separate migration runner is required for initial setup.

## Free-tier caveats
- Render free instances sleep when idle, so first request can be slow.
- MongoDB free tier has lower throughput/connection limits; tune pool sizes if needed.
- For production traffic, upgrade both tiers and use monitoring/alerts.
