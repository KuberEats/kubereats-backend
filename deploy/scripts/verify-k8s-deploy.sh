#!/usr/bin/env bash
set -euo pipefail

CONTROL_PLANE_IP="${CONTROL_PLANE_IP:-192.168.17.11}"
SSH_USER="${SSH_USER:-kubereats}"
NAMESPACE="${NAMESPACE:-kubereats-dev}"

if [[ -n "${SSH_KEY:-}" ]]; then
  RESOLVED_SSH_KEY="$SSH_KEY"
elif [[ -f "$HOME/.ssh/tf-cloud-init" ]]; then
  RESOLVED_SSH_KEY="$HOME/.ssh/tf-cloud-init"
else
  RESOLVED_SSH_KEY="./tf-cloud-init"
fi

if [[ ! -f "$RESOLVED_SSH_KEY" ]]; then
  cat >&2 <<EOF
ERROR: SSH key not found: $RESOLVED_SSH_KEY

Set SSH_KEY explicitly, or place the key at one of:
  1. \$HOME/.ssh/tf-cloud-init
  2. ./tf-cloud-init
EOF
  exit 1
fi

SSH_TARGET="${SSH_USER}@${CONTROL_PLANE_IP}"
SSH_OPTS=(-i "$RESOLVED_SSH_KEY" -o BatchMode=yes -o StrictHostKeyChecking=accept-new)

ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "hostname >/dev/null"

remote_script=$(cat <<'REMOTE_SCRIPT'
set -euo pipefail

namespace="${NAMESPACE:-kubereats-dev}"

echo "== Nodes =="
kubectl get nodes -o wide

echo
echo "== Namespaces =="
kubectl get ns argocd "$namespace"

echo
echo "== Workloads =="
kubectl get deploy,svc,ingress -n "$namespace"

echo
echo "== Argo CD Applications =="
if kubectl api-resources --api-group=argoproj.io | grep -q '^applications'; then
  kubectl get applications -n argocd
else
  echo "Argo CD Application CRD is not installed."
fi

echo
echo "== Rollout Status =="
mapfile -t deployments < <(kubectl get deploy -n "$namespace" -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')
if [[ ${#deployments[@]} -eq 0 ]]; then
  echo "No deployments found in namespace $namespace."
  exit 1
fi

rollout_failed=0
for deploy in "${deployments[@]}"; do
  if ! kubectl rollout status "deployment/$deploy" -n "$namespace" --timeout=180s; then
    rollout_failed=1
  fi
done

echo
echo "== Service Health =="
health_failed=0
services=(
  "merchant-service:/health/live"
  "committee-service:/health/live"
  "verification-service:/healthz"
)

for entry in "${services[@]}"; do
  service="${entry%%:*}"
  path="${entry#*:}"
  pod_name="tmp-curl-${service}"
  echo "-- $service $path"
  if ! kubectl get svc "$service" -n "$namespace" >/dev/null 2>&1; then
    echo "SKIP: service $service not found"
    health_failed=1
    continue
  fi
  if ! kubectl run "$pod_name" \
    --rm -i --restart=Never \
    --image=curlimages/curl:latest \
    -n "$namespace" \
    -- curl -fsS "http://${service}${path}"; then
    echo "FAIL: health check failed for $service"
    health_failed=1
  fi
done

echo
if [[ "$rollout_failed" -eq 0 && "$health_failed" -eq 0 ]]; then
  echo "SUCCESS: rollouts and health checks passed."
else
  cat <<EOF
FAIL: one or more checks failed.

Useful debug commands:
  kubectl get pods -n $namespace -o wide
  kubectl describe pod <pod-name> -n $namespace
  kubectl logs <pod-name> -n $namespace --all-containers
  kubectl get events -n $namespace --sort-by=.lastTimestamp
EOF
  exit 1
fi
REMOTE_SCRIPT
)

ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "NAMESPACE=$(printf '%q' "$NAMESPACE") bash -s" <<<"$remote_script"
