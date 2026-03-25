#!/bin/bash
# scripts/teardown.sh
# Removes all AIOps resources from the Kind cluster.

set -e
echo "==> Tearing down AIOps platform..."

kubectl delete -f infra/kubernetes/agents/     --ignore-not-found
kubectl delete -f infra/kubernetes/storage/    --ignore-not-found
kubectl delete -f infra/kubernetes/monitoring/ --ignore-not-found
kubectl delete secret aiops-secrets            --ignore-not-found
kubectl delete pod crash-test                  --ignore-not-found 2>/dev/null || true

echo "✓ All AIOps resources removed."
echo ""
echo "To also delete the Kind cluster entirely:"
echo "  kind delete cluster --name aiops"
