# Phase 5: Kubernetes Deployment

## Overview
This phase deploys the containerized application to Kubernetes, setting up all necessary resources including namespaces, configurations, persistent storage, and services.

## Kubernetes Fundamentals

### What is Kubernetes?
Kubernetes (K8s) is an open-source container orchestration platform that automates the deployment, scaling, and management of containerized applications. Originally developed by Google, it's now maintained by the Cloud Native Computing Foundation (CNCF).

### Core Concepts

#### 1. **Cluster Architecture**
```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
├─────────────────────────────────────────────────────────────┤
│  Control Plane (Master)          │   Worker Nodes           │
│  ┌─────────────────────┐        │  ┌──────────────────┐   │
│  │   API Server        │        │  │  Node 1          │   │
│  │   (Entry point)     │        │  │  ┌────────────┐  │   │
│  └─────────────────────┘        │  │  │   Kubelet  │  │   │
│  ┌─────────────────────┐        │  │  └────────────┘  │   │
│  │   etcd              │        │  │  ┌────────────┐  │   │
│  │   (Data store)      │        │  │  │   Pods     │  │   │
│  └─────────────────────┘        │  │  └────────────┘  │   │
│  ┌─────────────────────┐        │  └──────────────────┘   │
│  │   Controller        │        │  ┌──────────────────┐   │
│  │   Manager           │        │  │  Node 2          │   │
│  └─────────────────────┘        │  │  ...             │   │
│  ┌─────────────────────┐        │  └──────────────────┘   │
│  │   Scheduler         │        │                          │
│  └─────────────────────┘        │                          │
└─────────────────────────────────────────────────────────────┘
```

#### 2. **Key Components Explained**

**Control Plane Components:**
- **API Server**: The front-end of Kubernetes, handles all REST operations
- **etcd**: Distributed key-value store that holds all cluster data
- **Scheduler**: Assigns pods to nodes based on resource requirements
- **Controller Manager**: Runs controller processes (node controller, replication controller, etc.)

**Node Components:**
- **Kubelet**: Agent that ensures containers are running in pods
- **Container Runtime**: Software responsible for running containers (Docker, containerd)
- **Kube-proxy**: Maintains network rules for pod communication

#### 3. **Kubernetes Objects**

**Pods**: The smallest deployable unit
```yaml
# A pod is like a wrapper around your container(s)
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  containers:
  - name: my-container
    image: nginx
```

**Deployments**: Manages replica sets and provides declarative updates
```yaml
# Deployments ensure your desired number of pods are always running
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-deployment
spec:
  replicas: 3  # Kubernetes will maintain 3 pods
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: myapp:1.0
```

**Services**: Exposes pods to network traffic
```yaml
# Services provide stable networking for pods
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: myapp  # Routes traffic to pods with this label
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP  # Internal only
  # type: LoadBalancer  # External access
```

### Kubernetes Patterns

#### 1. **Init Container Pattern**
Init containers run before app containers and are useful for setup tasks:
```yaml
spec:
  initContainers:
  - name: init-db
    image: busybox
    command: ['sh', '-c', 'until nc -z db-service 5432; do sleep 1; done']
  containers:
  - name: app
    image: myapp
```

#### 2. **Sidecar Pattern**
Additional containers that enhance the main container:
```yaml
spec:
  containers:
  - name: app
    image: myapp
  - name: logging-agent
    image: fluentd  # Collects logs from the app container
```

#### 3. **ConfigMap and Secret Pattern**
Separate configuration from code:
```yaml
# ConfigMap for non-sensitive data
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  database_url: "postgres://db-service:5432"

# Secret for sensitive data
apiVersion: v1
kind: Secret
metadata:
  name: app-secret
type: Opaque
data:
  password: cGFzc3dvcmQ=  # base64 encoded
```

## Prerequisites
- Phases 1-4 completed successfully
- Kubernetes cluster available (minikube, kind, or cloud provider)
- kubectl CLI installed and configured
- Docker images built from Phase 4
- Container registry access (Docker Hub, ECR, GCR, etc.)

