#!/bin/bash
# scripts/simulate_failure.sh
# Creates real failure scenarios to test the full AIOps pipeline.

SUPERVISOR_URL="http://localhost:5001"

echo ""
echo "==> AIOps Failure Simulation Suite"
echo "─────────────────────────────────────"

# ── Scenario 1: CrashLoopBackOff pod ─────────────────────────────────────────
echo "[1/3] Deploying crash-loop pod..."
kubectl run crash-test \
  --image=busybox \
  --restart=Always \
  -- sh -c "echo 'FATAL: out of memory'; echo 'ERROR: connection refused'; sleep 2; exit 1" \
  2>/dev/null || echo "  (crash-test pod already exists)"

sleep 3

echo "  Firing PodCrashLooping alert..."
curl -s -X POST "${SUPERVISOR_URL}/test-alert" \
  -H "Content-Type: application/json" \
  -d '{"alertname":"PodCrashLooping","namespace":"default","pod":"crash-test","severity":"critical"}' \
  | python3 -m json.tool
echo ""

# ── Scenario 2: High memory alert ────────────────────────────────────────────
echo "[2/3] Firing HighMemoryUsage alert..."
curl -s -X POST "${SUPERVISOR_URL}/test-alert" \
  -H "Content-Type: application/json" \
  -d '{"alertname":"HighMemoryUsage","namespace":"default","pod":"crash-test","severity":"warning"}' \
  | python3 -m json.tool
echo ""

# ── Scenario 3: Pod not ready ─────────────────────────────────────────────────
echo "[3/3] Firing PodNotReady alert..."
curl -s -X POST "${SUPERVISOR_URL}/test-alert" \
  -H "Content-Type: application/json" \
  -d '{"alertname":"PodNotReady","namespace":"default","pod":"crash-test","severity":"warning"}' \
  | python3 -m json.tool
echo ""

echo "─────────────────────────────────────"
echo "✓ All 3 scenarios fired."
echo "  Check incidents: curl ${SUPERVISOR_URL}/incidents | python3 -m json.tool"
