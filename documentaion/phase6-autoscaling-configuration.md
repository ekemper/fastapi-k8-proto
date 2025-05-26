# Phase 6: Auto-scaling Configuration

## Overview
This phase implements Horizontal Pod Autoscaler (HPA) for dynamic scaling based on CPU, memory, and custom metrics from the job queue, enabling the system to automatically scale worker processes based on workload.

## Auto-scaling Fundamentals

### What is Auto-scaling?
Auto-scaling is the ability to automatically adjust the number of compute resources (in Kubernetes, this means pods) based on the actual workload. This ensures optimal resource utilization and application performance.

### Types of Scaling in Kubernetes

#### 1. **Horizontal Pod Autoscaler (HPA)**
Scales the number of pod replicas:
```
Low Load:  [Pod1] [Pod2]
High Load: [Pod1] [Pod2] [Pod3] [Pod4] [Pod5]
```

#### 2. **Vertical Pod Autoscaler (VPA)**
Adjusts resource requests/limits for pods:
```
Low Load:  [Pod: CPU=100m, Memory=128Mi]
High Load: [Pod: CPU=500m, Memory=512Mi]
```

#### 3. **Cluster Autoscaler**
Adds or removes nodes from the cluster:
```
Low Load:  [Node1] [Node2]
High Load: [Node1] [Node2] [Node3] [Node4]
```

### How HPA Works

```
┌─────────────────────────────────────────────────────────────┐
│                    HPA Architecture                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐     ┌──────────────┐    ┌──────────────┐ │
│  │   Metrics   │────▶│     HPA      │───▶│  Deployment  │ │
│  │   Server    │     │  Controller  │    │              │ │
│  └─────────────┘     └──────────────┘    └──────────────┘ │
│         ▲                    │                    │         │
│         │                    │                    ▼         │
│  ┌─────────────┐            │            ┌──────────────┐ │
│  │    Pods     │            │            │   ReplicaSet │ │
│  │  (Metrics)  │            │            │              │ │
│  └─────────────┘            ▼            └──────────────┘ │
│                     ┌──────────────┐                       │
│                     │   Decision   │                       │
│                     │    Logic     │                       │
│                     └──────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

**HPA Control Loop**:
1. **Fetch Metrics**: HPA queries metrics every 15 seconds (default)
2. **Calculate Desired Replicas**: Uses the formula below
3. **Scale Decision**: Compares current vs desired replicas
4. **Apply Scaling**: Updates the deployment/replicaset

**Scaling Formula**:
```
desiredReplicas = ceil[currentReplicas * (currentMetricValue / targetMetricValue)]
```

Example:
- Current replicas: 2
- Current CPU: 80%
- Target CPU: 50%
- Desired replicas: ceil[2 * (80/50)] = ceil[3.2] = 4

### Metrics Types

#### 1. **Resource Metrics**
Built-in metrics for CPU and memory:
```yaml
metrics:
- type: Resource
  resource:
    name: cpu
    target:
      type: Utilization
      averageUtilization: 70
```

#### 2. **Pods Metrics**
Metrics exposed by the pods themselves:
```yaml
metrics:
- type: Pods
  pods:
    metric:
      name: requests_per_second
    target:
      type: AverageValue
      averageValue: "1000"
```

#### 3. **Object Metrics**
Metrics from other Kubernetes objects:
```yaml
metrics:
- type: Object
  object:
    metric:
      name: queue_length
    describedObject:
      apiVersion: v1
      kind: Service
      name: redis-service
    target:
      type: Value
      value: "30"
```

#### 4. **External Metrics**
Metrics from external systems:
```yaml
metrics:
- type: External
  external:
    metric:
      name: queue_messages_ready
      selector:
        matchLabels:
          queue: "jobs"
    target:
      type: AverageValue
      averageValue: "5"
```

### Scaling Behaviors and Policies

**Stabilization Windows**: Prevent flapping
```yaml
behavior:
  scaleDown:
    stabilizationWindowSeconds: 300  # Wait 5 minutes before scaling down
  scaleUp:
    stabilizationWindowSeconds: 60   # Wait 1 minute before scaling up
```

**Scaling Policies**: Control how fast to scale
```yaml
behavior:
  scaleUp:
    policies:
    - type: Percent
      value: 100        # Double the pods
      periodSeconds: 60 # Every minute
    - type: Pods
      value: 4          # Add 4 pods
      periodSeconds: 60 # Every minute
    selectPolicy: Max   # Use the policy that scales most
