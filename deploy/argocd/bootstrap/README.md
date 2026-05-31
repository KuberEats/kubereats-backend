# Argo CD Bootstrap

Run this from your workstation. The script does not require local kubeconfig; all Kubernetes operations run on the control plane through SSH.

```bash
chmod +x deploy/argocd/bootstrap/install-argocd.sh
SSH_KEY=~/.ssh/tf-cloud-init ./deploy/argocd/bootstrap/install-argocd.sh
```

Defaults:

- `CONTROL_PLANE_IP=192.168.17.11`
- `SSH_USER=kubereats`
- `SSH_KEY=$HOME/.ssh/tf-cloud-init`, then `./tf-cloud-init`

Argo CD UI is intended to be accessed through SSH tunnel and `kubectl port-forward`. Do not expose Argo CD publicly by default.
