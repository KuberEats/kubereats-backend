#!/usr/bin/env bash
set -euo pipefail

CONTROL_PLANE_IP="${CONTROL_PLANE_IP:-192.168.17.11}"
SSH_USER="${SSH_USER:-kubereats}"

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

Do not generate a new key unless the cluster was provisioned with it.
EOF
  exit 1
fi

if [[ $# -eq 0 ]]; then
  cat >&2 <<'EOF'
Usage:
  ./deploy/scripts/remote-kubectl.sh get nodes -o wide
EOF
  exit 2
fi

SSH_TARGET="${SSH_USER}@${CONTROL_PLANE_IP}"
SSH_OPTS=(-i "$RESOLVED_SSH_KEY" -o BatchMode=yes -o StrictHostKeyChecking=accept-new)

ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "hostname >/dev/null"

remote_cmd="kubectl"
for arg in "$@"; do
  remote_cmd+=" $(printf '%q' "$arg")"
done

ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "$remote_cmd"