```

## Prerequisites
- Phases 1-5 completed successfully
- Application running on Kubernetes
- Metrics Server installed in the cluster
- Prometheus (optional, for custom metrics)

## Step 6.1: Install Metrics Server

### Understanding Metrics Server
Metrics Server is a cluster-wide aggregator of resource usage data. It collects metrics from the Kubelet on each node and provides them via the Metrics API.

**Architecture**:
```
┌─────────────────────────────────────────────────────┐
│                  Metrics Flow                        │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Node 1           Node 2           Node 3           │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐      │
│  │ Kubelet │     │ Kubelet │     │ Kubelet │      │
│  │ (cAdvisor)    │ (cAdvisor)    │ (cAdvisor)     │
│  └────┬────┘     └────┬────┘     └────┬────┘      │
│       │               │               │             │
│       └───────────────┴───────────────┘             │
│                       │                             │
│                       ▼                             │
│              ┌─────────────────┐                   │
│              │ Metrics Server  │                   │
│              │  (Aggregator)   │                   │
│              └────────┬────────┘                   │
│                       │                             │
│                       ▼                             │
│              ┌─────────────────┐                   │
│              │  Metrics API    │                   │
│              │ /apis/metrics.k8s.io                │
│              └─────────────────┘                   │
└─────────────────────────────────────────────────────┘
```

### AI Agent Instructions:
**Task**: Install Metrics Server for resource-based autoscaling.

**Action 1**: Check if Metrics Server is already installed:
```bash
kubectl get deployment metrics-server -n kube-system
```

**Action 2**: If not installed, install Metrics Server:
```bash
# For standard clusters
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# For minikube
minikube addons enable metrics-server

# For kind or other local clusters, you may need to add insecure TLS
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl patch deployment metrics-server -n kube-system --type='json' -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'
```

**Why the insecure TLS flag?**
Local clusters often use self-signed certificates. The `--kubelet-insecure-tls` flag allows Metrics Server to collect metrics without verifying the Kubelet's certificate.

**Action 3**: Verify Metrics Server is running:
```bash
kubectl get pods -n kube-system | grep metrics-server

# Wait for it to be ready
kubectl wait --for=condition=ready pod -l k8s-app=metrics-server -n kube-system --timeout=300s

# Test metrics availability
kubectl top nodes
kubectl top pods -n fastapi-k8-proto
```

**Understanding the Output**:
```bash
# kubectl top nodes shows:
NAME       CPU(cores)   CPU%   MEMORY(bytes)   MEMORY%
minikube   250m         12%    1024Mi          25%

# kubectl top pods shows:
NAME                          CPU(cores)   MEMORY(bytes)
fastapi-7d8b9c6d5-4xlmn      50m          128Mi
celery-worker-5f7b8c9d4-8x   100m         256Mi
```

**Expected outcome**: Metrics Server running and providing resource metrics.

## Step 6.2: Create Basic HPA for Workers

### Understanding HPA Configuration
The HPA continuously monitors metrics and adjusts the number of replicas to maintain the target metric values.

**Key Concepts**:
- **Target Metrics**: What you want to maintain (e.g., 70% CPU)
- **Min/Max Replicas**: Boundaries for scaling
- **Scaling Behavior**: How aggressively to scale

### AI Agent Instructions:
**Task**: Create Horizontal Pod Autoscaler for Celery workers based on CPU and memory.

**Action 1**: Create `k8s/workers/hpa.yaml`:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: celery-worker-hpa
  namespace: fastapi-k8-proto
spec:
  # Target deployment to scale
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: celery-worker
  # Scaling boundaries
  minReplicas: 2   # Never go below 2 pods
  maxReplicas: 10  # Never exceed 10 pods
  # Metrics to monitor
  metrics:
  # CPU-based scaling
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70  # Target 70% CPU usage
  # Memory-based scaling
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80  # Target 80% memory usage
  # Scaling behavior configuration
  behavior:
    scaleDown:
      # Wait 5 minutes before scaling down to avoid flapping
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50         # Remove at most 50% of pods
        periodSeconds: 60 # Every minute
    scaleUp:
      # Wait 1 minute before scaling up for faster response
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100        # At most double the pods
        periodSeconds: 60 # Every minute
      - type: Pods
        value: 2          # Or add 2 pods
        periodSeconds: 60 # Every minute
```

**Understanding the Configuration**:

1. **Multiple Metrics**: HPA will scale up if ANY metric exceeds its target
2. **averageUtilization**: Percentage of the resource request
3. **Scaling Policies**: 
   - Scale up: Max of (100% increase OR 2 pods)
   - Scale down: Max 50% decrease

**Action 2**: Apply the HPA:
```bash
kubectl apply -f k8s/workers/hpa.yaml
```

**Action 3**: Verify HPA is created:
```bash
# View HPA status
kubectl get hpa -n fastapi-k8-proto

# Expected output:
# NAME                REFERENCE                  TARGETS           MINPODS   MAXPODS   REPLICAS
# celery-worker-hpa   Deployment/celery-worker   20%/70%, 30%/80%  2         10        2

# Get detailed HPA information
kubectl describe hpa celery-worker-hpa -n fastapi-k8-proto
```

