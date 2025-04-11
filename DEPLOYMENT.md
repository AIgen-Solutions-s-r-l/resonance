# Deployment Guide for Matching Service

This guide explains how to deploy the Matching Service locally with Nginx and SSL using certbot. It also provides instructions for local development using Docker and docker-compose.

## Docker Configuration

This project uses two separate Dockerfiles:
- `Dockerfile` - Used for production deployment
- `Dockerfile.dev` - Used for local development

## Prerequisites

- Docker installed on your system
- A server with a public IP address
- Domain name (matching.aigenconsult.com) pointing to your server's IP address
- Ports 80 and 443 open on your firewall

## Automated Setup Options

### Option 1: Full Setup (Docker + Nginx + SSL)

We've provided a setup script that automates the deployment process:

1. Make the script executable (if not already):
   ```bash
   chmod +x setup.sh
   ```

2. Run the script as root or with sudo:
   ```bash
   sudo ./setup.sh
   ```

The script will:
- Build and run the Docker container on port 8002
- Install Nginx if not already installed
- Install certbot if not already installed
- Configure Nginx to route traffic from matching.aigenconsult.com to the local service
- Obtain SSL certificates using certbot
- Restart Nginx to apply the changes

### Option 2: Nginx Configuration Only

If you already have the Docker container running and just need to configure Nginx with SSL:

1. Make the script executable (if not already):
   ```bash
   chmod +x configure_nginx.sh
   ```

2. Run the script as root or with sudo:
   ```bash
   sudo ./configure_nginx.sh
   ```

The script will:
- Install Nginx if not already installed
- Install certbot if not already installed
- Configure Nginx to route traffic from matching.aigenconsult.com to the local service on port 8002
- Obtain SSL certificates using certbot
- Restart Nginx to apply the changes

## Manual Setup

If you prefer to set up everything manually, follow these steps:

### 1. Build and Run the Docker Container

```bash
# Build the Docker image for production
docker build -t matching-service -f Dockerfile .

# Run the container with host network mode to access host services
docker run -d --name matching-service --network host matching-service

# Run the container
docker run -d --name matching-service -p 8002:8002 matching-service
```

### 2. Verify the Docker Container

```bash
# Check if the container is running
docker ps | grep matching-service

# Check the logs
docker logs matching-service
```

### 3. Install Nginx

```bash
sudo apt-get update
sudo apt-get install -y nginx
```

### 4. Configure Nginx

Copy the provided Nginx configuration file:

```bash
sudo cp nginx-matching.conf /etc/nginx/sites-available/matching.aigenconsult.com
sudo ln -sf /etc/nginx/sites-available/matching.aigenconsult.com /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default  # Optional: remove default site
```

### 5. Install Certbot and Obtain SSL Certificates

```bash
# Install certbot and the Nginx plugin
sudo apt-get install -y certbot python3-certbot-nginx

# Create directory for certbot verification
sudo mkdir -p /var/www/certbot

# Stop Nginx temporarily
sudo systemctl stop nginx

# Obtain SSL certificate
sudo certbot certonly --standalone \
  --preferred-challenges http \
  --agree-tos \
  --email admin@aigenconsult.com \
  --domain matching.aigenconsult.com

# Start Nginx
sudo systemctl start nginx
```

### 6. Restart Nginx

```bash
sudo systemctl restart nginx
```

## Verifying the Deployment

After completing the setup, you can verify that everything is working correctly:

1. Check if the Docker container is running:
   ```bash
   docker ps | grep matching-service
   ```

2. Check if Nginx is running:
   ```bash
   sudo systemctl status nginx
   ```

3. Test the HTTPS connection:
   ```bash
   curl -k https://matching.aigenconsult.com
   ```

4. Open https://matching.aigenconsult.com in your browser

## Troubleshooting

### Docker Issues

If the Docker container is not running:
```bash
# Check container logs
docker logs matching-service

# Restart the container
docker restart matching-service
```

### Nginx Issues

If Nginx is not working correctly:
```bash
# Check Nginx configuration
sudo nginx -t

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### SSL Certificate Issues

If there are issues with the SSL certificates:
```bash
# Check certbot logs
sudo tail -f /var/log/letsencrypt/letsencrypt.log

# Renew certificates manually
sudo certbot renew --dry-run
```

## SSL Certificate Renewal

Certbot automatically creates a cron job or systemd timer to renew certificates before they expire. You can manually trigger a renewal with:

```bash
sudo certbot renew
```

## Environment Variables

The Docker container uses the `.env.docker` file for configuration. You can modify this file to change the service settings.

Key environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `MONGODB`: MongoDB connection string
- `REDIS_HOST`: Redis host
- `SECRET_KEY`: Secret key for JWT authentication

## Security Considerations

- The provided Nginx configuration includes modern SSL settings for security
- Make sure to use strong, unique passwords for your database connections
- Consider setting up a firewall to restrict access to your server
- Regularly update your system and dependencies

## Local Development with Docker Compose (Using Dockerfile.dev)

For local development using the host machine's services (MongoDB, PostgreSQL, Redis, RabbitMQ), you can use the provided docker-compose.yml file:

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

This will start:
- The matching service on port 8002

The service will connect to:
- MongoDB running on the host (localhost:27017)
- PostgreSQL running on the host (localhost:5432)
- Redis running on the host (localhost:6379)
- RabbitMQ running on the host (localhost:5672)

Make sure these services are running on the host machine before starting the Docker container.

## Quick Local Testing (Using Dockerfile.dev)

For quick testing without setting up all dependencies, you can use the provided run_local.sh script:

```bash
# Make the script executable
chmod +x run_local.sh

# Run the script
./run_local.sh
```

This will build and run the Docker container on port 8002 using the Dockerfile.dev configuration, and will use the host machine's services for dependencies.