### Setting Up a Local Kubernetes Environment

**Option 1: Minikube** (Recommended for learning)
```bash
# Install minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Start cluster
minikube start --cpus=4 --memory=8192

# Enable useful addons
minikube addons enable ingress
minikube addons enable metrics-server
```

**Option 2: Kind** (Kubernetes in Docker)
```bash
# Install kind
GO111MODULE="on" go get sigs.k8s.io/kind@v0.11.1

# Create cluster
kind create cluster --name fastapi-cluster
```

## Step 5.1: Create Kubernetes Namespace

### Understanding Namespaces
Namespaces provide a scope for names and are intended for use in environments with many users spread across multiple teams. They're like virtual clusters within a physical cluster.

**Why use namespaces?**
- **Resource isolation**: Separate environments (dev, staging, prod)
- **Access control**: Different permissions per namespace
- **Resource quotas**: Limit resource usage per namespace
- **Organization**: Group related resources

### AI Agent Instructions:
**Task**: Create a dedicated namespace for the application.

**Action 1**: Create the k8s directory structure:
```bash
mkdir -p k8s/{postgres,redis,api,workers,monitoring}
```

**Action 2**: Create `k8s/namespace.yaml`:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: fastapi-k8-proto
  labels:
    app: fastapi-k8-proto
    environment: development
```

**Understanding the YAML**:
- `apiVersion`: Kubernetes API version for this resource type
- `kind`: The type of resource (Namespace, Pod, Service, etc.)
- `metadata`: Data that helps identify the resource
- `labels`: Key-value pairs for organizing and selecting resources

**Action 3**: Apply the namespace:
```bash
kubectl apply -f k8s/namespace.yaml
```

**What happens when you apply?**
1. kubectl sends the YAML to the API server
2. API server validates the manifest
3. Data is stored in etcd
4. Namespace is created in the cluster

**Action 4**: Verify namespace creation:
```bash
kubectl get namespaces
kubectl describe namespace fastapi-k8-proto
```

**Expected outcome**: Namespace `fastapi-k8-proto` created successfully.

## Step 5.2: Create ConfigMap and Secrets

### Understanding Configuration Management
In Kubernetes, we separate configuration from application code using ConfigMaps and Secrets. This follows the "12-factor app" methodology.

**ConfigMaps vs Secrets:**
- **ConfigMaps**: Store non-sensitive configuration data
- **Secrets**: Store sensitive data (passwords, tokens, keys)
  - Base64 encoded (not encrypted by default)
  - Can be encrypted at rest with additional setup

### AI Agent Instructions:
**Task**: Create configuration and secrets for the application.

**Action 1**: Create `k8s/configmap.yaml`:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: fastapi-k8-proto
data:
  POSTGRES_SERVER: "postgres-service"
  POSTGRES_DB: "fastapi_k8_proto"
  REDIS_HOST: "redis-service"
  REDIS_PORT: "6379"
  API_V1_STR: "/api/v1"
  PROJECT_NAME: "FastAPI K8s Worker Prototype"
  VERSION: "0.1.0"
```

**Key Concepts**:
- Service names (like `postgres-service`) are DNS names within the cluster
- Kubernetes provides automatic DNS resolution: `<service-name>.<namespace>.svc.cluster.local`
- ConfigMaps can be mounted as files or environment variables

**Action 2**: Create `k8s/secrets.yaml`:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: fastapi-k8-proto
type: Opaque
stringData:
  POSTGRES_USER: "postgres"
  POSTGRES_PASSWORD: "postgres"  # Change this in production!
```

**Security Best Practices**:
1. Never commit secrets to version control
2. Use tools like Sealed Secrets or HashiCorp Vault in production
3. Enable RBAC to control secret access
4. Rotate secrets regularly

**Action 3**: Apply configurations:
```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
```

**Action 4**: Verify resources:
```bash
kubectl get configmap -n fastapi-k8-proto
kubectl get secrets -n fastapi-k8-proto

# View ConfigMap contents
kubectl describe configmap app-config -n fastapi-k8-proto

