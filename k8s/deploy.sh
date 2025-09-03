#!/bin/bash

# SuperManUS Kubernetes Deployment Script
# Deploys all components to Kubernetes cluster

set -e

NAMESPACE="supermanus"
KUBECTL_CMD=${KUBECTL_CMD:-kubectl}

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

# Check if kubectl is available
check_kubectl() {
    if ! command -v $KUBECTL_CMD &> /dev/null; then
        log_error "kubectl not found. Please install kubectl first."
        exit 1
    fi
    
    log_info "Using kubectl: $(which $KUBECTL_CMD)"
    
    # Check cluster connectivity
    if ! $KUBECTL_CMD cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster. Please check your kubectl configuration."
        exit 1
    fi
    
    log_success "Kubernetes cluster connection verified"
}

# Create namespace if it doesn't exist
create_namespace() {
    log_info "Creating namespace: $NAMESPACE"
    
    if $KUBECTL_CMD get namespace $NAMESPACE &> /dev/null; then
        log_warning "Namespace $NAMESPACE already exists"
    else
        $KUBECTL_CMD apply -f namespace.yaml
        log_success "Namespace created"
    fi
}

# Deploy infrastructure components (Redis, PostgreSQL)
deploy_infrastructure() {
    log_info "Deploying infrastructure components..."
    
    log_info "Deploying Redis..."
    $KUBECTL_CMD apply -f redis-deployment.yaml
    
    log_info "Deploying PostgreSQL..."
    $KUBECTL_CMD apply -f postgres-deployment.yaml
    
    log_success "Infrastructure components deployed"
}

# Wait for infrastructure to be ready
wait_for_infrastructure() {
    log_info "Waiting for infrastructure to be ready..."
    
    log_info "Waiting for Redis..."
    $KUBECTL_CMD wait --for=condition=available --timeout=300s deployment/redis -n $NAMESPACE
    
    log_info "Waiting for PostgreSQL..."
    $KUBECTL_CMD wait --for=condition=available --timeout=300s deployment/postgres -n $NAMESPACE
    
    log_success "Infrastructure is ready"
}

# Deploy Celery components
deploy_celery() {
    log_info "Deploying Celery task queue..."
    
    $KUBECTL_CMD apply -f celery-deployment.yaml
    
    log_info "Waiting for Celery workers..."
    $KUBECTL_CMD wait --for=condition=available --timeout=300s deployment/celery-worker -n $NAMESPACE
    
    log_success "Celery deployed"
}

# Deploy MCP server
deploy_mcp_server() {
    log_info "Deploying MCP Server..."
    
    $KUBECTL_CMD apply -f mcp-server-deployment.yaml
    
    log_info "Waiting for MCP Server..."
    $KUBECTL_CMD wait --for=condition=available --timeout=300s deployment/mcp-server -n $NAMESPACE
    
    log_success "MCP Server deployed"
}

# Deploy AI services
deploy_ai_services() {
    log_info "Deploying AI services..."
    
    $KUBECTL_CMD apply -f ai-services-deployment.yaml
    
    log_info "Waiting for AI services..."
    $KUBECTL_CMD wait --for=condition=available --timeout=600s deployment/voice-pipeline -n $NAMESPACE || log_warning "Voice pipeline deployment timeout"
    $KUBECTL_CMD wait --for=condition=available --timeout=600s deployment/search-service -n $NAMESPACE || log_warning "Search service deployment timeout"
    
    # GPU-dependent services might take longer or fail without proper GPU nodes
    log_warning "Note: GPU-dependent services (image-generator, code-generator) may require GPU nodes"
    
    log_success "AI services deployment initiated"
}

# Deploy monitoring
deploy_monitoring() {
    log_info "Deploying monitoring stack..."
    
    $KUBECTL_CMD apply -f monitoring.yaml
    
    log_info "Waiting for monitoring services..."
    $KUBECTL_CMD wait --for=condition=available --timeout=300s deployment/prometheus -n $NAMESPACE
    $KUBECTL_CMD wait --for=condition=available --timeout=300s deployment/grafana -n $NAMESPACE
    
    log_success "Monitoring deployed"
}

# Deploy ingress
deploy_ingress() {
    log_info "Deploying ingress controller..."
    
    # Check if nginx ingress controller is installed
    if ! $KUBECTL_CMD get ingressclass nginx &> /dev/null; then
        log_warning "NGINX Ingress Controller not found. Installing..."
        $KUBECTL_CMD apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml
        
        log_info "Waiting for NGINX Ingress Controller..."
        $KUBECTL_CMD wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=300s
    fi
    
    $KUBECTL_CMD apply -f ingress.yaml
    
    log_success "Ingress deployed"
}