**Understanding HPA Status**:
- `TARGETS`: Current/Target for each metric
- `REPLICAS`: Current number of pods
- `20%/70%`: Current CPU is 20%, target is 70%

**Expected outcome**: HPA created and monitoring worker pods.

## Step 6.3: Create HPA for API Deployment

### Different Scaling Strategies
API pods typically scale based on:
- **Request rate**: More requests = more pods
- **Response time**: Slower responses = more pods
- **CPU/Memory**: Resource utilization

### AI Agent Instructions:
**Task**: Create HPA for FastAPI deployment.

**Action 1**: Create `k8s/api/hpa.yaml`:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: fastapi-hpa
  namespace: fastapi-k8-proto
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: fastapi
  minReplicas: 3   # Minimum for high availability
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 75  # Higher threshold for APIs
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 85
  behavior:
    scaleDown:
      # Slower scale-down for APIs to maintain availability
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 25         # Remove at most 25% of pods
        periodSeconds: 60
    scaleUp:
      # Faster scale-up for responsiveness
      stabilizationWindowSeconds: 30
      policies:
      - type: Percent
        value: 50         # Add up to 50% more pods
        periodSeconds: 30 # Every 30 seconds
```

**API Scaling Considerations**:
1. **Higher minimum replicas**: Ensures availability
2. **Conservative scale-down**: Prevents dropping too many pods
3. **Aggressive scale-up**: Responds quickly to load spikes

**Action 2**: Apply the API HPA:
```bash
kubectl apply -f k8s/api/hpa.yaml
```

**Action 3**: Verify both HPAs:
```bash
kubectl get hpa -n fastapi-k8-proto

# Monitor HPA decisions
kubectl get hpa -n fastapi-k8-proto -w
```

**Expected outcome**: Both HPAs active and monitoring their respective deployments.

## Step 6.4: Deploy Celery Metrics Exporter

### Understanding Custom Metrics
While CPU and memory are useful, application-specific metrics often provide better scaling signals:
- **Queue length**: Scale based on pending jobs
- **Processing time**: Scale if jobs take too long
- **Error rate**: Scale up if errors increase

### Metrics Pipeline
```
Celery → Redis → Celery Exporter → Prometheus → Prometheus Adapter → HPA
```

### AI Agent Instructions:
**Task**: Deploy Celery exporter for queue-based metrics.

**Action 1**: Create `k8s/workers/celery-metrics-exporter.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-exporter
  namespace: fastapi-k8-proto
  labels:
    app: celery-exporter
spec:
  replicas: 1
  selector:
    matchLabels:
      app: celery-exporter
  template:
    metadata:
      labels:
        app: celery-exporter
      annotations:
        # Prometheus scraping configuration
        prometheus.io/scrape: "true"
        prometheus.io/port: "9540"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: exporter
        image: ovalmoney/celery-exporter:latest
        ports:
        - containerPort: 9540
          name: metrics
        env:
        - name: CELERY_BROKER_URL
          value: "redis://redis-service:6379/0"
        - name: CELERY_RESULT_BACKEND
          value: "redis://redis-service:6379/0"
        # Optional: Configure specific queues to monitor
        - name: CE_ACCEPT_CONTENT
          value: "json"
        - name: CE_ENABLE_EVENTS
          value: "true"
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
  name: celery-exporter-service
  namespace: fastapi-k8-proto
  labels:
    app: celery-exporter
spec:
  selector:
    app: celery-exporter
  ports:
  - port: 9540
    targetPort: 9540
    name: metrics
```

**Metrics Exposed by Celery Exporter**:
- `celery_task_sent_total`: Total tasks sent
- `celery_task_received_total`: Total tasks received
- `celery_task_started_total`: Total tasks started
- `celery_task_succeeded_total`: Total successful tasks
- `celery_task_failed_total`: Total failed tasks
- `celery_task_runtime_seconds`: Task execution time
- `celery_queue_length`: Current queue length

**Action 2**: Deploy the exporter:
```bash
kubectl apply -f k8s/workers/celery-metrics-exporter.yaml
```

**Action 3**: Verify exporter is running:
```bash
kubectl get pods -n fastapi-k8-proto -l app=celery-exporter
kubectl logs -n fastapi-k8-proto -l app=celery-exporter
```

**Action 4**: Test metrics endpoint:
```bash
# Port forward to test locally
kubectl port-forward -n fastapi-k8-proto svc/celery-exporter-service 9540:9540

# In another terminal, view metrics
curl http://localhost:9540/metrics | grep celery

