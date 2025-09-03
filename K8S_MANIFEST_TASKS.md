# 🚢 SuperManUS Kubernetes Manifest Tasks - SYSTEMATIC BREAKDOWN
## Completing T3.2.1: 8 Missing Manifests (1/9 complete)

**Task Parent:** T3.2.1: Add Kubernetes deployment configs  
**Current Status:** 11% complete (namespace.yaml only)  
**Validation Required:** Each manifest must pass kubectl validation before completion claim

---

## 📋 INDIVIDUAL ATOMIC TASKS

### T3.2.1.1: Redis Deployment Manifest
**File:** `k8s/redis-deployment.yaml`  
**Components Required:**
- Deployment with Redis 7-alpine image
- Service for internal cluster access
- PersistentVolumeClaim for data persistence
- ConfigMap for Redis configuration
- Resource limits and health checks

**Validation Command:**
```bash
kubectl apply --dry-run=client --validate=true -f k8s/redis-deployment.yaml
```

**Success Criteria:**
- [ ] File exists at correct path
- [ ] kubectl validation passes
- [ ] Contains all required components
- [ ] Resource specifications appropriate for cluster

---

### T3.2.1.2: PostgreSQL Deployment Manifest  
**File:** `k8s/postgres-deployment.yaml`
**Components Required:**
- Deployment with PostgreSQL 16-alpine image
- Service for database connections
- PersistentVolumeClaim for database storage
- Secret for database credentials
- ConfigMap for initialization scripts
- Health checks and resource limits

**Validation Command:**
```bash
kubectl apply --dry-run=client --validate=true -f k8s/postgres-deployment.yaml
```

**Success Criteria:**
- [ ] File exists at correct path
- [ ] kubectl validation passes
- [ ] Secrets properly base64 encoded
- [ ] Initialization scripts included

---

### T3.2.1.3: MCP Server Deployment Manifest
**File:** `k8s/mcp-server-deployment.yaml`
**Components Required:**
- Deployment with proper image reference
- Service for HTTP and WebSocket ports
- ConfigMap for application configuration  
- Environment variables for service discovery
- Resource specifications and scaling configuration

**Validation Command:**
```bash
kubectl apply --dry-run=client --validate=true -f k8s/mcp-server-deployment.yaml
```

**Success Criteria:**
- [ ] File exists at correct path
- [ ] kubectl validation passes
- [ ] Both HTTP (8000) and WebSocket (8001) ports configured
- [ ] Environment variables properly set

---

### T3.2.1.4: Celery Workers Deployment Manifest
**File:** `k8s/celery-deployment.yaml`  
**Components Required:**
- Deployment for Celery workers with scaling
- Deployment for Celery beat scheduler
- Deployment for Flower monitoring UI
- Service for Flower web interface
- Proper queue configuration and resource limits

**Validation Command:**
```bash
kubectl apply --dry-run=client --validate=true -f k8s/celery-deployment.yaml
```

**Success Criteria:**
- [ ] File exists at correct path
- [ ] kubectl validation passes
- [ ] Multiple deployments in single file
- [ ] Flower UI accessible via service

---

### T3.2.1.5: AI Services Deployment Manifest
**File:** `k8s/ai-services-deployment.yaml`
**Components Required:**
- Voice pipeline deployment with GPU node selector
- Image generator deployment with GPU requirements
- Code generator deployment
- Search service deployment
- Services for all AI components
- PersistentVolumeClaims for model storage

**Validation Command:**
```bash
kubectl apply --dry-run=client --validate=true -f k8s/ai-services-deployment.yaml
```

**Success Criteria:**
- [ ] File exists at correct path
- [ ] kubectl validation passes
- [ ] GPU node selectors properly configured
- [ ] All AI services have corresponding Service objects

---

### T3.2.1.6: Ingress Configuration Manifest
**File:** `k8s/ingress.yaml`
**Components Required:**
- Ingress resource for external access
- TLS certificate configuration
- Path-based routing to all services
- SSL termination and redirects
- WebSocket upgrade support for MCP server

**Validation Command:**
```bash
kubectl apply --dry-run=client --validate=true -f k8s/ingress.yaml
```

**Success Criteria:**
- [ ] File exists at correct path
- [ ] kubectl validation passes
- [ ] All service endpoints properly routed
- [ ] TLS configuration valid

---

### T3.2.1.7: Monitoring Stack Manifest
**File:** `k8s/monitoring.yaml`
**Components Required:**
- Prometheus deployment with configuration
- Grafana deployment with dashboards
- Services for both monitoring components
- ConfigMaps for Prometheus rules and Grafana datasources
- PersistentVolumeClaims for monitoring data

**Validation Command:**
```bash
kubectl apply --dry-run=client --validate=true -f k8s/monitoring.yaml
```

**Success Criteria:**
- [ ] File exists at correct path
- [ ] kubectl validation passes
- [ ] Prometheus configuration syntactically correct
- [ ] Grafana dashboard configs included

---

### T3.2.1.8: Deployment Automation Script
**File:** `k8s/deploy.sh`
**Components Required:**
- Bash script for automated deployment
- Validation of kubectl availability
- Sequential deployment with dependency checking
- Health check verification
- Rollback capability on failure
- Usage documentation

**Validation Command:**
```bash
bash -n k8s/deploy.sh && echo "Script syntax valid"
chmod +x k8s/deploy.sh && echo "Script executable"
```

**Success Criteria:**
- [ ] File exists at correct path
- [ ] Bash syntax validation passes
- [ ] Script is executable
- [ ] Contains proper error handling

---

## 🎯 COMPLETION WORKFLOW

### For Each Manifest Task:
1. **Create Work Log Entry** using WORK_LOG_TEMPLATE.md
2. **Write Manifest File** with all required components
3. **Validate Syntax** using kubectl dry-run
4. **Add Context Markers** per SuperManUS standards
5. **Update Task Status** with validation proof
6. **Move to Next Task** only after validation passes

### Final T3.2.1 Completion:
- All 8 manifests exist and validate
- deploy.sh script tested and functional
- SESSION_STATE.json updated with proof
- Full deployment tested (if cluster available)

---

## ⚠️ ANTI-CONFUSION ENFORCEMENT

### NEVER claim task completion without:
- Actual file existence verification: `ls -la k8s/filename.yaml`
- Successful kubectl validation: `kubectl apply --dry-run=client -f filename.yaml`
- All required components present in manifest
- Proper YAML syntax and Kubernetes API compliance

### MANDATORY validation before moving to next task:
```bash
# File existence check
ls -la k8s/redis-deployment.yaml || echo "ERROR: File does not exist"

# Syntax validation  
kubectl apply --dry-run=client --validate=true -f k8s/redis-deployment.yaml || echo "ERROR: Invalid manifest"

# Component count verification
grep -c "kind:" k8s/redis-deployment.yaml | grep -q "4" || echo "ERROR: Missing components"
```

---

**Next Action:** Begin T3.2.1.1 (Redis manifest) using WORK_LOG_TEMPLATE.md