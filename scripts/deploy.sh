#!/bin/bash

# Rogue Garmin Bridge Deployment Script
# This script handles deployment of the application in different environments

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DEFAULT_ENV="production"
DEFAULT_COMPOSE_FILE="docker-compose.yml"

# Detect docker compose command (v2 plugin preferred over v1 standalone)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE=""
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
Rogue Garmin Bridge Deployment Script

Usage: $0 [OPTIONS] COMMAND

Commands:
    deploy      Deploy the application
    start       Start the application
    stop        Stop the application
    restart     Restart the application
    status      Show application status
    logs        Show application logs
    update      Update and restart the application
    backup      Create a backup of application data
    restore     Restore from backup
    cleanup     Clean up old containers and images

Options:
    -e, --env ENV           Environment (production, development, testing)
    -f, --file FILE         Docker compose file to use
    -h, --help              Show this help message
    --no-backup             Skip backup during deployment
    --force                 Force operation without confirmation

Examples:
    $0 deploy                           # Deploy in production
    $0 -e development deploy            # Deploy in development
    $0 -f docker-compose.dev.yml start  # Start with specific compose file
    $0 logs                             # Show logs
    $0 backup                           # Create backup

EOF
}

# Parse command line arguments
ENV="$DEFAULT_ENV"
COMPOSE_FILE=""
NO_BACKUP=false
FORCE=false
COMMAND=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            ENV="$2"
            shift 2
            ;;
        -f|--file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        --no-backup)
            NO_BACKUP=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        deploy|start|stop|restart|status|logs|update|backup|restore|cleanup)
            COMMAND="$1"
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Set compose file based on environment if not specified
if [[ -z "$COMPOSE_FILE" ]]; then
    case "$ENV" in
        production|prod)
            COMPOSE_FILE="docker-compose.prod.yml"
            ;;
        raspberry-pi|rpi)
            COMPOSE_FILE="docker-compose.rpi.yml"
            ;;
        development|dev)
            COMPOSE_FILE="docker-compose.dev.yml"
            ;;
        staging)
            COMPOSE_FILE="docker-compose.staging.yml"
            ;;
        testing|test)
            COMPOSE_FILE="docker-compose.test.yml"
            ;;
        *)
            log_error "Unknown environment: $ENV"
            log_info "Valid environments: production, raspberry-pi, development, staging, testing"
            exit 1
            ;;
    esac
fi

# Validate command
if [[ -z "$COMMAND" ]]; then
    log_error "No command specified"
    show_help
    exit 1
fi

# Change to project directory
cd "$PROJECT_DIR"

# Validate compose file exists
if [[ ! -f "$COMPOSE_FILE" ]]; then
    log_error "Compose file not found: $COMPOSE_FILE"
    exit 1
fi

# Set environment file based on environment
ENV_FILE=""
case "$ENV" in
    production|prod)
        ENV_FILE=".env"
        ;;
    raspberry-pi|rpi)
        ENV_FILE=".env.rpi"
        ;;
    development|dev)
        ENV_FILE=".env"
        ;;
    staging)
        ENV_FILE=".env.staging"
        ;;
    testing|test)
        ENV_FILE=".env"
        ;;
esac

# Check if environment file exists
if [[ ! -f "$ENV_FILE" ]]; then
    log_warning "Environment file not found: $ENV_FILE"
    if [[ -f ".env.example" ]]; then
        log_info "Creating $ENV_FILE from .env.example"
        cp .env.example "$ENV_FILE"
        log_warning "Please review and customize $ENV_FILE before deployment"
        if [[ "$ENV" == "production" ]]; then
            log_error "Production deployment requires customized environment file"
            exit 1
        fi
    fi
fi

log_info "Using environment: $ENV"
log_info "Using compose file: $COMPOSE_FILE"
log_info "Using environment file: $ENV_FILE"

# Pre-deployment checks
check_requirements() {
    log_info "Checking requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if [[ -z "$DOCKER_COMPOSE" ]]; then
        log_error "Docker Compose is not installed (tried 'docker compose' and 'docker-compose')"
        exit 1
    fi
    log_info "Using compose command: $DOCKER_COMPOSE"
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    log_success "Requirements check passed"
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    
    mkdir -p data logs fit_files backups config nginx/ssl
    
    # Set proper permissions
    chmod 755 data logs fit_files backups
    
    log_success "Directories created"
}

# Generate SSL certificates for development
generate_dev_ssl() {
    if [[ "$ENV" == "development" ]] && [[ ! -f "nginx/ssl/cert.pem" ]]; then
        log_info "Generating self-signed SSL certificate for development..."
        
        openssl req -x509 -newkey rsa:4096 -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem \
            -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost" \
            2>/dev/null || log_warning "Failed to generate SSL certificate"
    fi
}