# Look for metrics like:
# celery_queue_length{queue_name="celery"} 5.0
# celery_task_runtime_seconds_sum{task_name="process_job"} 123.45
```

**Expected outcome**: Celery metrics exporter running and providing queue metrics.

## Step 6.5: Install Prometheus Adapter (Optional)

### Understanding the Custom Metrics Pipeline
To use custom metrics for HPA, we need:
1. **Metrics Source**: Celery Exporter (done)
2. **Metrics Storage**: Prometheus
3. **Metrics API**: Prometheus Adapter
4. **HPA**: Consumes metrics via Custom Metrics API

```
┌────────────────────────────────────────────────────────┐
│              Custom Metrics Architecture                │
├────────────────────────────────────────────────────────┤
│                                                         │
│  Celery         Celery          Prometheus             │
│  Workers   →    Exporter   →    Server                 │
│                                     │                   │
│                                     ▼                   │
│                            Prometheus Adapter           │
│                                     │                   │
│                                     ▼                   │
│                          Custom Metrics API             │
│                       /apis/custom.metrics.k8s.io       │
│                                     │                   │
│                                     ▼                   │
│                                   HPA                   │
└────────────────────────────────────────────────────────┘
```

### AI Agent Instructions:
**Task**: Install Prometheus Adapter for custom metrics-based scaling.

**Action 1**: Create `k8s/monitoring/prometheus-adapter-values.yaml`:
```yaml
# Prometheus connection
prometheus:
  url: http://prometheus-server.monitoring.svc.cluster.local
  port: 80

# Rules to expose metrics to HPA
rules:
  custom:
  # Expose queue length metric
  - seriesQuery: 'celery_queue_length{namespace="fastapi-k8-proto"}'
    resources:
      overrides:
        namespace: {resource: "namespace"}
    name:
      matches: "^celery_queue_length"
      as: "celery_queue_length"
    metricsQuery: 'avg_over_time(celery_queue_length{namespace="fastapi-k8-proto"}[1m])'
  
  # Expose pending tasks metric
  - seriesQuery: 'celery_tasks_pending{namespace="fastapi-k8-proto"}'
    resources:
      overrides:
        namespace: {resource: "namespace"}
    name:
      matches: "^celery_tasks_pending"
      as: "celery_tasks_pending"
    metricsQuery: 'avg_over_time(celery_tasks_pending{namespace="fastapi-k8-proto"}[1m])'
  
  # Expose task processing rate
  - seriesQuery: 'rate(celery_task_succeeded_total{namespace="fastapi-k8-proto"}[5m])'
    resources:
      overrides:
        namespace: {resource: "namespace"}
    name:
      matches: "^celery_task_succeeded_total"
      as: "celery_tasks_per_second"
    metricsQuery: 'rate(celery_task_succeeded_total{namespace="fastapi-k8-proto"}[5m])'
```

**Understanding the Rules**:
- `seriesQuery`: Which Prometheus metrics to use
- `resources`: How to map to Kubernetes resources
- `name`: How to expose the metric name
- `metricsQuery`: The actual Prometheus query

**Action 2**: Install Prometheus Adapter using Helm:
```bash
# Add Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install adapter
helm install prometheus-adapter prometheus-community/prometheus-adapter \
  -f k8s/monitoring/prometheus-adapter-values.yaml \
  -n monitoring --create-namespace
```

**Note**: This assumes you have Prometheus installed. If not, you can install it with:
```bash
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring
```

**Action 3**: Verify custom metrics are available:
```bash
# Wait a few minutes for metrics to be collected
sleep 180

# List all available custom metrics
kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1" | jq -r '.resources[].name'

# Check specific metric
kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1/namespaces/fastapi-k8-proto/metrics/celery_queue_length" | jq .
```

**Expected output**:
```json
{
  "kind": "MetricValueList",
  "apiVersion": "custom.metrics.k8s.io/v1beta1",
  "metadata": {
    "selfLink": "/apis/custom.metrics.k8s.io/v1beta1/namespaces/fastapi-k8-proto/metrics/celery_queue_length"
  },
  "items": [
    {
      "describedObject": {
        "kind": "Service",
        "namespace": "fastapi-k8-proto",
        "name": "redis-service"
      },
      "metricName": "celery_queue_length",
      "timestamp": "2023-12-01T10:00:00Z",
      "value": "15"
    }
  ]
}
```

**Expected outcome**: Custom metrics available for HPA use.

## Step 6.6: Create Advanced HPA with Custom Metrics

### Combining Multiple Metrics
Advanced HPA configurations can use multiple metrics for more intelligent scaling decisions:
- Scale up if CPU > 70% OR queue > 30 jobs
- Scale down only if CPU < 30% AND queue < 5 jobs

### AI Agent Instructions:
**Task**: Create HPA that scales based on queue length.

**Action 1**: Create `k8s/workers/hpa-custom.yaml`:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: celery-worker-hpa-custom
  namespace: fastapi-k8-proto
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: celery-worker
  minReplicas: 2
  maxReplicas: 20  # Higher max for queue-based scaling
  metrics:
  # CPU-based scaling (baseline)
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  # Memory-based scaling (safety)
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  # Queue length-based scaling (primary driver)
  - type: Object
    object:
      metric:
        name: celery_queue_length
      describedObject:
        apiVersion: v1
        kind: Service
        name: redis-service
      target:
        type: Value
        value: "30"  # Scale up if queue length > 30
  # Task processing rate (optional)
  - type: Object
    object:
      metric:
        name: celery_tasks_per_second
      describedObject:
        apiVersion: v1
        kind: Service
        name: celery-exporter-service
      target:
        type: AverageValue
        averageValue: "10"  # Each worker should process ~10 tasks/second
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      # Conservative scale-down
      - type: Percent
        value: 50
        periodSeconds: 60
      - type: Pods
        value: 1
        periodSeconds: 120
      selectPolicy: Min  # Use the most conservative policy
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      # Aggressive scale-up for queue spikes
      - type: Percent
        value: 100
        periodSeconds: 30
      - type: Pods
        value: 3
        periodSeconds: 60
      selectPolicy: Max  # Use the most aggressive policy
```

