#!/bin/bash
# scripts/setup.sh
# Deploys the full AIOps platform to a running Kind cluster.
# Run from project root: bash scripts/setup.sh

set -e

# ── Verify Kind cluster is running ────────────────────────────────────────────
echo "==> Checking Kind cluster..."
if ! kubectl cluster-info &>/dev/null; then
  echo "ERROR: No Kubernetes cluster found. Create one first:"
  echo "  kind create cluster --name aiops"
  exit 1
fi

CLUSTER=$(kubectl config current-context)
echo "  Using cluster: ${CLUSTER}"

# ── Load environment variables ────────────────────────────────────────────────
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
  echo "==> Loaded .env"
else
  echo "ERROR: .env file not found. Run: cp .env.example .env"
  exit 1
fi

# ── Create namespace and secrets ──────────────────────────────────────────────
echo "==> Creating aiops-secrets..."
kubectl create secret generic aiops-secrets \
  --from-literal=GROQ_API_KEY="${GROQ_API_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f -

# ── Build Docker images locally ───────────────────────────────────────────────
echo "==> Building Docker images..."
docker build -t aiops-supervisor:latest -f agents/supervisor/Dockerfile . --quiet
docker build -t aiops-evaluator:latest  -f agents/evaluator/Dockerfile  . --quiet
docker build -t aiops-resolver:latest   -f agents/resolver/Dockerfile   . --quiet
echo "  Images built."

# ── Load images into Kind ─────────────────────────────────────────────────────
# Kind runs its own containerd — images must be explicitly loaded into it.
# This replaces 'eval $(minikube docker-env)' from Minikube workflows.
echo "==> Loading images into Kind cluster..."
kind load docker-image aiops-supervisor:latest --name aiops
kind load docker-image aiops-evaluator:latest  --name aiops
kind load docker-image aiops-resolver:latest   --name aiops
echo "  Images loaded into Kind."

# ── Deploy storage ────────────────────────────────────────────────────────────
echo "==> Deploying Redis..."
kubectl apply -f infra/kubernetes/storage/
kubectl rollout status deployment/redis --timeout=60s

# ── Deploy monitoring stack ───────────────────────────────────────────────────
echo "==> Deploying Prometheus + AlertManager + Grafana..."
kubectl apply -f infra/kubernetes/monitoring/
kubectl rollout status deployment/prometheus  -n monitoring --timeout=90s
kubectl rollout status deployment/grafana     -n monitoring --timeout=90s

# ── Apply RBAC ────────────────────────────────────────────────────────────────
echo "==> Applying RBAC rules..."
kubectl apply -f infra/kubernetes/agents/rbac.yml

# ── Deploy agents ─────────────────────────────────────────────────────────────
echo "==> Deploying agents..."
kubectl apply -f infra/kubernetes/agents/
kubectl rollout status deployment/supervisor --timeout=90s

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║         AIOps Platform — Deployed on Kind        ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║  Run these in separate terminals to access:      ║"
echo "║                                                  ║"
echo "║  Supervisor  :           ║"
echo "║                                                  ║"
echo "║  Prometheus  : kubectl port-forward              ║"
echo "║                -n monitoring svc/prometheus      ║"
echo "║                9090:9090                         ║"
echo "║                                                  ║"
echo "║  Grafana     : kubectl port-forward              ║"
echo "║                -n monitoring svc/grafana         ║"
echo "║                3000:3000                         ║"
echo "║                                                  ║"
echo "║  AlertManager: kubectl port-forward              ║"
echo "║                -n monitoring svc/alertmanager    ║"
echo "║                9093:9093                         ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
kubectl get pods -A
