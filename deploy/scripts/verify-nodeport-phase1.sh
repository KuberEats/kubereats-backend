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

declare -A ports=(
  [merchant-service]=31081
  [committee-service]=31082
  [verification-service]=31083
)

declare -A health=(
  [merchant-service]="/health/live"
  [committee-service]="/health/live"
  [verification-service]="/healthz"
)

failures=0

print_fail_debug() {
  echo
  echo "== Debug: pods =="
  kubectl get pods -n "$namespace" -o wide || true
  echo
  echo "== Debug: describe pods =="
  kubectl describe pods -n "$namespace" || true
  echo
  echo "== Debug: logs tail =="
  mapfile -t pods < <(kubectl get pods -n "$namespace" --no-headers -o custom-columns=NAME:.metadata.name 2>/dev/null || true)
  for pod in "${pods[@]:-}"; do
    echo "-- logs $pod --"
    kubectl logs "$pod" -n "$namespace" --all-containers --tail=100 || true
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

echo "== Nodes =="
kubectl get nodes -o wide

mapfile -t worker_rows < <(kubectl get nodes --no-headers -o wide | awk '$3 !~ /control-plane|master/ {print $1"\t"$2"\t"$6}')
if [[ ${#worker_rows[@]} -ne 4 ]]; then
  echo "WARN: expected 4 worker nodes, found ${#worker_rows[@]}"
fi

worker_ips=()
for row in "${worker_rows[@]}"; do
  name=$(awk '{print $1}' <<<"$row")
  ready=$(awk '{print $2}' <<<"$row")
  ip=$(awk '{print $3}' <<<"$row")
  echo "worker: $name ready=$ready ip=$ip"
  if [[ "$ready" != "Ready" ]]; then
    echo "FAIL: worker $name is not Ready"
    failures=$((failures + 1))
  fi
  worker_ips+=("$ip")
done

echo
echo "== Services =="
kubectl get svc -n "$namespace"
for svc in merchant-service committee-service verification-service; do
  expected="${ports[$svc]}"
  actual_type=$(kubectl get svc "$svc" -n "$namespace" -o jsonpath='{.spec.type}')
  actual_port=$(kubectl get svc "$svc" -n "$namespace" -o jsonpath='{.spec.ports[?(@.name=="http")].nodePort}')
  check "$svc is NodePort" test "$actual_type" = "NodePort"
  check "$svc nodePort is $expected" test "$actual_port" = "$expected"
done

echo
echo "== Deployments =="
for deploy in merchant-service committee-service verification-service; do
  check "$deploy rollout" kubectl rollout status "deployment/$deploy" -n "$namespace" --timeout=120s
done

echo
echo "== Cluster DNS health checks =="
for svc in merchant-service committee-service verification-service; do
  pod="tmp-curl-${svc}"
  path="${health[$svc]}"
  check "$svc DNS health $path" kubectl run "$pod" --rm -i --restart=Never --image=curlimages/curl:latest -n "$namespace" -- curl -fsS "http://${svc}${path}"
done

echo
echo "== Worker NodePort health checks from control plane =="
if ! command -v curl >/dev/null 2>&1; then
  echo "FAIL: curl is not installed on the control plane; cannot test workerIP:nodePort directly."
  echo "Debug command: sudo apt-get update && sudo apt-get install -y curl"
  failures=$((failures + 1))
else
  for svc in merchant-service committee-service verification-service; do
    port="${ports[$svc]}"
    path="${health[$svc]}"
    for ip in "${worker_ips[@]}"; do
      check "$svc http://${ip}:${port}${path}" curl -fsS --connect-timeout 5 --max-time 10 "http://${ip}:${port}${path}"
    done
  done
fi

if [[ "$failures" -eq 0 ]]; then
  echo
  echo "SUCCESS: Phase 1 NodePort verification passed."
else
  echo
  echo "FAIL: $failures checks failed."
  print_fail_debug
  exit 1
fi
REMOTE_SCRIPT
)

ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "NAMESPACE=$(printf '%q' "$NAMESPACE") bash -s" <<<"$remote_script"