**Understanding Advanced HPA**:

1. **Multiple Metric Types**:
   - Resource metrics: CPU/Memory baseline
   - Object metrics: Queue length from Redis
   - Calculated metrics: Tasks per second

2. **Scaling Logic**:
   - Scale UP if ANY metric exceeds target
   - Scale DOWN only if ALL metrics are below target

3. **Select Policies**:
   - `Min`: Choose the policy that changes fewest pods
   - `Max`: Choose the policy that changes most pods

**Action 2**: Apply the custom HPA (only if Prometheus Adapter is installed):
```bash
# First delete the basic HPA
kubectl delete hpa celery-worker-hpa -n fastapi-k8-proto

# Apply the custom HPA
kubectl apply -f k8s/workers/hpa-custom.yaml

# Verify it's working
kubectl get hpa celery-worker-hpa-custom -n fastapi-k8-proto
```

**Expected outcome**: Advanced HPA configured with multiple metrics.

## Step 6.7: Test Auto-scaling

### Load Testing Strategy
To properly test auto-scaling, we need to:
1. Generate consistent load
2. Monitor scaling behavior
3. Verify performance under load
4. Test scale-down after load

### AI Agent Instructions:
**Task**: Generate load to test auto-scaling behavior.

**Action 1**: Create a load generation script `scripts/generate-load.sh`:
```bash
#!/bin/bash
set -e

API_URL="${1:-http://localhost:8000}"
NUM_JOBS="${2:-100}"
CONCURRENT="${3:-10}"

echo "=== Load Test Configuration ==="
echo "API URL: $API_URL"
echo "Total Jobs: $NUM_JOBS"
echo "Concurrent Requests: $CONCURRENT"
echo "==============================="

# Function to create a job
create_job() {
    local job_num=$1
    local response=$(curl -s -X POST $API_URL/api/v1/jobs \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"Load Test Job $job_num\", \"description\": \"Auto-scaling test\"}")
    
    if [ $? -eq 0 ]; then
        echo -n "."
    else
        echo -n "!"
    fi
}

# Export function for parallel execution
export -f create_job
export API_URL

echo "Starting load generation..."
start_time=$(date +%s)

# Generate jobs in parallel
seq 1 $NUM_JOBS | xargs -P $CONCURRENT -I {} bash -c 'create_job {}'

end_time=$(date +%s)
duration=$((end_time - start_time))

echo -e "\n\n=== Load Test Results ==="
echo "Duration: $duration seconds"
echo "Rate: $((NUM_JOBS / duration)) jobs/second"
echo "========================="

echo -e "\nChecking HPA status..."
kubectl get hpa -n fastapi-k8-proto

echo -e "\nChecking pod count..."
kubectl get pods -n fastapi-k8-proto -l app=celery-worker --no-headers | wc -l
```

**Action 2**: Make the script executable:
```bash
chmod +x scripts/generate-load.sh
```

**Action 3**: Port forward to access the API:
```bash
kubectl port-forward -n fastapi-k8-proto svc/fastapi-service 8000:80
```

**Action 4**: Run the load test:
```bash
# Generate 100 jobs with 10 concurrent connections
./scripts/generate-load.sh http://localhost:8000 100 10

# For heavier load
./scripts/generate-load.sh http://localhost:8000 500 20
```