# Create backup
create_backup() {
    if [[ "$NO_BACKUP" == true ]]; then
        log_info "Skipping backup (--no-backup specified)"
        return
    fi
    
    log_info "Creating backup..."
    
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup data directory
    if [[ -d "data" ]]; then
        cp -r data "$BACKUP_DIR/"
        log_success "Data backed up to $BACKUP_DIR/data"
    fi
    
    # Backup configuration
    if [[ -d "config" ]]; then
        cp -r config "$BACKUP_DIR/"
        log_success "Configuration backed up to $BACKUP_DIR/config"
    fi
    
    # Create backup info file
    cat > "$BACKUP_DIR/backup_info.txt" << EOF
Backup created: $(date)
Environment: $ENV
Compose file: $COMPOSE_FILE
Git commit: $(git rev-parse HEAD 2>/dev/null || echo "unknown")
EOF
    
    log_success "Backup created: $BACKUP_DIR"
}

# Deploy function
deploy() {
    log_info "Starting deployment..."
    
    check_requirements
    
    # Validate configuration
    log_info "Validating configuration..."
    if command -v python3 &> /dev/null; then
        if ! python3 scripts/validate-config.py "$ENV" --env-file "$ENV_FILE"; then
            log_error "Configuration validation failed"
            exit 1
        fi
    else
        log_warning "Python3 not found, skipping configuration validation"
    fi
    
    # Additional production checks
    if [[ "$ENV" == "production" || "$ENV" == "prod" ]]; then
        log_info "Production deployment detected. Performing additional checks..."
        
        # Confirm production deployment
        if [[ "$FORCE" != true ]]; then
            read -p "Are you sure you want to deploy to PRODUCTION? (yes/no): " confirm
            if [[ "$confirm" != "yes" ]]; then
                log_info "Production deployment cancelled."
                exit 0
            fi
        fi
    fi
    
    create_directories
    generate_dev_ssl
    create_backup
    
    # Pull latest images
    log_info "Pulling latest images..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull

    # Build images
    log_info "Building images..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build

    # Start services
    log_info "Starting services..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
    
    # Wait for health check
    log_info "Waiting for application to be healthy..."
    sleep 10
    
    # Check health
    if curl -f http://localhost:5000/health &> /dev/null; then
        log_success "Deployment successful! Application is healthy."
    else
        log_warning "Deployment completed but health check failed. Check logs for issues."
    fi
}

# Start function
start() {
    log_info "Starting application..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
    log_success "Application started"
}

# Stop function
stop() {
    log_info "Stopping application..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
    log_success "Application stopped"
}

# Restart function
restart() {
    log_info "Restarting application..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart
    log_success "Application restarted"
}

# Status function
status() {
    log_info "Application status:"
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
    
    # Get port from environment file
    PORT=$(grep "APP_PORT" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2 | tr -d ' ' || echo "5000")
    
    # Health check
    if curl -f "http://localhost:$PORT/health" &> /dev/null; then
        log_success "Application is healthy"
    else
        log_warning "Application health check failed"
    fi
}

# Logs function
show_logs() {
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f
}

# Update function
update() {
    log_info "Updating application..."
    
    # Pull latest code (if git repository)
    if [[ -d ".git" ]]; then
        log_info "Pulling latest code..."
        git pull
    fi
    
    # Redeploy
    deploy
}

# Cleanup function
cleanup() {
    log_info "Cleaning up old containers and images..."
    
    # Remove stopped containers
    docker container prune -f
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused volumes (with confirmation)
    if [[ "$FORCE" == true ]]; then
        docker volume prune -f
    else
        docker volume prune
    fi
    
    log_success "Cleanup completed"
}

# Restore function
restore() {
    log_info "Available backups:"
    ls -la backups/ 2>/dev/null || {
        log_error "No backups directory found"
        exit 1
    }
    
    echo "Enter backup directory name to restore from:"
    read -r BACKUP_NAME
    
    BACKUP_PATH="backups/$BACKUP_NAME"
    
    if [[ ! -d "$BACKUP_PATH" ]]; then
        log_error "Backup not found: $BACKUP_PATH"
        exit 1
    fi
    
    if [[ "$FORCE" != true ]]; then
        echo "This will overwrite current data. Are you sure? (y/N)"
        read -r CONFIRM
        if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
            log_info "Restore cancelled"
            exit 0
        fi
    fi
    
    # Stop application
    stop
    
    # Restore data
    if [[ -d "$BACKUP_PATH/data" ]]; then
        rm -rf data
        cp -r "$BACKUP_PATH/data" .
        log_success "Data restored from backup"
    fi
    
    # Restore configuration
    if [[ -d "$BACKUP_PATH/config" ]]; then
        rm -rf config
        cp -r "$BACKUP_PATH/config" .
        log_success "Configuration restored from backup"
    fi
    
    # Start application
    start
    
    log_success "Restore completed"
}

# Execute command
case "$COMMAND" in
    deploy)
        deploy
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        show_logs
        ;;
    update)
        update
        ;;
    backup)
        create_backup
        ;;
    restore)
        restore
        ;;
    cleanup)
        cleanup
        ;;
    *)
        log_error "Unknown command: $COMMAND"
        show_help
        exit 1
        ;;
esac