# Check deployment status
check_deployment_status() {
    log_info "Checking deployment status..."
    
    echo
    echo "=== Deployment Status ==="
    $KUBECTL_CMD get pods -n $NAMESPACE -o wide
    
    echo
    echo "=== Services ==="
    $KUBECTL_CMD get services -n $NAMESPACE
    
    echo
    echo "=== Ingress ==="
    $KUBECTL_CMD get ingress -n $NAMESPACE
    
    echo
    echo "=== Persistent Volumes ==="
    $KUBECTL_CMD get pvc -n $NAMESPACE
}

# Get service endpoints
get_endpoints() {
    log_info "Service endpoints:"
    
    echo
    echo "=== External Access ==="
    
    # Get ingress IP
    INGRESS_IP=$($KUBECTL_CMD get ingress supermanus-ingress -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    
    if [ "$INGRESS_IP" = "pending" ]; then
        log_warning "Ingress IP is pending. Use port-forward for testing:"
        echo "  kubectl port-forward -n $NAMESPACE svc/mcp-server 8000:8000"
        echo "  kubectl port-forward -n $NAMESPACE svc/celery-flower 5555:5555"
        echo "  kubectl port-forward -n $NAMESPACE svc/grafana 3000:3000"
    else
        echo "Main API: https://api.supermanus.local (${INGRESS_IP})"
        echo "Services: https://supermanus.local (${INGRESS_IP})"
        echo "Flower: https://flower.supermanus.local (${INGRESS_IP})"
        echo "Monitoring: https://monitoring.supermanus.local (${INGRESS_IP})"
        echo
        echo "Add to /etc/hosts:"
        echo "${INGRESS_IP} api.supermanus.local"
        echo "${INGRESS_IP} supermanus.local"
        echo "${INGRESS_IP} flower.supermanus.local"
        echo "${INGRESS_IP} monitoring.supermanus.local"
    fi
}

# Cleanup function
cleanup() {
    log_info "Cleaning up SuperManUS deployment..."
    
    $KUBECTL_CMD delete namespace $NAMESPACE --ignore-not-found=true
    
    log_success "Cleanup completed"
}

# Main deployment function
deploy_all() {
    log_info "🦸 Starting SuperManUS Kubernetes deployment..."
    
    check_kubectl
    create_namespace
    deploy_infrastructure
    wait_for_infrastructure
    deploy_celery
    deploy_mcp_server
    deploy_ai_services
    deploy_monitoring
    deploy_ingress
    
    log_success "🎉 SuperManUS deployment completed!"
    
    check_deployment_status
    get_endpoints
}

# Scale deployment
scale_deployment() {
    COMPONENT=$1
    REPLICAS=$2
    
    if [ -z "$COMPONENT" ] || [ -z "$REPLICAS" ]; then
        log_error "Usage: $0 scale <component> <replicas>"
        echo "Available components: mcp-server, celery-worker, voice-pipeline, search-service"
        exit 1
    fi
    
    log_info "Scaling $COMPONENT to $REPLICAS replicas..."
    $KUBECTL_CMD scale deployment/$COMPONENT --replicas=$REPLICAS -n $NAMESPACE
    
    log_success "$COMPONENT scaled to $REPLICAS replicas"
}

# Show usage
usage() {
    echo "SuperManUS Kubernetes Deployment Script"
    echo
    echo "Usage: $0 [command]"
    echo
    echo "Commands:"
    echo "  deploy    - Deploy all SuperManUS components (default)"
    echo "  cleanup   - Remove all SuperManUS components"
    echo "  status    - Show deployment status"
    echo "  endpoints - Show service endpoints"
    echo "  scale     - Scale a component: $0 scale <component> <replicas>"
    echo "  help      - Show this help message"
    echo
    echo "Examples:"
    echo "  $0                              # Deploy everything"
    echo "  $0 deploy                       # Deploy everything"
    echo "  $0 scale celery-worker 5        # Scale Celery workers to 5"
    echo "  $0 cleanup                      # Remove all components"
    echo
}

# Main script logic
case "${1:-deploy}" in
    "deploy")
        deploy_all
        ;;
    "cleanup")
        cleanup
        ;;
    "status")
        check_deployment_status
        ;;
    "endpoints")
        get_endpoints
        ;;
    "scale")
        scale_deployment $2 $3
        ;;
    "help"|"-h"|"--help")
        usage
        ;;
    *)
        log_error "Unknown command: $1"
        usage
        exit 1
        ;;
esac