**Action 5**: Monitor scaling behavior:
```bash
# Watch HPA status (in a separate terminal)
kubectl get hpa -n fastapi-k8-proto -w

# Example output:
# NAME                      REFERENCE              TARGETS                     MINPODS   MAXPODS   REPLICAS
# celery-worker-hpa-custom  Deployment/celery-worker  30%/70%, 40%/80%, 45/30   2         20        2
# celery-worker-hpa-custom  Deployment/celery-worker  30%/70%, 40%/80%, 45/30   2         20        4  ← Scaling up!
# celery-worker-hpa-custom  Deployment/celery-worker  50%/70%, 60%/80%, 60/30   2         20        6  ← More scaling!

# Watch pods (in another terminal)
kubectl get pods -n fastapi-k8-proto -l app=celery-worker -w

# Check metrics
kubectl top pods -n fastapi-k8-proto
```

**Understanding Scaling Events**:
1. **Initial State**: 2 workers, low metrics
2. **Load Applied**: Queue length increases
3. **HPA Reacts**: Calculates desired replicas
4. **Pods Created**: New workers start
5. **Load Distributed**: Metrics stabilize
6. **Load Removed**: Queue empties
7. **Scale Down**: After stabilization window

**Expected outcome**: 
- Workers scale up as jobs are created
- HPA shows increased replicas
- Workers scale down after jobs complete

## Step 6.8: Create Monitoring Dashboard

### Observability for Auto-scaling
Effective auto-scaling requires good observability:
- Real-time metrics
- Historical trends
- Scaling events
- Performance impact

### AI Agent Instructions:
**Task**: Create scripts to monitor auto-scaling behavior.

**Action 1**: Create `scripts/monitor-scaling.sh`:
```bash
#!/bin/bash

NAMESPACE="fastapi-k8-proto"
REFRESH_INTERVAL=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

while true; do
    clear
    echo "=== Auto-scaling Monitor ==="
    echo "Time: $(date)"
    echo "Refresh: ${REFRESH_INTERVAL}s"
    echo ""
    
    echo "=== HPA Status ==="
    kubectl get hpa -n $NAMESPACE
    echo ""
    
    echo "=== Pod Count ==="
    API_PODS=$(kubectl get pods -n $NAMESPACE -l app=fastapi --no-headers | wc -l)
    WORKER_PODS=$(kubectl get pods -n $NAMESPACE -l app=celery-worker --no-headers | wc -l)
    
    echo -e "API Pods: ${GREEN}$API_PODS${NC}"
    echo -e "Worker Pods: ${GREEN}$WORKER_PODS${NC}"
    echo ""
    
    echo "=== Resource Usage (Top 10) ==="
    kubectl top pods -n $NAMESPACE | grep -E "(fastapi|celery-worker)" | head -10
    echo ""
    
    echo "=== Queue Metrics ==="
    # If you have access to queue metrics
    QUEUE_LENGTH=$(kubectl exec -n $NAMESPACE deploy/redis -- redis-cli llen celery 2>/dev/null || echo "N/A")
    echo -e "Queue Length: ${YELLOW}$QUEUE_LENGTH${NC}"
    echo ""
    
    echo "=== Recent Scaling Events ==="
    kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | grep -E "(HorizontalPodAutoscaler|Scaled)" | tail -5
    
    echo ""
    echo "Press Ctrl+C to exit"
    sleep $REFRESH_INTERVAL
done
```

**Action 2**: Create `scripts/queue-status.sh`:
```bash
#!/bin/bash

NAMESPACE="fastapi-k8-proto"

echo "=== Celery Queue Status ==="

# Function to get queue info
get_queue_info() {
    kubectl exec -n $NAMESPACE deploy/redis -- redis-cli --raw eval "
        local celery_len = redis.call('llen', 'celery')
        local keys = redis.call('keys', '_kombu.binding.*')
        local queues = {}
        for i, key in ipairs(keys) do
            local queue_name = string.match(key, '_kombu.binding.(.*)')
            if queue_name then
                table.insert(queues, queue_name)
            end
        end
        return 'Queue Length: ' .. celery_len .. '\nKnown Queues: ' .. table.concat(queues, ', ')
    " 0 2>/dev/null
}

# Main monitoring loop
echo "Checking queue status..."
get_queue_info

echo ""
echo "=== Worker Status ==="
kubectl get pods -n $NAMESPACE -l app=celery-worker -o wide

echo ""
echo "=== Active Tasks ==="
# This would require Flower API or Celery inspect
kubectl logs -n $NAMESPACE -l app=celery-worker --tail=20 | grep -E "(Received task|Task .* succeeded)"
```

