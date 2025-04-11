#!/bin/bash

# Script to configure Nginx with SSL for matching.aigenconsult.com
set -e

echo "=== Configuring Nginx with SSL for matching.aigenconsult.com ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script as root or with sudo"
  exit 1
fi

# Step 1: Install Nginx if not already installed
echo "=== Step 1: Installing Nginx if not already installed ==="
if ! command -v nginx &> /dev/null; then
    echo "Nginx not found. Installing..."
    apt-get update
    apt-get install -y nginx
else
    echo "Nginx is already installed"
fi

# Step 2: Install certbot if not already installed
echo "=== Step 2: Installing certbot if not already installed ==="
if ! command -v certbot &> /dev/null; then
    echo "Certbot not found. Installing certbot and Nginx plugin..."
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
else
    echo "Certbot is already installed"
fi

# Step 3: Set up Nginx configuration
echo "=== Step 3: Setting up Nginx configuration ==="
NGINX_CONF_DIR="/etc/nginx/sites-available"
NGINX_ENABLED_DIR="/etc/nginx/sites-enabled"
DOMAIN="matching.aigenconsult.com"

# Create directory for certbot verification
mkdir -p /var/www/certbot

# Create Nginx configuration
cat > "$NGINX_CONF_DIR/$DOMAIN" << EOF
# Nginx configuration for matching.aigenconsult.com

# HTTP server block - redirects to HTTPS
server {
    listen 80;
    server_name matching.aigenconsult.com;

    # Redirect all HTTP requests to HTTPS
    location / {
        return 301 https://\$host\$request_uri;
    }

    # For Let's Encrypt certbot verification
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
}

# HTTPS server block
server {
    listen 443 ssl;
    server_name matching.aigenconsult.com;

    # SSL certificate configuration
    ssl_certificate /etc/letsencrypt/live/matching.aigenconsult.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/matching.aigenconsult.com/privkey.pem;
    
    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # HSTS (optional, but recommended)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Proxy settings
    location / {
        proxy_pass http://localhost:8002;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF

# Enable the site
ln -sf "$NGINX_CONF_DIR/$DOMAIN" "$NGINX_ENABLED_DIR/$DOMAIN"

# Remove default site if it exists
if [ -f "$NGINX_ENABLED_DIR/default" ]; then
    rm -f "$NGINX_ENABLED_DIR/default"
fi

# Test Nginx configuration
nginx -t

# Step 4: Obtain SSL certificates using certbot
echo "=== Step 4: Obtaining SSL certificates using certbot ==="
echo "NOTE: The domain matching.aigenconsult.com points to IP address 37.27.65.57"
echo "      Make sure port 80 is open for the domain verification process."
echo ""
read -p "Press Enter to continue with SSL certificate setup or Ctrl+C to cancel..."

# Stop Nginx temporarily to allow certbot to bind to port 80
systemctl stop nginx

# Obtain SSL certificate
certbot certonly --standalone \
  --preferred-challenges http \
  --agree-tos \
  --email admin@aigenconsult.com \
  --domain matching.aigenconsult.com

# Start Nginx
systemctl start nginx

# Step 5: Restart Nginx to apply the changes
echo "=== Step 5: Restarting Nginx to apply the changes ==="
systemctl restart nginx

echo "=== Nginx configuration completed successfully ==="
echo "The matching service is now accessible at https://matching.aigenconsult.com"
echo ""
echo "To check the status of Nginx:"
echo "  systemctl status nginx"
echo ""
echo "To view Nginx logs:"
echo "  tail -f /var/log/nginx/error.log"
echo ""
echo "SSL certificates will be automatically renewed by certbot"