# Raspberry Pi Quick Start Guide

## Prerequisites

- Raspberry Pi 4 (4GB+ RAM recommended)
- Raspberry Pi OS (64-bit)
- Docker and Docker Compose installed
- Git installed
- Network connectivity

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Douglas-Christian/rogue_garmin_bridge.git
cd rogue_garmin_bridge
```

### 2. Deploy

```bash
# Basic deployment (recommended for most users)
./scripts/deploy.sh -e raspberry-pi deploy

# With monitoring dashboard
./scripts/deploy.sh -e raspberry-pi -p monitoring deploy

# Full deployment with reverse proxy
./scripts/deploy.sh -e raspberry-pi -p nginx,monitoring deploy
```

## Automatic Updates from GitHub

The auto-update script checks GitHub for new commits and redeploys automatically when changes are found.

### Set Up Automatic Updates (Cron)

```bash
# Open crontab editor
crontab -e

# Check for updates every hour (recommended):
0 * * * * /home/pi/rogue_garmin_bridge/scripts/auto-update.sh >> /home/pi/rogue_garmin_bridge/logs/auto-update.log 2>&1

# Or check every 15 minutes:
*/15 * * * * /home/pi/rogue_garmin_bridge/scripts/auto-update.sh >> /home/pi/rogue_garmin_bridge/logs/auto-update.log 2>&1
```

### Manual Update Commands

```bash
# Check for updates and deploy if available
./scripts/auto-update.sh

# Check only (don't deploy)
./scripts/auto-update.sh --check-only

# Force redeploy even if no changes
./scripts/auto-update.sh --force

# Update using the deploy script
./scripts/deploy.sh -e raspberry-pi update
```

### Auto-Update Behavior

- Only redeploys when new commits are detected (saves resources)
- Uses a lock file to prevent concurrent updates
- Logs all activity to `logs/auto-update.log` with automatic rotation
- Runs a health check after deploy to verify the app started
- Cleans up old Docker images to save disk space

## Quick Commands

```bash
# Deploy
./scripts/deploy.sh -e raspberry-pi deploy

# Check status
./scripts/deploy.sh -e raspberry-pi status

# View logs
./scripts/deploy.sh -e raspberry-pi logs

# Restart
./scripts/deploy.sh -e raspberry-pi restart

# Stop
./scripts/deploy.sh -e raspberry-pi stop

# Validate configuration
python scripts/validate-docker-config.py docker-compose.rpi.yml
```

## Access Points

After deployment, access your application at:

- **Main App**: `http://<raspberry-pi-ip>:5000`
- **Health Check**: `http://<raspberry-pi-ip>:5000/health`
- **Prometheus** (if monitoring enabled): `http://<raspberry-pi-ip>:9090`
- **Grafana** (if monitoring enabled): `http://<raspberry-pi-ip>:3000`

## Network Mode

The Raspberry Pi configuration (`docker-compose.rpi.yml`) uses `network_mode: host` for Bluetooth access. This means:

- The app binds directly to the host network on port 5000
- No Docker port mapping is needed (or allowed)
- Bluetooth devices are accessible from within the container

```yaml
services:
  app:
    network_mode: host
    # NO ports declaration - app binds directly to host:5000
    environment:
      - APP_PORT=5000
```

## Troubleshooting

### Check if app is running
```bash
curl http://localhost:5000/health
```

### Check Docker containers
```bash
docker ps
```

### Check port usage
```bash
sudo netstat -tulpn | grep :5000
```

### View application logs
```bash
docker logs rogue-garmin-bridge-rpi
```

### View auto-update logs
```bash
tail -50 logs/auto-update.log
```

## Resource Usage

The RPi configuration is optimized for Raspberry Pi 4 with 4GB+ RAM:

- **Main App**: 256MB RAM, 0.8 CPU cores
- **Nginx**: 64MB RAM, 0.2 CPU cores
- **Prometheus**: 128MB RAM, 0.3 CPU cores
- **Grafana**: 128MB RAM, 0.3 CPU cores

Total: ~576MB RAM when all services are running.

## Security

The configuration includes:
- Non-root user execution
- Resource limits to prevent resource exhaustion
- Proper volume permissions
- Health checks for service monitoring

For production use, consider:
- Setting up SSL certificates
- Configuring firewall rules
- Using strong passwords
- Regular security updates