**Action 3**: Create `scripts/scaling-report.sh`:
```bash
#!/bin/bash

NAMESPACE="fastapi-k8-proto"
DURATION="${1:-1h}"

echo "=== Auto-scaling Report ==="
echo "Duration: $DURATION"
echo "Generated: $(date)"
echo ""

echo "=== Current State ==="
kubectl get hpa -n $NAMESPACE
echo ""

echo "=== Scaling History ==="
kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | grep -E "Scaled (up|down)" | tail -20
echo ""

echo "=== Resource Usage Statistics ==="
echo "Note: This requires Prometheus/Grafana for historical data"
echo "Current usage:"
kubectl top pods -n $NAMESPACE --containers | grep -E "(fastapi|celery-worker)"
echo ""

echo "=== Recommendations ==="
# Analyze current settings
WORKER_HPA=$(kubectl get hpa celery-worker-hpa-custom -n $NAMESPACE -o json 2>/dev/null)
if [ $? -eq 0 ]; then
    MIN_REPLICAS=$(echo $WORKER_HPA | jq '.spec.minReplicas')
    MAX_REPLICAS=$(echo $WORKER_HPA | jq '.spec.maxReplicas')
    
    echo "Current worker scaling: $MIN_REPLICAS-$MAX_REPLICAS replicas"
    
    # Simple recommendations based on events
    SCALE_UP_EVENTS=$(kubectl get events -n $NAMESPACE --field-selector reason=SuccessfulRescale | grep "Scaled up" | wc -l)
    SCALE_DOWN_EVENTS=$(kubectl get events -n $NAMESPACE --field-selector reason=SuccessfulRescale | grep "Scaled down" | wc -l)
    
    if [ $SCALE_UP_EVENTS -gt 10 ]; then
        echo "- Consider increasing minReplicas (frequent scale-ups detected)"
    fi
    
    if [ $SCALE_DOWN_EVENTS -lt 2 ]; then
        echo "- Consider decreasing minReplicas (infrequent scale-downs)"
    fi
fi
```

**Action 4**: Make scripts executable:
```bash
chmod +x scripts/monitor-scaling.sh scripts/queue-status.sh scripts/scaling-report.sh
```

**Expected outcome**: Monitoring scripts created for observing scaling behavior.

## Phase 6 Completion Checklist

- [ ] Metrics Server installed and running
- [ ] Basic HPA created for workers
- [ ] HPA created for API deployment
- [ ] Celery metrics exporter deployed
- [ ] Custom metrics available (optional)
- [ ] Advanced HPA with custom metrics (optional)
- [ ] Load testing performed
- [ ] Auto-scaling verified working
- [ ] Scale-up behavior confirmed
- [ ] Scale-down behavior confirmed
- [ ] Monitoring scripts created

## Troubleshooting

### Common Issues:

1. **HPA shows "unknown" for metrics**:
```bash
# Check metrics server
kubectl get pods -n kube-system | grep metrics-server
kubectl logs -n kube-system -l k8s-app=metrics-server

# Verify resource requests are set
kubectl describe deployment celery-worker -n fastapi-k8-proto | grep -A 5 "Requests:"

# Common fix: Ensure resource requests are defined
# resources:
#   requests:
#     cpu: 100m
#     memory: 128Mi
```

2. **HPA not scaling**:
```bash
# Check HPA events
kubectl describe hpa celery-worker-hpa -n fastapi-k8-proto

# Look for messages like:
# - "failed to get cpu utilization: missing request for cpu"
# - "the HPA was unable to compute the replica count"

# Verify metrics are available
kubectl get --raw /apis/metrics.k8s.io/v1beta1/nodes
kubectl top pods -n fastapi-k8-proto
```

3. **Custom metrics not available**:
```bash
# Check Prometheus Adapter logs
kubectl logs -n monitoring -l app=prometheus-adapter

# Verify Prometheus is scraping metrics
kubectl port-forward -n monitoring svc/prometheus-server 9090:80
# Visit http://localhost:9090 and search for celery_queue_length

# Test custom metrics API
kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1" | jq .
```

4. **Scaling too aggressive or too slow**:
```yaml
# Adjust behavior section in HPA
behavior:
  scaleDown:
    stabilizationWindowSeconds: 600  # Increase for less aggressive
    policies:
    - type: Percent
      value: 10  # Smaller percentage for gradual scale-down
      periodSeconds: 120
  scaleUp:
    stabilizationWindowSeconds: 30  # Decrease for faster response
    policies:
    - type: Pods
      value: 1  # Add one pod at a time
      periodSeconds: 30
```

## Performance Tuning

### HPA Best Practices:

1. **Resource Requests**:
```yaml
# Always set resource requests for HPA to work
resources:
  requests:
    cpu: 100m     # Base CPU needed
    memory: 128Mi # Base memory needed
  limits:
    cpu: 1000m    # Maximum CPU allowed
    memory: 1Gi   # Maximum memory allowed
```

2. **Choosing Metrics**:
- **CPU**: Good for compute-intensive tasks
- **Memory**: Good for memory-bound applications
- **Queue Length**: Best for job processing systems
- **Request Rate**: Good for APIs