# DON'T do this in production (exposes secrets)
kubectl get secret app-secrets -n fastapi-k8-proto -o yaml
```

**Expected outcome**: ConfigMap and Secret created in the namespace.

## Step 5.3: Deploy PostgreSQL

### Understanding Stateful Applications in Kubernetes
PostgreSQL is a stateful application, which requires special consideration in Kubernetes:

**Challenges with Stateful Apps:**
- Need persistent storage that survives pod restarts
- Require stable network identities
- Often need ordered deployment and scaling

**Storage Concepts:**
- **PersistentVolume (PV)**: A piece of storage in the cluster
- **PersistentVolumeClaim (PVC)**: A request for storage by a user
- **StorageClass**: Defines different types of storage (SSD, HDD, etc.)

### AI Agent Instructions:
**Task**: Deploy PostgreSQL with persistent storage.

**Action 1**: Create `k8s/postgres/pvc.yaml`:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: fastapi-k8-proto
spec:
  accessModes:
    - ReadWriteOnce  # Can be mounted by a single node
  resources:
    requests:
      storage: 5Gi
  storageClassName: standard  # Adjust based on your cluster
```

**Access Modes Explained**:
- `ReadWriteOnce (RWO)`: Volume can be mounted as read-write by one node
- `ReadOnlyMany (ROX)`: Volume can be mounted read-only by many nodes
- `ReadWriteMany (RWX)`: Volume can be mounted as read-write by many nodes

**Action 2**: Create `k8s/postgres/deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: fastapi-k8-proto
spec:
  replicas: 1  # PostgreSQL typically runs as a single instance
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
        env:
        # Environment variables from Secret
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: POSTGRES_USER
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: POSTGRES_PASSWORD
        # Environment variable from ConfigMap
        - name: POSTGRES_DB
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: POSTGRES_DB
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        # Health checks ensure the container is running properly
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 5
          periodSeconds: 5
        # Resource management
        resources:
          requests:  # Minimum resources needed
            memory: "256Mi"
            cpu: "250m"  # 0.25 CPU cores
          limits:    # Maximum resources allowed
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
```

**Key Deployment Concepts**:
1. **Labels and Selectors**: How Kubernetes groups resources
2. **Probes**:
   - `livenessProbe`: Restarts container if it fails
   - `readinessProbe`: Removes pod from service if not ready
3. **Resource Management**: Ensures fair resource allocation

**Action 3**: Create `k8s/postgres/service.yaml`:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: fastapi-k8-proto
spec:
  selector:
    app: postgres  # Routes traffic to pods with this label
  ports:
  - port: 5432        # Service port
    targetPort: 5432  # Container port
  type: ClusterIP     # Internal cluster access only
```

**Service Types Explained**:
- `ClusterIP`: Internal cluster access only (default)
- `NodePort`: Exposes service on each node's IP
- `LoadBalancer`: Creates external load balancer (cloud providers)
- `ExternalName`: Maps service to external DNS name

**Action 4**: Deploy PostgreSQL:
```bash
kubectl apply -f k8s/postgres/pvc.yaml
kubectl apply -f k8s/postgres/deployment.yaml
kubectl apply -f k8s/postgres/service.yaml
```

**Action 5**: Verify PostgreSQL deployment:
```bash
# Check pod status
kubectl get pods -n fastapi-k8-proto -l app=postgres

# View pod logs
kubectl logs -n fastapi-k8-proto -l app=postgres

# Check PVC status
kubectl get pvc -n fastapi-k8-proto

# Test database connection
kubectl run -it --rm debug --image=postgres:15-alpine --restart=Never -n fastapi-k8-proto -- psql -h postgres-service -U postgres
```

**Expected outcome**: PostgreSQL running with persistent storage.

## Step 5.4: Deploy Redis

### Understanding Stateless Applications
Redis, when used as a cache/message broker, can be treated as stateless. If it crashes, Celery will reconnect and continue processing.

### AI Agent Instructions:
**Task**: Deploy Redis for message queuing.

**Action 1**: Create `k8s/redis/deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: fastapi-k8-proto
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        command:
        - redis-server
        - --appendonly
        - "yes"
        livenessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        volumeMounts:
        - name: redis-data
          mountPath: /data
      volumes:
      - name: redis-data
        emptyDir: {}  # Temporary storage, deleted when pod is removed
