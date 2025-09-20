 
Complete Kubernetes manifests for all your services. Based on available Docker containers, we have:

- `careti_staging` (Django app)
- `celery_worker_staging` (Celery worker)
- `flower_staging` (Flower monitoring)
- `redis_staging` (Redis)

Create comprehensive manifests for each service:

## 1. Create the Namespace and ConfigMap

First, create `00-namespace.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: careti-staging
  labels:
    name: careti-staging
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: careti-config
  namespace: careti-staging
data:
  DJANGO_ENV: "staging"
  REDIS_HOST: "redis-staging"
  REDIS_PORT: "6379"
  CELERY_BROKER_URL: "redis://redis-staging:6379/0"
  CELERY_RESULT_BACKEND: "redis://redis-staging:6379/0"
```

## 2. Redis Deployment and Service

Create `01-redis.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: careti-staging
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 2Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-staging
  namespace: careti-staging
  labels:
    app: redis-staging
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis-staging
  template:
    metadata:
      labels:
        app: redis-staging
    spec:
      containers:
      - name: redis
        image: redis:latest
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-data
          mountPath: /data
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          tcpSocket:
            port: 6379
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          tcpSocket:
            port: 6379
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: redis-data
        persistentVolumeClaim:
          claimName: redis-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: redis-staging
  namespace: careti-staging
spec:
  selector:
    app: redis-staging
  ports:
  - port: 6379
    targetPort: 6379
  type: ClusterIP
```

## 3. Django Application Deployment

Create `02-django-app.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: careti-staging
  namespace: careti-staging
  labels:
    app: careti-staging
spec:
  replicas: 2
  selector:
    matchLabels:
      app: careti-staging
  template:
    metadata:
      labels:
        app: careti-staging
    spec:
      containers:
      - name: careti
        image: python-careti-careti_staging:latest
        imagePullPolicy: Never  # Use local image
        ports:
        - containerPort: 8001
        envFrom:
        - configMapRef:
            name: careti-config
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /admin/  # Adjust based on your health check endpoint
            port: 8001
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /admin/  # Adjust based on your health check endpoint
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
        volumeMounts:
        - name: app-logs
          mountPath: /app/logs
      volumes:
      - name: app-logs
        emptyDir: {}
      initContainers:
      - name: wait-for-redis
        image: busybox:1.28
        command: ['sh', '-c', 'until nc -z redis-staging 6379; do echo waiting for redis; sleep 2; done;']
---
apiVersion: v1
kind: Service
metadata:
  name: careti-staging-service
  namespace: careti-staging
spec:
  selector:
    app: careti-staging
  ports:
  - port: 8001
    targetPort: 8001
    nodePort: 30001
  type: NodePort
```

## 4. Celery Worker Deployment

Create `03-celery-worker.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker-staging
  namespace: careti-staging
  labels:
    app: celery-worker-staging
spec:
  replicas: 2
  selector:
    matchLabels:
      app: celery-worker-staging
  template:
    metadata:
      labels:
        app: celery-worker-staging
    spec:
      containers:
      - name: celery-worker
        image: python-careti-celery_worker_staging:latest
        imagePullPolicy: Never  # Use local image
        envFrom:
        - configMapRef:
            name: careti-config
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        volumeMounts:
        - name: celery-logs
          mountPath: /app/logs
        livenessProbe:
          exec:
            command:
            - sh
            - -c
            - "celery -A careti inspect ping"
          initialDelaySeconds: 60
          periodSeconds: 30
      volumes:
      - name: celery-logs
        emptyDir: {}
      initContainers:
      - name: wait-for-redis
        image: busybox:1.28
        command: ['sh', '-c', 'until nc -z redis-staging 6379; do echo waiting for redis; sleep 2; done;']
```

## 5. Flower Monitoring Deployment

Create `04-flower.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flower-staging
  namespace: careti-staging
  labels:
    app: flower-staging
spec:
  replicas: 1
  selector:
    matchLabels:
      app: flower-staging
  template:
    metadata:
      labels:
        app: flower-staging
    spec:
      containers:
      - name: flower
        image: mher/flower:latest
        ports:
        - containerPort: 5555
        env:
        - name: CELERY_BROKER_URL
          value: "redis://redis-staging:6379/0"
        - name: FLOWER_PORT
          value: "5555"
        command: ["celery"]
        args: ["-A", "careti", "flower", "--port=5555"]
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
        livenessProbe:
          httpGet:
            path: /
            port: 5555
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /
            port: 5555
          initialDelaySeconds: 10
          periodSeconds: 10
      initContainers:
      - name: wait-for-redis
        image: busybox:1.28
        command: ['sh', '-c', 'until nc -z redis-staging 6379; do echo waiting for redis; sleep 2; done;']
---
apiVersion: v1
kind: Service
metadata:
  name: flower-staging-service
  namespace: careti-staging
spec:
  selector:
    app: flower-staging
  ports:
  - port: 5555
    targetPort: 5555
    nodePort: 30555
  type: NodePort
```

## 6. Ingress Configuration (Optional)

Create `05-ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: careti-ingress
  namespace: careti-staging
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: careti-staging.local  # Change to your domain
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: careti-staging-service
            port:
              number: 8001
      - path: /flower
        pathType: Prefix
        backend:
          service:
            name: flower-staging-service
            port:
              number: 5555
```

## 7. Horizontal Pod Autoscaler (Optional)

Create `06-hpa.yaml`:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: careti-staging-hpa
  namespace: careti-staging
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: careti-staging
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: celery-worker-staging-hpa
  namespace: careti-staging
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: celery-worker-staging
  minReplicas: 2
  maxReplicas: 8
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 75
```

## Deployment Commands

Now run these commands in your SSH terminal:

```bash
# Create directory for manifests
mkdir -p ~/k8s-manifests
cd ~/k8s-manifests

# Copy all the YAML content above into respective files, then:

# Deploy in order
kubectl apply -f 00-namespace.yaml
kubectl apply -f 01-redis.yaml
kubectl apply -f 02-django-app.yaml
kubectl apply -f 03-celery-worker.yaml
kubectl apply -f 04-flower.yaml
kubectl apply -f 05-ingress.yaml  # Optional
kubectl apply -f 06-hpa.yaml      # Optional

# Check deployment status
kubectl get all -n careti-staging

# Watch pods come up
kubectl get pods -n careti-staging -w
```

## Access Your Services

- **Django App**: `http://your-server-ip:30001`
- **Flower**: `http://your-server-ip:30555`
- **Redis**: Internal only (redis-staging:6379)

## Monitoring Commands

```bash
# Check logs
kubectl logs -f deployment/careti-staging -n careti-staging
kubectl logs -f deployment/celery-worker-staging -n careti-staging
kubectl logs -f deployment/flower-staging -n careti-staging

# Check resource usage
kubectl top pods -n careti-staging

# Scale services
kubectl scale deployment careti-staging --replicas=3 -n careti-staging
kubectl scale deployment celery-worker-staging --replicas=4 -n careti-staging
```
