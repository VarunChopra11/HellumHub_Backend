# Hellum IoT Core Backend — Production Deployment Guide

> **Domain used throughout this guide:** `api.hellum.dev`
> Replace with your actual domain wherever you see it.

---

## Table of Contents

1. [Prerequisites & Architecture Overview](#1-prerequisites--architecture-overview)
2. [Server Provisioning](#2-server-provisioning)
3. [Install System Dependencies](#3-install-system-dependencies)
4. [Domain & DNS Setup](#4-domain--dns-setup)
5. [TLS Certificates with Let's Encrypt](#5-tls-certificates-with-lets-encrypt)
6. [Clone & Configure the Repository](#6-clone--configure-the-repository)
7. [Write the Dockerfile](#7-write-the-dockerfile)
8. [Configure Mosquitto MQTT Broker](#8-configure-mosquitto-mqtt-broker)
9. [Configure the Environment File (.env)](#9-configure-the-environment-file-env)
10. [Google Cloud Console Setup](#10-google-cloud-console-setup)
11. [Deploy with Docker Compose](#11-deploy-with-docker-compose)
12. [Nginx Reverse Proxy Setup](#12-nginx-reverse-proxy-setup)
13. [Verify the Deployment](#13-verify-the-deployment)
14. [Bootstrap: First Admin Login & Device Model Registration](#14-bootstrap-first-admin-login--device-model-registration)
15. [Provision the First ESP32 Device](#15-provision-the-first-esp32-device)
16. [Google Home Actions Console Setup](#16-google-home-actions-console-setup)
17. [Certificate Auto-Renewal](#17-certificate-auto-renewal)
18. [Log Monitoring & Maintenance](#18-log-monitoring--maintenance)
19. [Security Hardening Checklist](#19-security-hardening-checklist)
20. [Troubleshooting Reference](#20-troubleshooting-reference)

---

## 1. Prerequisites & Architecture Overview

### Server Requirements

| Component | Minimum | Recommended |
|---|---|---|
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| CPU | 1 vCPU | 2 vCPU |
| RAM | 1 GB | 2 GB |
| Disk | 20 GB SSD | 40 GB SSD |
| Open Ports | 22, 80, 443, 8883 | Same |

> Port **8883** (MQTTS) must be open for ESP32 devices. Ports **80** and **443** serve the API via Nginx. Port **1883** (plain MQTT) must **NOT** be exposed externally — it is internal Docker traffic only.

### Architecture Diagram

```
Internet
  |
  |-- :443  --> Nginx (TLS termination) --> FastAPI :8000  --> MongoDB
  |                                              |
  `-- :8883 --> Mosquitto (MQTTS)               | (internal Docker network)
                    |                            |
                    `----------------------------'
                        (MQTT plain :1883)
                    |
              ESP32 Devices
```

### Services
| Service | Container | Purpose |
|---|---|---|
| `hellum_api` | FastAPI app | REST API, Google Home fulfillment, MQTT bridge |
| `hellum_mosquitto` | Eclipse Mosquitto 2.0 | MQTT broker (TLS on 8883, plain on 1883) |
| MongoDB | External / Atlas | Persistent data store |

---

## 2. Server Provisioning

### 2.1 Create a VPS

Use any cloud provider (DigitalOcean, Hetzner, AWS Lightsail, Vultr). Choose **Ubuntu 22.04 LTS**.

### 2.2 Initial SSH Access

```bash
ssh root@<server-ip>
```

### 2.3 Create a Non-Root User

```bash
adduser hellum
usermod -aG sudo hellum
# Copy your SSH key to the new user
rsync --archive --chown=hellum:hellum ~/.ssh /home/hellum
```

Log out and re-connect as the new user for all remaining steps:

```bash
ssh hellum@<server-ip>
```

### 2.4 Configure UFW Firewall

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp        # SSH
sudo ufw allow 80/tcp        # HTTP (Let's Encrypt + Nginx redirect)
sudo ufw allow 443/tcp       # HTTPS API
sudo ufw allow 8883/tcp      # MQTTS (ESP32 devices)
sudo ufw enable
sudo ufw status
```

> **CAUTION:** Do NOT add a UFW rule for port 1883. It must remain internal-only within the Docker bridge network.

---

## 3. Install System Dependencies

### 3.1 Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### 3.2 Install Docker

```bash
# Add Docker's official GPG key and repository
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) \
  signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Allow current user to run Docker without sudo
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

### 3.3 Install Nginx, Certbot, and MQTT Clients

```bash
sudo apt install -y nginx certbot python3-certbot-nginx mosquitto-clients
```

---

## 4. Domain & DNS Setup

In your DNS provider's dashboard, create the following **A record**:

| Record | Type | Value |
|---|---|---|
| `api.hellum.dev` | A | `<your-server-ip>` |

Wait for DNS propagation (usually 1–10 minutes). Verify with:

```bash
dig +short api.hellum.dev
# Should return your server IP
```

---

## 5. TLS Certificates with Let's Encrypt

The **same certificate** is used for both HTTPS (Nginx) and MQTTS (Mosquitto port 8883).

### 5.1 Obtain the Certificate

```bash
# Stop nginx temporarily so certbot can bind port 80
sudo systemctl stop nginx

# Obtain certificate (standalone mode)
sudo certbot certonly --standalone \
  -d api.hellum.dev \
  --agree-tos \
  --email admin@hellum.dev \
  --no-eff-email
```

Expected output:
```
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/api.hellum.dev/fullchain.pem
Key is saved at:         /etc/letsencrypt/live/api.hellum.dev/privkey.pem
```

### 5.2 Verify Certificate Files Exist

```bash
sudo ls -la /etc/letsencrypt/live/api.hellum.dev/
# fullchain.pem  privkey.pem  chain.pem  cert.pem
```

### 5.3 Allow the Mosquitto Docker Container to Read Certificates

Mosquitto runs as uid `1883` inside the container but the cert files are owned by root on the host.
The `docker-compose.yml` mounts `/etc/letsencrypt` read-only. To allow Mosquitto to read the private key:

```bash
sudo chmod 0755 /etc/letsencrypt/live/
sudo chmod 0755 /etc/letsencrypt/archive/
sudo chmod 0755 /etc/letsencrypt/archive/api.hellum.dev/
sudo chmod 0644 /etc/letsencrypt/archive/api.hellum.dev/*.pem
```

---

## 6. Clone & Configure the Repository

```bash
cd /home/hellum
git clone https://github.com/YOUR_ORG/OTA_Server.git hellum-backend
cd hellum-backend
```

> If the repo is private, use an SSH deploy key or a personal access token.

---

## 7. Write the Dockerfile

The repository does not include a Dockerfile. Create one now in the project root:

```bash
cat > Dockerfile << 'DOCKERFILE'
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Non-root user for container security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--log-level", "info"]
DOCKERFILE
```

Add a `.dockerignore` to keep image size small:

```bash
cat > .dockerignore << 'EOF'
.git
.env
__pycache__
*.pyc
*.pyo
.pytest_cache
tests/
sample/
*.md
.gitignore
EOF
```

---

## 8. Configure Mosquitto MQTT Broker

### 8.1 Verify the Config File

The `mosquitto/mosquitto.conf` file is already in the repository.
Confirm the certificate paths match your domain:

```bash
grep "api.hellum.dev" mosquitto/mosquitto.conf
# Should show 3 lines pointing to /etc/letsencrypt/live/api.hellum.dev/
```

If your domain differs, replace all occurrences:

```bash
sed -i 's/api.hellum.dev/your.actual.domain/g' mosquitto/mosquitto.conf
```

### 8.2 Create the Password File

```bash
# Create an empty password file (will be populated per-device in Step 15)
touch mosquitto/passwd
chmod 600 mosquitto/passwd
```

### 8.3 (Optional) Enable Per-Device Topic ACLs

For production security, create an ACL file so each ESP32 can only publish
to its own state topic and subscribe to its own command topic:

```bash
cat > mosquitto/acl << 'EOF'
# Per-device access control
# Pattern: %u substitutes the MQTT username

# ESP32 devices: can only publish state and read commands for their own MAC
pattern write smarthome/device/%c/state
pattern read  smarthome/device/%c/cmd

# All authenticated users can publish to the registration topic
topic write smarthome/register
EOF
```

Then add `acl_file /mosquitto/config/acl` to `mosquitto/mosquitto.conf`
under the listener 8883 section and mount the file in `docker-compose.yml`.

---

## 9. Configure the Environment File (.env)

```bash
cp .env.example .env
nano .env
```

### 9.1 MongoDB

**MongoDB Atlas (recommended for production):**
```env
MONGO_URI=mongodb+srv://USERNAME:PASSWORD@cluster.mongodb.net/?retryWrites=true&w=majority
MONGO_DB_NAME=hellum_iot
```

**Self-hosted MongoDB on the same server:**
```env
MONGO_URI=mongodb://host.docker.internal:27017
MONGO_DB_NAME=hellum_iot
```

If using `host.docker.internal`, add the following to the `api` service in `docker-compose.yml`:
```yaml
api:
  extra_hosts:
    - "host.docker.internal:host-gateway"
```

### 9.2 Generate All Required Secrets

Run each command and paste the output into `.env`:

```bash
echo "OAUTH_CLIENT_SECRET=$(openssl rand -hex 32)"
echo "CONSUMER_JWT_SECRET=$(openssl rand -hex 32)"
echo "SIGNED_URL_SECRET=$(openssl rand -hex 32)"
```

### 9.3 Complete `.env` Reference

```env
# Application
ENVIRONMENT=production
LOG_LEVEL=INFO

# MongoDB
MONGO_URI=<your-mongo-uri>
MONGO_DB_NAME=hellum_iot
MONGO_MIN_POOL_SIZE=5
MONGO_MAX_POOL_SIZE=50

# MQTT (overridden by docker-compose.yml to use service name)
MQTT_BROKER_HOST=mosquitto
MQTT_BROKER_PORT=1883

# Google Sign-In (single Client ID for consumers + admins)
GOOGLE_CLIENT_ID=<from Step 10>

# Admin RBAC
SUPER_ADMIN_EMAIL=your-personal-google@gmail.com

# Google Home OAuth Account Linking
OAUTH_CLIENT_ID=hellum-google-home
OAUTH_CLIENT_SECRET=<openssl rand -hex 32>
OAUTH_REDIRECT_URIS=https://oauth-redirect.googleusercontent.com/r/YOUR_GH_PROJECT_ID
OAUTH_AUTH_CODE_TTL_SECONDS=600

# Consumer JWT
CONSUMER_JWT_SECRET=<openssl rand -hex 32>
CONSUMER_JWT_ALGORITHM=HS256
CONSUMER_JWT_TTL_SECONDS=3600
CONSUMER_REFRESH_TOKEN_TTL_SECONDS=2592000

# Device Provisioning
BINDING_TOKEN_TTL_SECONDS=600

# OTA firmware URLs
PUBLIC_BASE_URL=https://api.hellum.dev
SIGNED_URL_SECRET=<openssl rand -hex 32>
SIGNED_URL_TTL_SECONDS=1800

# CORS (your frontend domains, comma-separated)
CORS_ORIGINS=https://app.hellum.dev,https://admin.hellum.dev
```

Protect the file:
```bash
chmod 600 .env
```

> **CAUTION:** Never commit `.env` to version control. Verify with `git status` before any push.

---

## 10. Google Cloud Console Setup

This generates the `GOOGLE_CLIENT_ID` used for both consumer login and admin authentication.

### 10.1 Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project selector at the top → **New Project**
3. Name: `Hellum IoT` → **Create**

### 10.2 Configure the OAuth Consent Screen

1. Navigate to **APIs & Services → OAuth consent screen**
2. Choose **External** → **Create**
3. Fill in:
   - **App name:** `Hellum Smart Home`
   - **User support email:** admin@hellum.dev
   - **Developer contact information:** admin@hellum.dev
4. Click **Save and Continue**
5. **Scopes** — click "Add or Remove Scopes", add:
   - `openid`
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
6. Click **Save and Continue**
7. **Test users** — add your personal Google email for testing
8. Click **Save and Continue** → **Back to Dashboard**

### 10.3 Create an OAuth 2.0 Client ID

1. Navigate to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. **Application type:** Web application
4. **Name:** `Hellum IoT Backend`
5. **Authorized JavaScript origins:** `https://app.hellum.dev`
6. **Authorized redirect URIs:** `https://app.hellum.dev/auth/callback`
7. Click **Create**
8. **Copy the Client ID** — it looks like `123456789-abc....apps.googleusercontent.com`

### 10.4 Update .env with the Client ID

```bash
# Edit .env and set:
GOOGLE_CLIENT_ID=123456789-abc....apps.googleusercontent.com
```

### 10.5 Enable the Smart Home API

1. Go to **APIs & Services → Library**
2. Search for "Smart Home"
3. Click **Google Smart Home Actions API** → **Enable**

---

## 11. Deploy with Docker Compose

### 11.1 Build and Start All Services

```bash
cd /home/hellum/hellum-backend

# Build the API image
docker compose build --no-cache

# Start all services in detached mode
docker compose up -d

# Confirm all containers are running
docker compose ps
```

Expected output:
```
NAME                STATUS     PORTS
hellum_mosquitto    running    0.0.0.0:1883->1883/tcp, 0.0.0.0:8883->8883/tcp
hellum_api          running    0.0.0.0:8000->8000/tcp
```

### 11.2 Watch Startup Logs

```bash
docker compose logs -f api
```

Look for these success indicators:
```
INFO:     Application startup complete.
INFO      mqtt_bridge_starting host=mosquitto port=1883
INFO      mqtt_bridge_connected host=mosquitto port=1883
INFO      mqtt_bridge_subscribed state=smarthome/device/+/state register=smarthome/register
```

If you see `mqtt_bridge_disconnected` — Mosquitto isn't ready yet. It usually connects
within a few seconds. If it persists, check Mosquitto logs:

```bash
docker compose logs mosquitto
```

---

## 12. Nginx Reverse Proxy Setup

Nginx terminates HTTPS and proxies traffic to FastAPI on port 8000.

### 12.1 Create the Nginx Site Config

```bash
sudo nano /etc/nginx/sites-available/hellum-api
```

Paste:

```nginx
# HTTP → HTTPS redirect
server {
    listen 80;
    server_name api.hellum.dev;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS — main API
server {
    listen 443 ssl http2;
    server_name api.hellum.dev;

    ssl_certificate     /etc/letsencrypt/live/api.hellum.dev/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.hellum.dev/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header X-Content-Type-Options    nosniff;
    add_header X-Frame-Options           DENY;
    add_header X-XSS-Protection          "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Upload limit for firmware .bin files (64 MB)
    client_max_body_size 64m;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }
}
```

### 12.2 Enable and Start Nginx

```bash
sudo ln -s /etc/nginx/sites-available/hellum-api /etc/nginx/sites-enabled/

# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Test config
sudo nginx -t

# Start and enable Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

---

## 13. Verify the Deployment

### 13.1 API Health Check

```bash
curl https://api.hellum.dev/health
# Expected: {"status": "ok"}
```

### 13.2 OpenAPI Docs

Open in browser: `https://api.hellum.dev/docs`

You should see all endpoint groups:
- `consumer` — `/api/v1/auth/google`, `/api/v1/me`, `/api/v1/devices/*`
- `oauth` — `/oauth/authorize`, `/oauth/token`
- `smart_home` — `/smarthome/fulfillment`
- `admin_smarthome` — `/admin/smarthome-devices`
- `admin_device_models` — `/admin/device-models`
- `admin_rbac` — `/admin/roles`
- `admin` — OTA firmware management

### 13.3 Test MQTT Broker TLS

From your **local machine** (not the server):

```bash
mosquitto_pub \
  -h api.hellum.dev \
  -p 8883 \
  --cafile /etc/ssl/certs/ca-certificates.crt \
  -t "test/ping" \
  -m "hello" \
  -u "unknown_user" \
  -P "wrong_password" \
  -v
```

**Expected last line:**
```
Error: Connection Refused: not authorised.
```

This confirms the TLS handshake succeeded and the broker is running correctly.
A **TLS/SSL error** instead means the certificate setup needs attention.

---

## 14. Bootstrap: First Admin Login & Device Model Registration

Admin authentication is exclusively via Google Sign-In. Get your Google ID token
using the `gcloud` CLI (or any OAuth flow that returns an ID token for your
`SUPER_ADMIN_EMAIL` account):

```bash
# Install gcloud CLI if needed: https://cloud.google.com/sdk/docs/install
gcloud auth login
gcloud auth print-identity-token

export GOOGLE_TOKEN="<paste token here>"
```

### 14.1 Verify Admin Access

```bash
curl -X GET https://api.hellum.dev/admin/device-models \
  -H "Authorization: Bearer $GOOGLE_TOKEN"
# Expected: []   (empty — no models registered yet)
```

### 14.2 Register the First Device Model

Register your hardware model. Repeat for each device type your platform supports.

```bash
curl -X POST https://api.hellum.dev/admin/device-models \
  -H "Authorization: Bearer $GOOGLE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "4-switch-board",
    "display_name": "4-Switch Smart Board",
    "manufacturer": "Hellum",
    "hw_version": "1.0",
    "endpoints": [
      {"id": "light1", "name": "Light 1", "google_type": "action.devices.types.LIGHT"},
      {"id": "light2", "name": "Light 2", "google_type": "action.devices.types.LIGHT"},
      {"id": "fan",    "name": "Fan",     "google_type": "action.devices.types.FAN"},
      {"id": "plug",   "name": "Plug",    "google_type": "action.devices.types.OUTLET"}
    ]
  }'
```

Expected response includes `"model_id": "4-switch-board"` with the full endpoint list.

### 14.3 Grant Admin to a Team Member

```bash
curl -X POST https://api.hellum.dev/admin/roles \
  -H "Authorization: Bearer $GOOGLE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "teammate@hellum.dev"}'
```

---

## 15. Provision the First ESP32 Device

### 15.1 Add MQTT Credentials for the Device

Each physical device gets a unique MQTT username (`esp32_<mac>`) and a strong password.
This password is flashed into the ESP32's NVS partition.

```bash
# Set your device's MAC address (12-char lowercase hex, no colons)
MAC="aabbccddeeff"

# Generate a strong password and save it somewhere secure
PASSWORD="$(openssl rand -base64 24)"
echo "Device MQTT Password for $MAC: $PASSWORD"
# --> SAVE THIS PASSWORD, it goes into the ESP32 firmware NVS

# Add the credentials to Mosquitto's password file
docker exec hellum_mosquitto \
  mosquitto_passwd -b /mosquitto/config/passwd "esp32_${MAC}" "$PASSWORD"

# Signal Mosquitto to reload passwords without restarting
docker exec hellum_mosquitto kill -HUP 1
```

**Repeat this for every ESP32 device you manufacture.**

### 15.2 Test the Device Credentials

```bash
mosquitto_pub \
  -h api.hellum.dev \
  -p 8883 \
  --cafile /etc/ssl/certs/ca-certificates.crt \
  -t "smarthome/device/${MAC}/state" \
  -m '{"device":"light1","state":"on"}' \
  -u "esp32_${MAC}" \
  -P "$PASSWORD" \
  -v

# Expected final line:
# Client esp32_aabbccddeeff sent PUBLISH (d0, q0, r0, m1, 'smarthome/device/.../state', ... (26 bytes))
```

Check API logs:
```bash
docker compose logs api | grep "mqtt_state"
# You'll see: mqtt_state_unmatched (device not provisioned yet — this is expected)
```

### 15.3 Run the Full MQTT Binding Token Provisioning Flow

**Step A — Consumer authenticates and gets a binding token:**

```bash
# --- Consumer authenticates via Google (from your mobile/web app) ---
# For testing, get a Google ID token via gcloud:
gcloud auth print-identity-token

CONSUMER_GOOGLE_TOKEN="<google-id-token>"

# Exchange for a Hellum JWT:
RESPONSE=$(curl -s -X POST https://api.hellum.dev/api/v1/auth/google \
  -H "Content-Type: application/json" \
  -d "{\"id_token\": \"$CONSUMER_GOOGLE_TOKEN\"}")

echo $RESPONSE | python3 -m json.tool
CONSUMER_JWT=$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Request a binding token:
BINDING_RESPONSE=$(curl -s -X POST https://api.hellum.dev/api/v1/devices/binding-token \
  -H "Authorization: Bearer $CONSUMER_JWT")

echo $BINDING_RESPONSE | python3 -m json.tool
BINDING_TOKEN=$(echo $BINDING_RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin)['binding_token'])")

echo "Binding Token: $BINDING_TOKEN"
# This token is passed to the ESP32 via BLE in the real flow.
```

**Step B — Simulate the ESP32 publishing its registration message:**

```bash
# This is what the ESP32 firmware publishes after connecting to WiFi
mosquitto_pub \
  -h api.hellum.dev \
  -p 8883 \
  --cafile /etc/ssl/certs/ca-certificates.crt \
  -t "smarthome/register" \
  -m "{\"mac\":\"${MAC}\",\"binding_token\":\"${BINDING_TOKEN}\",\"device_model\":\"4-switch-board\"}" \
  -u "esp32_${MAC}" \
  -P "$PASSWORD"

# Watch API logs for the success event:
docker compose logs api | grep -E "mqtt_device_provisioned|mqtt_registration"
# Expected: INFO mqtt_device_provisioned mac=aabbccddeeff model=4-switch-board user_id=...
```

**Step C — Verify the device is in the consumer's account:**

```bash
curl https://api.hellum.dev/api/v1/devices \
  -H "Authorization: Bearer $CONSUMER_JWT" | python3 -m json.tool

# Expected: array with one device, 4 endpoints all state=false
```

**Step D — Test a state update (simulate ESP32 reporting):**

```bash
mosquitto_pub \
  -h api.hellum.dev \
  -p 8883 \
  --cafile /etc/ssl/certs/ca-certificates.crt \
  -t "smarthome/device/${MAC}/state" \
  -m '{"device":"light1","state":"on"}' \
  -u "esp32_${MAC}" \
  -P "$PASSWORD"

# Check state was persisted:
docker compose logs api | grep "mqtt_state_persisted"
# Expected: INFO mqtt_state_persisted mac=aabbccddeeff endpoint=light1 state=True
```

---

## 16. Google Home Actions Console Setup

### 16.1 Create a Smart Home Action

1. Go to [console.actions.google.com](https://console.actions.google.com)
2. Click **New Project** → select the existing `Hellum IoT` Google Cloud project
3. Choose **Smart Home** → **Start Building**

### 16.2 Configure Fulfillment

1. In the left sidebar → **Develop → Actions**
2. Click **Add Action**
3. **Fulfillment URL:** `https://api.hellum.dev/smarthome/fulfillment`
4. Click **Done** → **Save**

### 16.3 Configure Account Linking (OAuth)

1. In the left sidebar → **Develop → Account Linking**
2. Fill in the following:

| Field | Value |
|---|---|
| **Linking type** | OAuth + Google Sign-In (Streamlined) |
| **Grant type** | Authorization code |
| **Client ID** | Value of `OAUTH_CLIENT_ID` from `.env` (e.g., `hellum-google-home`) |
| **Client secret** | Value of `OAUTH_CLIENT_SECRET` from `.env` |
| **Authorization URL** | `https://api.hellum.dev/oauth/authorize` |
| **Token URL** | `https://api.hellum.dev/oauth/token` |

3. Click **Save**

### 16.4 Get Your Project ID and Update OAUTH_REDIRECT_URIS

The redirect URI that Google uses after OAuth is based on your Actions project ID.
Find it in the Actions Console URL bar:
```
https://console.actions.google.com/project/YOUR_PROJECT_ID/overview
```

Update `.env` on the server:
```bash
nano /home/hellum/hellum-backend/.env
# Set: OAUTH_REDIRECT_URIS=https://oauth-redirect.googleusercontent.com/r/YOUR_PROJECT_ID

# Restart the API to pick up the change:
docker compose up -d api
```

### 16.5 Test in the Google Home App

1. Open **Google Home** app (Android or iOS)
2. Tap **+** → **Set up device** → **Works with Google**
3. Search for your action name → tap it
4. Sign in with the same Google account you used as a consumer in Step 15
5. Google uses Streamlined Account Linking — your Google ID token is verified server-side
6. After linking, tap **Done** — your Smart Board's endpoints should appear as devices in the Google Home app

---

## 17. Certificate Auto-Renewal

Let's Encrypt certificates expire every 90 days. Certbot installs a systemd timer that runs twice daily, but Mosquitto and Nginx need to reload the new cert files.

### 17.1 Create a Post-Renewal Hook

```bash
sudo mkdir -p /etc/letsencrypt/renewal-hooks/post

sudo tee /etc/letsencrypt/renewal-hooks/post/reload-services.sh << 'EOF'
#!/bin/bash
set -e

# Reload Nginx TLS configuration (zero-downtime)
systemctl reload nginx

# Restart the Mosquitto Docker container to pick up new cert files
cd /home/hellum/hellum-backend
docker compose restart mosquitto

echo "[$(date)] TLS services reloaded after certificate renewal" \
  >> /var/log/letsencrypt/service-reload.log
EOF

sudo chmod +x /etc/letsencrypt/renewal-hooks/post/reload-services.sh
```

### 17.2 Verify Auto-Renewal Works

```bash
# Check the certbot systemd timer is active
sudo systemctl status certbot.timer

# Dry-run to confirm end-to-end renewal succeeds
sudo certbot renew --dry-run
# Expected last line: "Congratulations, all simulated renewals succeeded"
```

---

## 18. Log Monitoring & Maintenance

### 18.1 Useful Log Commands

```bash
# All services live
docker compose logs -f

# API logs with timestamps
docker compose logs -f --timestamps api

# Errors only
docker compose logs api 2>&1 | grep -E "ERROR|WARNING|CRITICAL"

# Mosquitto connection events
docker compose logs mosquitto | grep -E "New client|Client .* disconnected|Socket error"
```

### 18.2 Key Log Patterns

| Pattern | Meaning | Action Required |
|---|---|---|
| `mqtt_bridge_connected` | MQTT bridge healthy | None |
| `mqtt_bridge_disconnected retry_in=Xs` | Broker unavailable | Check `docker compose ps` |
| `mqtt_state_persisted mac=... endpoint=...` | ESP32 reporting state | None |
| `mqtt_state_unmatched mac=...` | State for unknown endpoint | Device not provisioned yet |
| `mqtt_device_provisioned mac=...` | New device claimed via binding token | None |
| `mqtt_registration_invalid_token` | Bad/expired binding token | User should request a new token |
| `mqtt_registration_unknown_model` | Unknown device_model slug in ESP32 payload | Register model via `/admin/device-models` |
| `admin_auth_super_admin email=...` | Super Admin authenticated | None |
| `admin_auth_ok email=... role=admin` | Regular admin authenticated | None |
| `admin_auth_rejected email=...` | Unauthorized access attempt | Investigate |
| `consumer_google_sign_in user_id=...` | Consumer login success | None |

### 18.3 Rolling Code Deployments (Zero MQTT Downtime)

```bash
cd /home/hellum/hellum-backend

# Pull latest code
git pull

# Rebuild and restart API only (Mosquitto stays up — no ESP32 disconnections)
docker compose build api
docker compose up -d api

# Confirm healthy
docker compose ps
docker compose logs api --tail=30
```

### 18.4 MongoDB Backup

```bash
# One-time backup (for local MongoDB)
mongodump \
  --uri="mongodb://localhost:27017/hellum_iot" \
  --archive="/home/hellum/backups/hellum_iot_$(date +%Y%m%d_%H%M%S).gz" \
  --gzip

# Set up daily automated backup (runs at 02:00)
mkdir -p /home/hellum/backups
crontab -e
# Add this line:
# 0 2 * * * mongodump --uri="mongodb://localhost:27017/hellum_iot" --archive="/home/hellum/backups/hellum_$(date +\%Y\%m\%d).gz" --gzip
```

---

## 19. Security Hardening Checklist

Run through this list before going live:

**Network**
- [ ] UFW active — only ports 22, 80, 443, 8883 are open
- [ ] Port 1883 is NOT reachable from the internet — verify: `sudo ufw status | grep 1883` (no result)
- [ ] SSH password authentication disabled — `PasswordAuthentication no` in `/etc/ssh/sshd_config`

**Files**
- [ ] `.env` permissions: `chmod 600 .env`
- [ ] `mosquitto/passwd` permissions: `chmod 600 mosquitto/passwd`
- [ ] `.env` is in `.gitignore` — run `git status` to verify it is untracked

**Secrets**
- [ ] All secrets are at least 32 random bytes (use `openssl rand -hex 32`)
- [ ] No placeholder values remain in `.env` — grep: `grep "change-me\|FILL_IN" .env`

**Auth**
- [ ] `SUPER_ADMIN_EMAIL` is set to a real Google account you control
- [ ] `GOOGLE_CLIENT_ID` is set — test: `curl /api/v1/auth/google` returns a proper error, not 503
- [ ] MongoDB authentication enabled (if self-hosted) — create a dedicated DB user

**TLS**
- [ ] `openssl s_client -connect api.hellum.dev:8883` shows `Verify return code: 0 (ok)`
- [ ] `openssl s_client -connect api.hellum.dev:443` shows `Verify return code: 0 (ok)`
- [ ] Certbot renewal dry-run passes: `sudo certbot renew --dry-run`

**Google**
- [ ] OAuth consent screen published (or test users added for pre-launch)
- [ ] Smart Home Action published (or in test mode for internal use)

**Ongoing**
- [ ] Consider enabling `acl_file` in Mosquitto for per-device topic isolation

---

## 20. Troubleshooting Reference

### API Container Won't Start

```bash
docker compose logs api | tail -50
```

| Error Message | Cause | Fix |
|---|---|---|
| `database unavailable` | MongoDB unreachable | Check `MONGO_URI`; add `extra_hosts` if using `host.docker.internal` |
| `mqtt_bridge_disconnected` on startup | Mosquitto not ready | Check `docker compose logs mosquitto`; usually self-resolves in seconds |
| `ModuleNotFoundError: google.auth` | Dependency missing in image | Run `docker compose build --no-cache api` |
| `ValidationError` on startup | `.env` missing required field | Compare `.env` against `.env.example` |
| `google_sso_not_configured` from API | `GOOGLE_CLIENT_ID` not set | Set it in `.env` and restart |

### Mosquitto Won't Start

```bash
docker compose logs mosquitto | tail -20
```

| Error | Fix |
|---|---|
| `Unable to load server cert` | Cert path in `mosquitto.conf` is wrong, or file permissions too restrictive — run the `chmod` commands from Step 5.3 |
| `Error: Unable to open pwfile` | `mosquitto/passwd` doesn't exist — run `touch mosquitto/passwd` |
| `Address already in use :8883` | Another process holds the port — `sudo lsof -i :8883` to identify it |

### ESP32 TLS Connection Fails

Test the cert from your local machine:
```bash
openssl s_client -connect api.hellum.dev:8883 -servername api.hellum.dev < /dev/null
```

| Symptom | Likely Cause | Fix |
|---|---|---|
| `SSL handshake failure` | Cert CN mismatch or expired | `sudo certbot certificates` — check expiry and domain |
| `Connection Refused` | Mosquitto down or port blocked | `docker compose ps`; `sudo ufw status` |
| `Connection Refused: not authorised` | Wrong MQTT username/password | Re-add with `mosquitto_passwd`; signal reload with `kill -HUP 1` |

### Admin Returns 403

1. Decode your Bearer token at [jwt.io](https://jwt.io) and verify:
   - `email` matches `SUPER_ADMIN_EMAIL` in `.env` OR exists in `admin_users` MongoDB collection
   - `email_verified` is `true`
   - `aud` contains your `GOOGLE_CLIENT_ID`
   - `exp` timestamp has not passed

2. Check logs: `docker compose logs api | grep "admin_auth"`

### Google Home SYNC Returns Empty Device List

1. Verify consumer JWT works: `GET /api/v1/me` returns the user profile
2. Verify devices exist: `GET /api/v1/devices` returns the device array
3. If the device list is empty, provisioning failed — check:
   ```bash
   docker compose logs api | grep -E "mqtt_registration|mqtt_device_provisioned"
   ```
4. Common causes: binding token expired (re-request), unknown `device_model` slug (register the model first)

---

*Deployment Guide v2.0.0 — matches IoT Core Backend refactor 2026-06-24*