```

**Storage Options**:
- `emptyDir`: Temporary storage, good for caches
- `hostPath`: Uses node's filesystem (not portable)
- `persistentVolumeClaim`: For data that must persist

**Action 2**: Create `k8s/redis/service.yaml`:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: redis-service
  namespace: fastapi-k8-proto
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
  type: ClusterIP
```

**Action 3**: Deploy Redis:
```bash
kubectl apply -f k8s/redis/deployment.yaml
kubectl apply -f k8s/redis/service.yaml
```

**Action 4**: Verify Redis deployment:
```bash
kubectl get pods -n fastapi-k8-proto -l app=redis
kubectl logs -n fastapi-k8-proto -l app=redis

# Test Redis connection
kubectl run -it --rm debug --image=redis:7-alpine --restart=Never -n fastapi-k8-proto -- redis-cli -h redis-service ping
```

**Expected outcome**: Redis running and accessible within the cluster.

## Step 5.5: Deploy FastAPI Application

### Understanding Application Deployment Patterns

**Init Containers Pattern**:
Init containers run to completion before app containers start. Perfect for:
- Waiting for dependencies
- Running database migrations
- Downloading configuration files

**Multi-Container Pods**:
While we're using single-container pods here, Kubernetes supports multiple containers per pod for patterns like:
- Sidecar (logging, monitoring)
- Ambassador (proxy)
- Adapter (standardize output)

### AI Agent Instructions:
**Task**: Deploy the FastAPI application with proper initialization.

**Action 1**: Push Docker images to registry (replace with your registry):
```bash
# For Docker Hub
docker tag fastapi-k8-proto-api:latest yourusername/fastapi-k8-proto-api:latest
docker tag fastapi-k8-proto-worker:latest yourusername/fastapi-k8-proto-worker:latest

docker push yourusername/fastapi-k8-proto-api:latest
docker push yourusername/fastapi-k8-proto-worker:latest

# For local development with minikube
eval $(minikube docker-env)
docker build -f docker/Dockerfile.api -t fastapi-k8-proto-api:latest .
docker build -f docker/Dockerfile.worker -t fastapi-k8-proto-worker:latest .
```

**Action 2**: Create `k8s/api/deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi
  namespace: fastapi-k8-proto
spec:
  replicas: 3  # Run 3 instances for high availability
  selector:
    matchLabels:
      app: fastapi
  template:
    metadata:
      labels:
        app: fastapi
    spec:
      # Init containers run sequentially before main containers
      initContainers:
      # Wait for PostgreSQL to be ready
      - name: wait-for-postgres
        image: busybox:1.35
        command: ['sh', '-c', 'until nc -z postgres-service 5432; do echo waiting for postgres; sleep 2; done']
      # Run database migrations
      - name: run-migrations
        image: your-registry/fastapi-k8-proto-api:latest  # Update with your registry
        command: ['alembic', 'upgrade', 'head']
        envFrom:
        - configMapRef:
            name: app-config
        - secretRef:
            name: app-secrets
      containers:
      - name: fastapi
        image: your-registry/fastapi-k8-proto-api:latest  # Update with your registry
        # For minikube local images, add:
        # imagePullPolicy: Never
        ports:
        - containerPort: 8000
        # Load all environment variables from ConfigMap and Secret
        envFrom:
        - configMapRef:
            name: app-config
        - secretRef:
            name: app-secrets
        # Health checks
        livenessProbe:
          httpGet:
            path: /api/v1/health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /api/v1/health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          successThreshold: 1
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

**Probe Configuration Explained**:
- `initialDelaySeconds`: Wait before first check
- `periodSeconds`: How often to check
- `timeoutSeconds`: Timeout for each check
- `failureThreshold`: Failures before taking action
- `successThreshold`: Successes to be considered ready

**Action 3**: Create `k8s/api/service.yaml`:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: fastapi-service
  namespace: fastapi-k8-proto
spec:
  selector:
    app: fastapi
  ports:
  - port: 80         # Service port (what other pods use)
    targetPort: 8000 # Container port
    protocol: TCP
    name: http       # Named port for better documentation
  type: LoadBalancer # Creates external load balancer
  # For production, consider using Ingress instead
```

