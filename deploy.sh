#!/bin/bash

set -e

ENVIRONMENT=${1:-staging}
ACTION=${2:-deploy}

echo "SuperManUS Deployment Script"
echo "Environment: $ENVIRONMENT"
echo "Action: $ACTION"
echo ""

# Configuration
REPO_URL="https://github.com/wspotter/SuperManUS.git"
DEPLOY_DIR="/opt/supermanus"
CONFIG_DIR="/etc/supermanus"
LOG_DIR="/var/log/supermanus"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking requirements..."
    
    command -v docker >/dev/null 2>&1 || { log_error "Docker is required but not installed."; exit 1; }
    command -v docker-compose >/dev/null 2>&1 || { log_error "Docker Compose is required but not installed."; exit 1; }
    command -v git >/dev/null 2>&1 || { log_error "Git is required but not installed."; exit 1; }
    
    log_info "All requirements met"
}

setup_directories() {
    log_info "Setting up directories..."
    
    sudo mkdir -p $DEPLOY_DIR
    sudo mkdir -p $CONFIG_DIR
    sudo mkdir -p $LOG_DIR
    sudo mkdir -p $LOG_DIR/{voice,image,code,search,mcp}
    
    log_info "Directories created"
}

clone_or_update_repo() {
    log_info "Updating codebase..."
    
    if [ -d "$DEPLOY_DIR/.git" ]; then
        cd $DEPLOY_DIR
        sudo git pull origin main
    else
        sudo git clone $REPO_URL $DEPLOY_DIR
        cd $DEPLOY_DIR
    fi
    
    log_info "Code updated"
}

create_env_file() {
    log_info "Creating environment configuration..."
    
    cat > $CONFIG_DIR/.env << EOF
# SuperManUS Environment Configuration
# Generated: $(date)

# Environment
ENVIRONMENT=$ENVIRONMENT

# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=supermanus
POSTGRES_USER=supermanus
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Services
MCP_SERVER_URL=http://mcp-server:3000
VOICE_SERVICE_URL=http://voice:8001
IMAGE_SERVICE_URL=http://image:8002
CODE_SERVICE_URL=http://code:8003
SEARCH_SERVICE_URL=http://search:8004

# GPU
GPU_ENABLED=true
ROCM_PATH=/opt/rocm

# Logging
LOG_LEVEL=INFO

# Session
SESSION_TIMEOUT=3600

# Anticipation
ANTICIPATION_THRESHOLD=0.75
EOF
    
    log_info "Environment configured"
}

build_images() {
    log_info "Building Docker images..."
    
    cd $DEPLOY_DIR
    ./build.sh
    
    log_info "Images built successfully"
}

deploy_services() {
    log_info "Deploying services..."
    
    cd $DEPLOY_DIR
    
    # Stop existing services
    docker-compose down || true
    
    # Start services
    docker-compose --env-file $CONFIG_DIR/.env up -d
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 30
    
    # Check health
    for service in mcp-server voice image code search; do
        if docker-compose ps | grep -q "${service}.*Up"; then
            log_info "$service is running"
        else
            log_warn "$service may not be running properly"
        fi
    done
    
    log_info "Services deployed"
}

setup_monitoring() {
    log_info "Setting up monitoring..."
    
    # Create systemd service for auto-restart
    sudo cat > /etc/systemd/system/supermanus.service << EOF
[Unit]
Description=SuperManUS AI System
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$DEPLOY_DIR
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable supermanus.service
    
    log_info "Monitoring configured"
}

setup_backup() {
    log_info "Setting up backup..."
    
    # Create backup script
    cat > $CONFIG_DIR/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/supermanus"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
docker exec postgres pg_dump -U supermanus supermanus | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup Redis
docker exec redis redis-cli BGSAVE
docker cp redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Keep only last 7 days of backups
find $BACKUP_DIR -type f -mtime +7 -delete
EOF
    
    chmod +x $CONFIG_DIR/backup.sh
    
    # Add to crontab
    (crontab -l 2>/dev/null; echo "0 2 * * * $CONFIG_DIR/backup.sh") | crontab -
    
    log_info "Backup configured"
}

health_check() {
    log_info "Running health checks..."
    
    SERVICES=(
        "http://localhost:3000/health"
        "http://localhost:8001/health"
        "http://localhost:8002/health"
        "http://localhost:8003/health"
        "http://localhost:8004/health"
    )
    
    for url in "${SERVICES[@]}"; do
        if curl -f -s "$url" > /dev/null; then
            log_info "✓ $url is healthy"
        else
            log_error "✗ $url is not responding"
        fi
    done
}

rollback() {
    log_warn "Rolling back deployment..."
    
    cd $DEPLOY_DIR
    
    # Get previous commit
    PREVIOUS_COMMIT=$(git rev-parse HEAD~1)
    
    # Rollback code
    sudo git checkout $PREVIOUS_COMMIT
    
    # Rebuild and redeploy
    build_images
    deploy_services
    
    log_info "Rollback complete to commit: $PREVIOUS_COMMIT"
}

show_status() {
    log_info "System Status:"
    echo ""
    
    docker-compose ps
    
    echo ""
    log_info "Resource Usage:"
    docker stats --no-stream
    
    echo ""
    log_info "Service URLs:"
    echo "  Dashboard:  http://localhost:80"
    echo "  MCP Server: http://localhost:3000"
    echo "  Voice:      http://localhost:8001"
    echo "  Image:      http://localhost:8002"
    echo "  Code:       http://localhost:8003"
    echo "  Search:     http://localhost:8004"
}

# Main execution
case $ACTION in
    deploy)
        check_requirements
        setup_directories
        clone_or_update_repo
        create_env_file
        build_images
        deploy_services
        setup_monitoring
        setup_backup
        health_check
        show_status
        log_info "Deployment complete!"
        ;;
    
    update)
        clone_or_update_repo
        build_images
        deploy_services
        health_check
        log_info "Update complete!"
        ;;
    
    rollback)
        rollback
        ;;
    
    status)
        show_status
        ;;
    
    health)
        health_check
        ;;
    
    stop)
        log_info "Stopping services..."
        cd $DEPLOY_DIR
        docker-compose down
        log_info "Services stopped"
        ;;
    
    start)
        log_info "Starting services..."
        cd $DEPLOY_DIR
        docker-compose up -d
        log_info "Services started"
        ;;
    
    logs)
        SERVICE=${3:-all}
        if [ "$SERVICE" = "all" ]; then
            docker-compose logs -f
        else
            docker-compose logs -f $SERVICE
        fi
        ;;
    
    *)
        echo "Usage: $0 [staging|production] [deploy|update|rollback|status|health|stop|start|logs]"
        echo ""
        echo "Actions:"
        echo "  deploy   - Full deployment with setup"
        echo "  update   - Update code and redeploy"
        echo "  rollback - Rollback to previous version"
        echo "  status   - Show system status"
        echo "  health   - Run health checks"
        echo "  stop     - Stop all services"
        echo "  start    - Start all services"
        echo "  logs     - View service logs"
        exit 1
        ;;
esac