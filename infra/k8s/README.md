# Kubernetes Manifests — ChatOps SRE Stack

Deploys the full ChatOps SRE stack into a Kubernetes cluster (Minikube or kind).

## Prerequisites

- [Minikube](https://minikube.sigs.k8s.io/) or [kind](https://kind.sigs.k8s.io/) installed  
- `kubectl` installed and in PATH  
- Docker images built (see build instructions below)

---

## Quick start with Minikube

```bash
# 1. Start cluster
minikube start --cpus=4 --memory=4096

# 2. Point Docker to Minikube's daemon (build images inside the cluster)
eval $(minikube docker-env)           # Linux/macOS
# Windows PowerShell:
# & minikube -p minikube docker-env | Invoke-Expression

# 3. Build images inside Minikube's Docker
docker build -t chatops-payment-service:latest   sample_apps/payment-service/
docker build -t chatops-order-service:latest     sample_apps/order-service/
docker build -t chatops-inventory-service:latest sample_apps/inventory-service/

# 4. Apply manifests (order matters)
kubectl apply -f infra/k8s/00-namespace.yaml
kubectl apply -f infra/k8s/01-postgres.yaml
kubectl apply -f infra/k8s/05-prometheus.yaml
kubectl apply -f infra/k8s/02-payment-service.yaml
kubectl apply -f infra/k8s/03-order-service.yaml
kubectl apply -f infra/k8s/04-inventory-service.yaml

# 5. Check status
kubectl get pods -n chatops -w

# 6. Access services
kubectl port-forward svc/prometheus      -n chatops 9090:9090 &
kubectl port-forward svc/payment-service -n chatops 8001:8001 &
kubectl port-forward svc/order-service   -n chatops 8002:8002 &
```

---

## Switching the MCP server to Kubernetes mode

Set the env var before starting the infra MCP server:

```bash
RUNTIME=k8s python -m mcp_servers.kubernetes.server
```

The `K8sBackend` will load `~/.kube/config` (or in-cluster config if running inside the cluster) and connect to the `chatops` namespace.

Override the namespace:
```bash
K8S_NAMESPACE=my-namespace RUNTIME=k8s python -m mcp_servers.kubernetes.server
```

---

## Files

| File | Description |
|---|---|
| `00-namespace.yaml` | `chatops` namespace |
| `01-postgres.yaml` | Postgres 15 Deployment + Service |
| `02-payment-service.yaml` | payment-service Deployment + Service |
| `03-order-service.yaml` | order-service Deployment + Service |
| `04-inventory-service.yaml` | inventory-service Deployment + Service |
| `05-prometheus.yaml` | Prometheus ConfigMap + Deployment + Service |

---

## Resource limits (match docker-compose)

| Service | Memory limit | CPU limit |
|---|---|---|
| payment-service | 128 Mi | 0.5 |
| order-service | 128 Mi | 0.5 |
| inventory-service | 128 Mi | 0.5 |
| postgres | 256 Mi | 0.5 |
| prometheus | 512 Mi | 0.5 |

---

## State mapping (Kubernetes → contract)

| Kubernetes state | Contract state |
|---|---|
| `Running` | `running` |
| `CrashLoopBackOff` | `restarting` |
| `OOMKilled` | `oom_killed` |
| `Error` / `Completed` | `exited` |
| `Pending` / `ImagePullBackOff` | `not_found` |

> [!NOTE]
> The `K8sBackend` returns the same JSON shapes as `DockerBackend` — Person A's agent sees no difference.

---

## Tear down

```bash
kubectl delete namespace chatops
minikube stop
```