**Action 4**: Deploy FastAPI:
```bash
kubectl apply -f k8s/api/deployment.yaml
kubectl apply -f k8s/api/service.yaml
```

**Action 5**: Verify API deployment:
```bash
# Watch pods come up
kubectl get pods -n fastapi-k8-proto -l app=fastapi -w

# Check deployment status
kubectl rollout status deployment/fastapi -n fastapi-k8-proto

# View logs from all API pods
kubectl logs -n fastapi-k8-proto -l app=fastapi --tail=50

# Describe a pod for detailed info
kubectl describe pod -n fastapi-k8-proto -l app=fastapi
```

**Expected outcome**: FastAPI pods running and service exposed.

## Step 5.6: Deploy Celery Workers

### Understanding Worker Deployment
Workers are stateless and can be scaled horizontally. They pull jobs from Redis and process them independently.

### AI Agent Instructions:
**Task**: Deploy Celery workers for job processing.

**Action 1**: Create `k8s/workers/deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
  namespace: fastapi-k8-proto
spec:
  replicas: 2  # Start with 2 workers
  selector:
    matchLabels:
      app: celery-worker
  template:
    metadata:
      labels:
        app: celery-worker
    spec:
      containers:
      - name: worker
        image: your-registry/fastapi-k8-proto-worker:latest  # Update with your registry
        envFrom:
        - configMapRef:
            name: app-config
        - secretRef:
            name: app-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        # Celery-specific health check
        livenessProbe:
          exec:
            command:
            - celery
            - -A
            - app.workers.celery_app
            - inspect
            - ping
          initialDelaySeconds: 30
          periodSeconds: 60
          timeoutSeconds: 10
```

