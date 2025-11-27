# Deployment Guide - Nginx Setup

This guide explains how to deploy the Hybrid RAG application using Nginx.

## Architecture

```
                    ┌─────────────┐
                    │   Client    │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Nginx     │
                    │  (Port 80)  │
                    └──────┬──────┘
                           │
            ┌──────────────┴──────────────┐
            │                             │
            ▼                             ▼
    ┌───────────────┐           ┌─────────────────┐
    │ Static Files  │           │ FastAPI Backend │
    │ (React Build) │           │   (Port 8000)   │
    └───────────────┘           └─────────────────┘
```

## Quick Start (macOS)

### Prerequisites

1. **Install Nginx**
   ```bash
   brew install nginx
   ```

2. **Install Node.js** (for building frontend)
   ```bash
   brew install node
   ```

3. **Install Python 3.8+**
   ```bash
   brew install python@3.11
   ```

### Deployment Steps

1. **Run the deployment script**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

2. **Start the backend** (in a terminal)
   ```bash
   source venv/bin/activate
   uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```

3. **Start Nginx** (in another terminal)
   ```bash
   # For local testing (port 8080)
   sudo nginx -c /Users/johangeorge/rag/nginx/nginx.local.conf
   ```

4. **Access the application**
   - Frontend: http://localhost:8080
   - API Docs: http://localhost:8080/docs

### Stopping Services

```bash
# Stop Nginx
sudo nginx -s stop

# Stop backend: Ctrl+C in the terminal running uvicorn
```

---

## Production Deployment (Linux)

### Prerequisites

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx python3-pip python3-venv nodejs npm

# CentOS/RHEL
sudo yum install nginx python3-pip nodejs npm
```

### Step 1: Clone and Setup

```bash
cd /var/www
git clone <your-repo-url> rag
cd rag
chmod +x deploy.sh start_prod.sh
./deploy.sh
```

### Step 2: Configure Nginx

```bash
# Copy the Nginx configuration
sudo cp nginx/nginx.conf /etc/nginx/nginx.conf

# Update the root path in nginx.conf if needed
sudo nano /etc/nginx/nginx.conf
# Change: root /var/www/rag/frontend/dist;

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### Step 3: Setup Systemd Service for Backend

Create `/etc/systemd/system/rag-backend.service`:

```ini
[Unit]
Description=RAG FastAPI Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/rag
ExecStart=/var/www/rag/start_prod.sh
Restart=always
RestartSec=3
Environment=WORKERS=4

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl start rag-backend
sudo systemctl enable rag-backend
sudo systemctl status rag-backend
```

### Step 4: Configure Firewall

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 'Nginx Full'
sudo ufw allow 22
sudo ufw enable

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

---

## SSL/HTTPS Setup (Production)

### Using Let's Encrypt (Certbot)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is set up automatically
sudo certbot renew --dry-run
```

### Updated Nginx Config with SSL

Replace the server block in `/etc/nginx/nginx.conf`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_protocols TLSv1.2 TLSv1.3;

    root /var/www/rag/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        rewrite ^/api/(.*)$ /$1 break;
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location ~ ^/(docs|redoc|openapi.json|health|stats) {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## API Endpoints After Deployment

With the Nginx proxy setup, API calls should use the `/api/` prefix:

| Development | Production (via Nginx) |
|-------------|------------------------|
| `http://localhost:8000/search` | `http://yourdomain.com/api/search` |
| `http://localhost:8000/add_document` | `http://yourdomain.com/api/add_document` |
| `http://localhost:8000/hybrid` | `http://yourdomain.com/api/hybrid` |

Direct access to docs is still available:
- `http://yourdomain.com/docs` - Swagger UI
- `http://yourdomain.com/redoc` - ReDoc
- `http://yourdomain.com/health` - Health check

---

## Troubleshooting

### Check Nginx Status
```bash
sudo systemctl status nginx
sudo nginx -t  # Test configuration
```

### Check Backend Status
```bash
sudo systemctl status rag-backend
journalctl -u rag-backend -f  # View logs
```

### Check Nginx Logs
```bash
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### Common Issues

1. **502 Bad Gateway**: Backend not running
   ```bash
   sudo systemctl restart rag-backend
   ```

2. **Permission denied**: Fix file permissions
   ```bash
   sudo chown -R www-data:www-data /var/www/rag
   ```

3. **Frontend not updating**: Rebuild and clear cache
   ```bash
   cd frontend && npm run build
   sudo nginx -s reload
   ```

---

## Updating the Application

```bash
cd /var/www/rag

# Pull latest changes
git pull

# Rebuild frontend
cd frontend && npm install && npm run build && cd ..

# Update backend dependencies
source venv/bin/activate
pip install -r requirements.txt

# Restart services
sudo systemctl restart rag-backend
sudo nginx -s reload
```