3. **Scaling Policies**:
```yaml
# Example: Gradual scaling for stability
behavior:
  scaleUp:
    policies:
    - type: Pods
      value: 1
      periodSeconds: 60  # Add 1 pod per minute
    - type: Percent
      value: 10
      periodSeconds: 60  # Or 10% increase per minute
    selectPolicy: Max    # Choose whichever scales more
```

4. **Testing Different Configurations**:
```bash
# Test configuration without applying
kubectl apply -f k8s/workers/hpa.yaml --dry-run=client -o yaml

# Compare different HPA configurations
kubectl diff -f k8s/workers/hpa-custom.yaml
```

### Optimization Strategies

1. **Right-size Your Pods**:
```bash
# Analyze actual usage
kubectl top pods -n fastapi-k8-proto --containers

# Adjust requests/limits based on p95 usage
```

2. **Use Multiple HPAs**:
```yaml
# Separate HPAs for different workload types
# - CPU-based HPA for general load
# - Queue-based HPA for batch processing
```

3. **Consider VPA for Right-sizing**:
```bash
# VPA can recommend optimal resource requests
kubectl describe vpa celery-worker-vpa -n fastapi-k8-proto
```

## Monitoring Auto-scaling

### Useful Commands:

```bash
# Watch HPA in real-time
watch -n 2 'kubectl get hpa -n fastapi-k8-proto'

# Get HPA details with conditions
kubectl describe hpa -n fastapi-k8-proto | grep -A 10 "Conditions:"

# View scaling events
kubectl get events -n fastapi-k8-proto --field-selector reason=SuccessfulRescale

# Check current metrics values
kubectl get hpa celery-worker-hpa -n fastapi-k8-proto -o jsonpath='{.status.currentMetrics[*]}'

# Monitor pod creation/deletion
kubectl get pods -n fastapi-k8-proto -w --show-labels
```

### Key Metrics to Monitor:

1. **Scaling Frequency**: How often does scaling occur?
2. **Scaling Amplitude**: How many pods are added/removed?
3. **Response Time**: How quickly does scaling respond to load?
4. **Stability**: Does the system reach a stable state?

### Grafana Dashboard (Optional):

If you have Grafana installed, create dashboards for:
- HPA metrics over time
- Pod count by deployment
- Resource utilization trends
- Queue length vs pod count
- Scaling events timeline

Example Prometheus queries:
```promql
# Pod count over time
kube_deployment_status_replicas{namespace="fastapi-k8-proto"}

# HPA target metrics
kube_horizontalpodautoscaler_status_target_metric{namespace="fastapi-k8-proto"}

# Queue length
celery_queue_length{namespace="fastapi-k8-proto"}

# Scaling rate
rate(kube_deployment_status_replicas[5m])
```

## Advanced Auto-scaling Patterns

### 1. **Predictive Scaling**
Use historical data to predict load:
```yaml
# Scale up before expected load
# Requires custom controller or scheduled scaling
```

### 2. **Multi-Metric Scaling**
Combine multiple signals:
```yaml
metrics:
- type: Resource
  resource:
    name: cpu
    target:
      type: Utilization
      averageUtilization: 70
- type: External
  external:
    metric:
      name: predictions_per_second
      selector:
        matchLabels:
          model: "ml-model"
    target:
      type: AverageValue
      averageValue: "100"
```

### 3. **Scheduled Scaling**
For predictable patterns:
```bash
# Use CronJob to adjust HPA min/max
kubectl patch hpa celery-worker-hpa -n fastapi-k8-proto \
  --patch '{"spec":{"minReplicas":5}}' \
  --type merge
```

### 4. **Cost-Aware Scaling**
Balance performance and cost:
```yaml
# Use node selectors for spot instances
# Scale on spot instances first
```

## Summary

The auto-scaling configuration enables:
1. **Resource-based scaling**: CPU and memory utilization
2. **Queue-based scaling**: Scale based on pending jobs (with custom metrics)
3. **Intelligent behavior**: Different policies for scale-up and scale-down
4. **Stability**: Prevents flapping with stabilization windows

The system now automatically adjusts the number of worker pods based on workload, ensuring efficient resource utilization while maintaining performance.

## Next Steps

With auto-scaling configured, consider:
1. **Production Hardening**:
   - Set up comprehensive monitoring (Prometheus + Grafana)
   - Implement pod disruption budgets
   - Configure cluster auto-scaling
   
2. **Advanced Patterns**:
   - Implement predictive scaling
   - Set up multi-region scaling
   - Create custom metrics for business KPIs
   
3. **Optimization**:
   - Fine-tune scaling parameters based on real load
   - Implement cost optimization strategies
   - Set up alerting for scaling events
   
4. **Testing**:
   - Chaos engineering for scaling behavior
   - Load testing with production-like patterns
   - Disaster recovery testing 