**Worker Considerations**:
- No service needed (workers don't receive network traffic)
- Can scale independently from API
- Resource limits prevent memory leaks from affecting other pods

**Action 2**: Deploy workers:
```bash
kubectl apply -f k8s/workers/deployment.yaml
```

**Action 3**: Deploy Flower for monitoring (optional):
```yaml
# Create k8s/workers/flower-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flower
  namespace: fastapi-k8-proto
spec:
  replicas: 1
  selector:
    matchLabels:
      app: flower
  template:
    metadata:
      labels:
        app: flower
    spec:
      containers:
      - name: flower
        image: your-registry/fastapi-k8-proto-worker:latest
        command: ["celery", "-A", "app.workers.celery_app", "flower", "--port=5555"]
        ports:
        - containerPort: 5555
        envFrom:
        - configMapRef:
            name: app-config
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
---
apiVersion: v1
kind: Service
metadata:
  name: flower-service
  namespace: fastapi-k8-proto
spec:
  selector:
    app: flower
  ports:
  - port: 5555
    targetPort: 5555
  type: LoadBalancer  # Or ClusterIP with port-forward
```

**Action 4**: Apply Flower deployment:
```bash
kubectl apply -f k8s/workers/flower-deployment.yaml
```

**Expected outcome**: Celery workers running and processing jobs.

## Step 5.7: Verify Complete Deployment

### Understanding Kubernetes Networking
Kubernetes networking follows these principles:
1. Every pod gets its own IP address
2. Pods can communicate without NAT
3. Services provide stable endpoints for pod groups

**DNS in Kubernetes**:
- Service DNS: `<service>.<namespace>.svc.cluster.local`
- Pod DNS: `<pod-ip>.<namespace>.pod.cluster.local`

### AI Agent Instructions:
**Task**: Verify all components are working together.

**Action 1**: Check all pods are running:
```bash
kubectl get pods -n fastapi-k8-proto

# Should see something like:
# NAME                            READY   STATUS    RESTARTS   AGE
# celery-worker-5f7b8c9d4-8xnzk   1/1     Running   0          2m
# celery-worker-5f7b8c9d4-p9vxm   1/1     Running   0          2m
# fastapi-7d8b9c6d5-4xlmn         1/1     Running   0          3m
# fastapi-7d8b9c6d5-9kpqr         1/1     Running   0          3m
# fastapi-7d8b9c6d5-hs7wx         1/1     Running   0          3m
# postgres-6f9b8c7d4-2njkl        1/1     Running   0          5m
# redis-8c9d7e6f5-7mwxp           1/1     Running   0          4m
```

**Action 2**: Check services:
```bash
kubectl get services -n fastapi-k8-proto

# Should see:
# NAME               TYPE           CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
# fastapi-service    LoadBalancer   10.96.10.100    <pending>     80:30080/TCP   3m
# postgres-service   ClusterIP      10.96.20.200    <none>        5432/TCP       5m
# redis-service      ClusterIP      10.96.30.300    <none>        6379/TCP       4m
```

**Action 3**: Get API endpoint:
```bash
# For LoadBalancer service (cloud providers)
kubectl get service fastapi-service -n fastapi-k8-proto -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# For minikube
minikube service fastapi-service -n fastapi-k8-proto --url

# For port-forwarding (works everywhere)
kubectl port-forward -n fastapi-k8-proto svc/fastapi-service 8000:80
```

**Action 4**: Test the API:
```bash
# Replace with your actual endpoint
API_URL="http://localhost:8000"  # If using port-forward

# Test health
curl $API_URL/api/v1/health

# Create a job
curl -X POST $API_URL/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"name": "K8s Test Job", "description": "Testing on Kubernetes"}'

# Check job status
curl $API_URL/api/v1/jobs
```

**Action 5**: Check worker logs:
```bash
# View logs from all workers
kubectl logs -n fastapi-k8-proto -l app=celery-worker --tail=50

# Follow logs in real-time
kubectl logs -n fastapi-k8-proto -l app=celery-worker -f

# View logs from a specific pod
kubectl logs -n fastapi-k8-proto celery-worker-5f7b8c9d4-8xnzk
```

**Expected outcome**: 
- All pods running
- API accessible
- Jobs being processed by workers

## Step 5.8: Create Management Scripts

### Kubernetes Best Practices for Operations

**1. Use Labels Consistently**:
```yaml
metadata:
  labels:
    app: myapp
    component: backend
    version: v1.0
    environment: production
```

**2. Resource Naming Conventions**:
- Use lowercase
- Separate words with hyphens
- Be descriptive but concise

**3. Declarative vs Imperative**:
- Declarative (preferred): `kubectl apply -f manifest.yaml`
- Imperative: `kubectl create deployment myapp --image=myimage`

### AI Agent Instructions:
**Task**: Create scripts for easier Kubernetes management.

**Action 1**: Create `scripts/k8s-deploy.sh`:
```bash
#!/bin/bash
set -e

NAMESPACE="fastapi-k8-proto"
REGISTRY="${DOCKER_REGISTRY:-your-registry}"
VERSION="${VERSION:-latest}"

echo "Deploying to Kubernetes..."

# Create namespace if it doesn't exist
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Apply configurations
echo "Applying configurations..."
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml

# Deploy PostgreSQL
echo "Deploying PostgreSQL..."
kubectl apply -f k8s/postgres/

# Wait for PostgreSQL
kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=300s

# Deploy Redis
echo "Deploying Redis..."
kubectl apply -f k8s/redis/

# Wait for Redis
kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=300s

# Deploy API
echo "Deploying FastAPI..."
kubectl apply -f k8s/api/

# Deploy Workers
echo "Deploying Celery workers..."
kubectl apply -f k8s/workers/

echo "Deployment complete!"
echo "Checking pod status..."
kubectl get pods -n $NAMESPACE
```

**Script Features**:
- Idempotent (safe to run multiple times)
- Waits for dependencies
- Provides feedback

**Action 2**: Create `scripts/k8s-status.sh`:
```bash
#!/bin/bash

NAMESPACE="fastapi-k8-proto"

echo "=== Pods ==="
kubectl get pods -n $NAMESPACE -o wide

echo -e "\n=== Services ==="
kubectl get services -n $NAMESPACE

echo -e "\n=== Deployments ==="
kubectl get deployments -n $NAMESPACE

echo -e "\n=== PVCs ==="
kubectl get pvc -n $NAMESPACE

echo -e "\n=== ConfigMaps ==="
kubectl get configmap -n $NAMESPACE

echo -e "\n=== Secrets ==="
kubectl get secrets -n $NAMESPACE

echo -e "\n=== API Endpoint ==="
kubectl get service fastapi-service -n $NAMESPACE
```

**Action 3**: Create `scripts/k8s-logs.sh`:
```bash
#!/bin/bash

NAMESPACE="fastapi-k8-proto"
APP="${1:-fastapi}"
TAIL="${2:-100}"

echo "Showing logs for app: $APP (last $TAIL lines)"
echo "Press Ctrl+C to stop following logs"
echo "----------------------------------------"

kubectl logs -n $NAMESPACE -l app=$APP --tail=$TAIL -f --timestamps=true
```

**Action 4**: Create `scripts/k8s-debug.sh`:
```bash
#!/bin/bash

NAMESPACE="fastapi-k8-proto"

echo "=== Debugging Kubernetes Deployment ==="

echo -e "\n1. Checking pod status..."
kubectl get pods -n $NAMESPACE -o wide

echo -e "\n2. Checking recent events..."
kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -20

echo -e "\n3. Checking resource usage..."
kubectl top pods -n $NAMESPACE

echo -e "\n4. Checking pod descriptions for errors..."
for pod in $(kubectl get pods -n $NAMESPACE -o name | grep -v Running); do
    echo -e "\nDescribing $pod:"
    kubectl describe $pod -n $NAMESPACE | grep -A 10 "Events:"
done
```

**Action 5**: Make scripts executable:
```bash
chmod +x scripts/k8s-*.sh
```

**Expected outcome**: Management scripts created for easier operations.

## Phase 5 Completion Checklist

- [ ] Kubernetes namespace created
- [ ] ConfigMap and Secrets deployed
- [ ] PostgreSQL deployed with persistent storage
- [ ] Redis deployed and running
- [ ] FastAPI application deployed
- [ ] Database migrations completed
- [ ] Celery workers deployed
- [ ] All pods running successfully
- [ ] Services accessible
- [ ] API endpoints tested
- [ ] Jobs processing correctly
- [ ] Management scripts created

## Troubleshooting

### Common Issues and Solutions:

1. **ImagePullBackOff**:
```bash
# Check the exact error
kubectl describe pod <pod-name> -n fastapi-k8-proto

# Common causes:
# - Wrong image name/tag
# - Private registry needs authentication
# - Image doesn't exist

# For private registries, create a pull secret:
kubectl create secret docker-registry regcred \
  --docker-server=<your-registry-server> \
  --docker-username=<your-name> \
  --docker-password=<your-pword> \
  --docker-email=<your-email> \
  -n fastapi-k8-proto

# Then add to deployment:
# spec:
#   imagePullSecrets:
#   - name: regcred
```

2. **CrashLoopBackOff**:
```bash
# View logs from the crashed container
kubectl logs <pod-name> -n fastapi-k8-proto --previous

# Common causes:
# - Application errors
# - Missing environment variables
# - Incorrect command/entrypoint
# - Resource limits too low
```

3. **Service not accessible**:
```bash
# Check if pods have correct labels
kubectl get pods -n fastapi-k8-proto --show-labels

# Check service endpoints
kubectl get endpoints -n fastapi-k8-proto

# Test service from within cluster
kubectl run -it --rm debug --image=busybox --restart=Never -n fastapi-k8-proto -- wget -qO- http://fastapi-service/api/v1/health
```

4. **Database connection errors**:
```bash
# Test DNS resolution
kubectl run -it --rm debug --image=busybox --restart=Never -n fastapi-k8-proto -- nslookup postgres-service

# Test connectivity
kubectl run -it --rm debug --image=postgres:15-alpine --restart=Never -n fastapi-k8-proto -- psql -h postgres-service -U postgres

# Check if services are in the same namespace
kubectl get svc -A | grep -E "(postgres|redis|fastapi)"
```

## Monitoring Commands

### Essential kubectl Commands:

```bash
# Watch resources in real-time
kubectl get pods -n fastapi-k8-proto -w

# Get detailed information
kubectl describe pod <pod-name> -n fastapi-k8-proto
kubectl describe deployment fastapi -n fastapi-k8-proto
kubectl describe service fastapi-service -n fastapi-k8-proto

# Execute commands in containers
kubectl exec -it <pod-name> -n fastapi-k8-proto -- /bin/bash
kubectl exec -it <pod-name> -n fastapi-k8-proto -- python -c "import app; print(app.__version__)"

# Copy files to/from pods
kubectl cp local-file.txt <pod-name>:/tmp/file.txt -n fastapi-k8-proto
kubectl cp <pod-name>:/app/logs/app.log ./local-app.log -n fastapi-k8-proto

# Port forwarding for debugging
kubectl port-forward -n fastapi-k8-proto pod/<pod-name> 8000:8000
kubectl port-forward -n fastapi-k8-proto svc/postgres-service 5432:5432

# View resource usage
kubectl top nodes
kubectl top pods -n fastapi-k8-proto

# Get YAML of running resources
kubectl get deployment fastapi -n fastapi-k8-proto -o yaml
kubectl get pod <pod-name> -n fastapi-k8-proto -o yaml
```

### Debugging Workflow:

1. **Check Pod Status**:
```bash
kubectl get pods -n fastapi-k8-proto
# Look for: Running, Pending, CrashLoopBackOff, ImagePullBackOff
```

2. **Investigate Issues**:
```bash
# For non-running pods
kubectl describe pod <pod-name> -n fastapi-k8-proto
# Look at Events section at the bottom
```

3. **Check Logs**:
```bash
# Current logs
kubectl logs <pod-name> -n fastapi-k8-proto

# Previous container logs (if crashed)
kubectl logs <pod-name> -n fastapi-k8-proto --previous

# Follow logs
kubectl logs <pod-name> -n fastapi-k8-proto -f
```

4. **Resource Issues**:
```bash
# Check resource usage
kubectl top pod <pod-name> -n fastapi-k8-proto

# Check resource limits
kubectl describe pod <pod-name> -n fastapi-k8-proto | grep -A 5 "Limits:"
```

## Advanced Kubernetes Concepts

### 1. **Rolling Updates**:
```bash
# Update image
kubectl set image deployment/fastapi fastapi=your-registry/fastapi-k8-proto-api:v2 -n fastapi-k8-proto

# Check rollout status
kubectl rollout status deployment/fastapi -n fastapi-k8-proto

# Rollback if needed
kubectl rollout undo deployment/fastapi -n fastapi-k8-proto
```

### 2. **Scaling**:
```bash
# Manual scaling
kubectl scale deployment/celery-worker --replicas=5 -n fastapi-k8-proto

# Check scaling
kubectl get deployment celery-worker -n fastapi-k8-proto
```

### 3. **Resource Quotas**:
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-quota
  namespace: fastapi-k8-proto
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 10Gi
    limits.cpu: "20"
    limits.memory: 20Gi
    persistentvolumeclaims: "5"
```

### 4. **Network Policies**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-netpol
  namespace: fastapi-k8-proto
spec:
  podSelector:
    matchLabels:
      app: fastapi
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector: {}  # Allow from all pods in namespace
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
```

## Next Steps
Once Phase 5 is complete and the application is running on Kubernetes, proceed to Phase 6 for auto-scaling configuration. 