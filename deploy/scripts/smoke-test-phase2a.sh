#!/usr/bin/env bash
set -euo pipefail

CONTROL_PLANE_IP="${CONTROL_PLANE_IP:-192.168.17.11}"
SSH_USER="${SSH_USER:-kubereats}"
NAMESPACE="${NAMESPACE:-kubereats-dev}"

if [[ -n "${SSH_KEY:-}" ]]; then
  RESOLVED_SSH_KEY="$SSH_KEY"
elif [[ -f "/home/edtsai/tf-cloud-init" ]]; then
  RESOLVED_SSH_KEY="/home/edtsai/tf-cloud-init"
elif [[ -f "$HOME/.ssh/tf-cloud-init" ]]; then
  RESOLVED_SSH_KEY="$HOME/.ssh/tf-cloud-init"
else
  RESOLVED_SSH_KEY="./tf-cloud-init"
fi

if [[ ! -f "$RESOLVED_SSH_KEY" ]]; then
  cat >&2 <<EOF
ERROR: SSH key not found: $RESOLVED_SSH_KEY
Set SSH_KEY or place the key at /home/edtsai/tf-cloud-init, $HOME/.ssh/tf-cloud-init, or ./tf-cloud-init.
EOF
  exit 1
fi

SSH_TARGET="${SSH_USER}@${CONTROL_PLANE_IP}"
SSH_OPTS=(-i "$RESOLVED_SSH_KEY" -o BatchMode=yes -o StrictHostKeyChecking=accept-new)

remote_script=$(cat <<'REMOTE_SCRIPT'
set -euo pipefail

namespace="${NAMESPACE:-kubereats-dev}"
failures=0

services=(
  "merchant-service:/health/live"
  "committee-service:/health/live"
  "verification-service:/healthz"
  "tagging-service:/health"
  "finance-service:/health"
)

print_fail_debug() {
  echo
  echo "== Debug: pods =="
  kubectl get pod -n "$namespace" -o wide || true

  echo
  echo "== Debug: describe pods =="
  for svc_path in "${services[@]}"; do
    svc="${svc_path%%:*}"
    echo "-- describe pods for $svc --"
    kubectl describe pod -n "$namespace" -l "app.kubernetes.io/name=$svc" || true
  done

  echo
  echo "== Debug: logs tail =="
  for svc_path in "${services[@]}"; do
    svc="${svc_path%%:*}"
    mapfile -t pods < <(kubectl get pod -n "$namespace" -l "app.kubernetes.io/name=$svc" --no-headers -o custom-columns=NAME:.metadata.name 2>/dev/null || true)
    if [[ ${#pods[@]} -eq 0 ]]; then
      echo "-- no pods for $svc --"
      continue
    fi
    for pod in "${pods[@]:-}"; do
      echo "-- logs $pod --"
      kubectl logs "$pod" -n "$namespace" --all-containers --tail=100 || true
    done
  done

  echo
  echo "== Debug: events =="
  kubectl get events -n "$namespace" --sort-by=.lastTimestamp || true
}

check() {
  local label="$1"
  shift
  echo "-- $label"
  if "$@"; then
    echo "PASS: $label"
  else
    echo "FAIL: $label"
    failures=$((failures + 1))
  fi
}

echo "== Argo CD Applications =="
kubectl get applications -n argocd

echo
echo "== Deployments and Services =="
kubectl get deploy,svc,pod -n "$namespace" -o wide

echo
echo "== Rollouts =="
for svc_path in "${services[@]}"; do
  svc="${svc_path%%:*}"
  check "$svc rollout" kubectl rollout status "deployment/$svc" -n "$namespace" --timeout=180s
done

echo
echo "== ClusterIP health checks =="
for svc_path in "${services[@]}"; do
  svc="${svc_path%%:*}"
  path="${svc_path#*:}"
  pod_name="tmp-curl-${svc}"
  check "$svc $path" kubectl run "$pod_name" \
    --rm -i --restart=Never \
    --image=curlimages/curl:latest \
    -n "$namespace" \
    -- curl -fsS "http://${svc}${path}"
done

if [[ "$failures" -eq 0 ]]; then
  echo
  echo "SUCCESS: Phase 2a smoke test passed."
else
  echo
  echo "FAIL: $failures checks failed."
  print_fail_debug
  exit 1
fi
REMOTE_SCRIPT
)

ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "NAMESPACE=$(printf '%q' "$NAMESPACE") bash -s" <<<"$remote_script"
