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

Do not copy the private key into this repo.
EOF
  exit 1
fi

SSH_TARGET="${SSH_USER}@${CONTROL_PLANE_IP}"
SSH_OPTS=(-i "$RESOLVED_SSH_KEY" -o BatchMode=yes -o StrictHostKeyChecking=accept-new)

echo "Testing SSH and remote kubectl access..."
ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "hostname && kubectl get nodes"

echo "Installing Argo CD into namespace argocd..."
ssh "${SSH_OPTS[@]}" "$SSH_TARGET" 'set -euo pipefail
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl apply --server-side=true --force-conflicts -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=Available deployment/argocd-server -n argocd --timeout=300s
kubectl wait --for=condition=Available deployment/argocd-repo-server -n argocd --timeout=300s
kubectl wait --for=condition=Available deployment/argocd-applicationset-controller -n argocd --timeout=300s
'

cat <<EOF

Argo CD is installed. It was not exposed publicly.

Open the UI through SSH tunnel + remote port-forward:
  ssh -i "$RESOLVED_SSH_KEY" -L 8080:127.0.0.1:8080 "$SSH_TARGET" \\
    'kubectl port-forward svc/argocd-server -n argocd 8080:443 --address 127.0.0.1'

UI URL:
  https://localhost:8080

Initial admin password:
  ssh -i "$RESOLVED_SSH_KEY" "$SSH_TARGET" \\
    "kubectl -n argocd get secret argocd-initial-admin-secret \\
    -o jsonpath='{.data.password}' | base64 -d && echo"
EOF
