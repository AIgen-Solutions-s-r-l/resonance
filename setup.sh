#!/bin/bash

# Setup script for matching service with Nginx and SSL
set -e

echo "=== Setting up Matching Service with Nginx and SSL ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script as root or with sudo"
  exit 1
fi

# Step 1: Build and run the Docker container
echo "=== Step 1: Building and running the Docker container ==="
cd "$(dirname "$0")"
# Use the original Dockerfile for production
docker build -t matching-service -f Dockerfile .
docker stop matching-service 2>/dev/null || true
docker rm matching-service 2>/dev/null || true
docker run -d --name matching-service --network host matching-service
echo "Docker container started on port 8002"

# Step 2: Install Nginx if not already installed
echo "=== Step 2: Installing Nginx if not already installed ==="
if ! command -v nginx &> /dev/null; then
    echo "Nginx not found. Installing..."
    apt-get update
    apt-get install -y nginx
else
    echo "Nginx is already installed"
fi

# Step 3: Install certbot if not already installed
echo "=== Step 3: Installing certbot if not already installed ==="
if ! command -v certbot &> /dev/null; then
    echo "Certbot not found. Installing certbot and Nginx plugin..."
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
else
    echo "Certbot is already installed"
fi

# Step 4: Set up Nginx configuration
echo "=== Step 4: Setting up Nginx configuration ==="
NGINX_CONF_DIR="/etc/nginx/sites-available"
NGINX_ENABLED_DIR="/etc/nginx/sites-enabled"
DOMAIN="matching.aigenconsult.com"

# Create directory for certbot verification
mkdir -p /var/www/certbot

# Copy the Nginx configuration
cp nginx-matching.conf "$NGINX_CONF_DIR/$DOMAIN"
ln -sf "$NGINX_CONF_DIR/$DOMAIN" "$NGINX_ENABLED_DIR/$DOMAIN"

# Remove default site if it exists
if [ -f "$NGINX_ENABLED_DIR/default" ]; then
    rm -f "$NGINX_ENABLED_DIR/default"
fi

# Test Nginx configuration
nginx -t

# Step 5: Obtain SSL certificates using certbot
echo "=== Step 5: Obtaining SSL certificates using certbot ==="
echo "NOTE: You will need to ensure that the domain matching.aigenconsult.com points to this server's IP address"
echo "      and that port 80 is open for the domain verification process."
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

# Step 6: Restart Nginx to apply the changes
echo "=== Step 6: Restarting Nginx to apply the changes ==="
systemctl restart nginx

echo "=== Setup completed successfully ==="
echo "The matching service is now running at https://matching.aigenconsult.com"
echo ""
echo "To check the status of the Docker container:"
echo "  docker ps -a | grep matching-service"
echo ""
echo "To view the logs of the Docker container:"
echo "  docker logs matching-service"
echo ""
echo "To stop the Docker container:"
echo "  docker stop matching-service"
echo ""
echo "To restart the Docker container:"
echo "  docker start matching-service"
echo ""
echo "SSL certificates will be automatically renewed by certbot"