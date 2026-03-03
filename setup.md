# Movie Mania Agent — Complete AWS EC2 Deployment Guide

> Stack: Ubuntu 24.04 · Docker · Nginx · DuckDNS · GitHub Actions CI/CD · Groq LLM · TMDB API

---

## PHASE 1: Launch EC2 Instance on AWS Console

### Step 1 — Sign in & Navigate

1. Go to [https://console.aws.amazon.com](https://console.aws.amazon.com)
2. Top-right: select your preferred **Region** (e.g., `us-east-1`)
3. Search bar → type **EC2** → click **EC2**

---

### Step 2 — Launch Instance

1. Click **"Launch instances"** (orange button)
2. Fill in:

| Field | Value |
|---|---|
| Name | `movie-mania-agent` |
| AMI | **Ubuntu Server 24.04 LTS (HVM), SSD** — 64-bit x86 |
| Instance type | `t3.micro` |

---

### Step 3 — Key Pair (SSH .pem)

1. Click **"Create new key pair"**
2. Name: `movie-mania-key`
3. Key pair type: **RSA**
4. Private key file format: **.pem**
5. Click **"Create key pair"** — it auto-downloads `movie-mania-key.pem`
6. **Save this file somewhere safe** — you cannot download it again

---

### Step 4 — Network Settings

1. Click **"Edit"** next to Network settings
2. VPC: **select your default VPC** (the one labeled `default`)
3. Subnet: **No preference** (or pick any public subnet)
4. Auto-assign public IP: **Enable**
5. Firewall — **Create security group**, name it `movie-mania-sg`
6. Add these inbound rules:

| Type | Protocol | Port | Source |
|---|---|---|---|
| SSH | TCP | 22 | My IP (recommended for safety) |
| HTTP | TCP | 80 | 0.0.0.0/0 |
| HTTPS | TCP | 443 | 0.0.0.0/0 |
| Custom TCP | TCP | 8000 | 0.0.0.0/0 (optional, for direct API testing) |

---

### Step 5 — Storage

1. Root volume: **8 GiB**
2. Volume type: **gp3**
3. Leave everything else default

---

### Step 6 — Launch

1. Click **"Launch instance"**
2. Wait ~1 minute for state to show **"Running"**

---

## PHASE 2: Assign Elastic IP

1. In EC2 left sidebar → **Network & Security** → **Elastic IPs**
2. Click **"Allocate Elastic IP address"**
3. Network border group: keep default → Click **"Allocate"**
4. Select the new Elastic IP → click **Actions** → **"Associate Elastic IP address"**
5. Resource type: **Instance**
6. Instance: select `movie-mania-agent`
7. Click **"Associate"**
8. **Copy this Elastic IP** — you will use it everywhere (DNS, SSH, CI/CD secrets)

---

## PHASE 3: SSH from Windows using .pem Key

### Step 1 — Fix .pem File Permissions (Required on Windows)

> **Important:** `icacls /inheritance:r` alone is NOT enough. It only blocks future inheritance but does not remove permissions already stamped on the file. You must explicitly remove broad groups like `NT AUTHORITY\Authenticated Users` — SSH will refuse any key file accessible by such groups.

Open **PowerShell** (no need for Administrator):

```powershell
$pemFile = "D:\Your\Path\To\movie-mania-key.pem"

# Step 1: Block inheritance from parent folder
icacls $pemFile /inheritance:r

# Step 2: Explicitly remove all broad group permissions
icacls $pemFile /remove "NT AUTHORITY\Authenticated Users"
icacls $pemFile /remove "BUILTIN\Users"
icacls $pemFile /remove "Everyone"

# Step 3: Grant read access to your user only
icacls $pemFile /grant:r "$($env:USERNAME):(R)"

# Step 4: Verify — output should show ONLY your username + SYSTEM + Administrators
icacls $pemFile
```

Expected output:
```
your-pc\your-username:(R)
BUILTIN\Administrators:(F)
NT AUTHORITY\SYSTEM:(F)
```

`Administrators` and `SYSTEM` entries are acceptable to SSH — only broad user groups like `Authenticated Users` cause the "bad permissions" error.

### Step 2 — Connect via SSH

```powershell
ssh -i "D:\Your\Path\To\movie-mania-key.pem" ubuntu@YOUR_ELASTIC_IP
```

- Default username for Ubuntu AMI is always `ubuntu`
- Type `yes` when asked to confirm the fingerprint
- You are now inside your EC2 instance

---

## PHASE 4: Initial Server Setup

Run these commands **inside the EC2 instance**:

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essentials
sudo apt install -y curl git ufw nginx

# Install Docker (official script)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt install -y docker-compose-plugin

# Apply docker group without re-login
newgrp docker

# Verify installations
docker --version
docker compose version
```

---

## PHASE 5: Setup DuckDNS Subdomain

### Step 1 — Get a DuckDNS Domain

1. Go to [https://www.duckdns.org](https://www.duckdns.org)
2. Sign in with GitHub or Google
3. Create a subdomain e.g., `movie-mania`
4. Set its IP to your **Elastic IP**
5. Click **"update ip"**
6. Copy your **token** from the top of the page

Your domain will be: `movie-mania.duckdns.org`

### Step 2 — Auto-Renew DuckDNS on Server

```bash
mkdir -p ~/duckdns
nano ~/duckdns/duck.sh
```

Paste (replace `YOUR_SUBDOMAIN` and `YOUR_TOKEN`):

```bash
#!/bin/bash
echo url="https://www.duckdns.org/update?domains=YOUR_SUBDOMAIN&token=YOUR_TOKEN&ip=" | curl -k -o ~/duckdns/duck.log -K -
```

```bash
chmod +x ~/duckdns/duck.sh

# Add cron job to run every 5 minutes
crontab -e
```

Add this line at the bottom of crontab:

```
*/5 * * * * ~/duckdns/duck.sh >/dev/null 2>&1
```

---

## PHASE 6: Setup GitHub Private Repo with Deploy Key

### Step 1 — Generate SSH Deploy Key on EC2

```bash
ssh-keygen -t ed25519 -C "deploy-key-movie-mania" -f ~/.ssh/deploy_key -N ""
cat ~/.ssh/deploy_key.pub
```

Copy the full output (starts with `ssh-ed25519 ...`)

### Step 2 — Add Deploy Key to GitHub

1. Go to your private repo on GitHub
2. **Settings** → **Deploy keys** → **"Add deploy key"**
3. Title: `EC2 Movie Mania Deploy Key`
4. Key: paste the public key you copied
5. **Allow write access**: leave unchecked (read-only is enough for deploy)
6. Click **"Add key"**

### Step 3 — Configure SSH on EC2 to Use Deploy Key

```bash
nano ~/.ssh/config
```

Add:

```
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/deploy_key
    StrictHostKeyChecking no
```

```bash
chmod 600 ~/.ssh/config

# Test the connection
ssh -T git@github.com
# Expected output: Hi username/repo! You've successfully authenticated...
```

### Step 4 — Clone Your Private Repo

```bash
cd /home/ubuntu
git clone git@github.com:YOUR_USERNAME/Movie-Mania-Agent.git
cd Movie-Mania-Agent
```

### Step 5 — Create .env File on Server

```bash
nano .env
```

Paste and fill in your actual keys:

```env
tmdb_api_key=your_tmdb_api_key_here
groq_api_key=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
ALLOWED_ORIGINS=https://movie-mania.duckdns.org
REDIS_URL=redis://redis:6379
```

```bash
chmod 600 .env
```

---

## PHASE 7: Setup Nginx Reverse Proxy

### Step 1 — Create Nginx Config

```bash
sudo nano /etc/nginx/sites-available/movie-mania
```

Paste (replace `movie-mania.duckdns.org` with your actual subdomain):

```nginx
server {
    listen 80;
    server_name movie-mania.duckdns.org;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/movie-mania /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test Nginx config
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
sudo systemctl enable nginx
```

### Step 2 — Enable HTTPS with Let's Encrypt (Certbot)

```bash
sudo apt install -y certbot python3-certbot-nginx

sudo certbot --nginx -d movie-mania.duckdns.org
```

Follow the prompts:
- Enter your email address
- Agree to terms: press `A`
- Choose **2** — Redirect HTTP to HTTPS (recommended)

Certbot auto-configures Nginx and schedules auto-renewal. Verify renewal works:

```bash
sudo certbot renew --dry-run
```

---

## PHASE 8: Configure UFW Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable

# Verify rules
sudo ufw status
```

Expected output:
```
Status: active
To                         Action      From
--                         ------      ----
OpenSSH                    ALLOW       Anywhere
Nginx Full                 ALLOW       Anywhere
```

---

## PHASE 9: CI/CD with GitHub Actions

### Step 1 — Add GitHub Secrets

Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these secrets one by one:

| Secret Name | Value |
|---|---|
| `EC2_HOST` | Your Elastic IP address |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | Full contents of `movie-mania-key.pem` |
| `TMDB_API_KEY` | Your TMDB API key |
| `GROQ_API_KEY` | Your Groq API key |

To get the .pem content on Windows (run in PowerShell):

```powershell
Get-Content "C:\Users\YourName\Downloads\movie-mania-key.pem"
```

Copy everything including `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----`

### Step 2 — Create GitHub Actions Workflow

Create the file `.github/workflows/deploy.yml` in your repo:

```yaml
name: Deploy to EC2

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Deploy to EC2 via SSH
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ${{ secrets.EC2_USER }}
          key: ${{ secrets.EC2_SSH_KEY }}
          timeout: 120s
          script: |
            cd /home/ubuntu/Movie-Mania-Agent

            # Pull latest code from main
            git pull origin main

            # Rebuild and restart Docker containers
            docker compose down
            docker compose build --no-cache
            docker compose up -d

            # Wait for containers to initialize
            sleep 10

            # Show running containers
            docker compose ps

            # Health check
            curl -f http://localhost:8000/health && echo "✅ Deploy successful!" || echo "❌ Health check failed"
```

Commit and push this file to your repo:

```powershell
git add .github/workflows/deploy.yml
git commit -m "Add CI/CD GitHub Actions workflow"
git push origin main
```

Every push to `main` will now automatically deploy to EC2.

---

## PHASE 10: First Manual Deploy & Verification

### On EC2 — Start Containers for the First Time

```bash
cd /home/ubuntu/Movie-Mania-Agent

# Build and start all services
docker compose up -d --build

# Check container status
docker compose ps

# Tail logs to confirm startup
docker compose logs -f movie-api
```

### Verify All Layers

```bash
# 1. Direct FastAPI health check (bypasses Nginx)
curl http://localhost:8000/health

# 2. Through Nginx on HTTP
curl http://movie-mania.duckdns.org/health

# 3. Through Nginx on HTTPS (final production check)
curl https://movie-mania.duckdns.org/health
```

All three should return:
```json
{"status": "healthy", "timestamp": "...", "version": "1.0.0", ...}
```

### Test the Chat Endpoint

```bash
curl -X POST "https://movie-mania.duckdns.org/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the trending movies today?"}'
```

---

## Troubleshooting

### Docker containers not starting
```bash
docker compose logs movie-api
docker compose logs redis
```

### Nginx 502 Bad Gateway
```bash
# Check if FastAPI is running
docker compose ps
curl http://localhost:8000/health

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### SSH connection refused
- Verify EC2 instance is in **Running** state
- Verify Security Group has port 22 open for your IP
- Verify you are using the correct Elastic IP

### Certbot SSL fails
- Confirm DuckDNS domain resolves to your Elastic IP: `nslookup movie-mania.duckdns.org`
- Ensure port 80 is open in Security Group before running certbot

### GitHub Actions deploy fails
- Check the `EC2_SSH_KEY` secret includes the full key with header/footer lines
- Confirm the repo was cloned to `/home/ubuntu/Movie-Mania-Agent` on EC2
- Check the deploy key has access to the private repo

---

## Summary Checklist

| # | Task | Done |
|---|---|---|
| 1 | EC2 t3.micro Ubuntu 24.04 launched | ☐ |
| 2 | Security group configured (22, 80, 443) | ☐ |
| 3 | Elastic IP allocated and associated | ☐ |
| 4 | SSH working from Windows with .pem | ☐ |
| 5 | Docker + Docker Compose installed on EC2 | ☐ |
| 6 | DuckDNS subdomain pointing to Elastic IP | ☐ |
| 7 | DuckDNS auto-update cron job active | ☐ |
| 8 | Deploy key generated and added to GitHub | ☐ |
| 9 | SSH config set to use deploy key | ☐ |
| 10 | Private repo cloned on EC2 | ☐ |
| 11 | `.env` file created on EC2 with API keys | ☐ |
| 12 | Nginx configured and running | ☐ |
| 13 | HTTPS enabled via Certbot | ☐ |
| 14 | UFW firewall enabled | ☐ |
| 15 | GitHub Actions secrets added | ☐ |
| 16 | `.github/workflows/deploy.yml` committed | ☐ |
| 17 | First `docker compose up` successful | ☐ |
| 18 | Health endpoint returning 200 HTTPS | ☐ |
| 19 | CI/CD push-to-deploy tested and working | ☐ |

---

> **After setup**: every `git push` to `main` automatically SSHs into EC2, pulls latest code, rebuilds Docker, and redeploys — zero manual steps required.
