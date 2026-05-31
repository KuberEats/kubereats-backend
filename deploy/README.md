# Kubereats GitOps Deployment

This directory defines the first-pass on-prem Kubernetes deployment for Kubereats backend services using Argo CD + Kustomize + GitOps.

## Architecture

- Argo CD is installed in `argocd` and syncs this Git repository.
- Kustomize `base` contains common Deployment, Service, ConfigMap, and secret examples.
- Kustomize `overlays/dev` deploys to `kubereats-dev` with one replica per service and `:dev` image tags.
- Kustomize `overlays/prod` is sample-only until production promotion is explicitly enabled.
- CI should build and publish images, then commit image tag changes to Git. CI should not directly run `kubectl apply` against production because Git must remain the auditable desired state and Argo CD must own drift correction and rollback.

## Repository Inventory

Current `main` has only repo-level documentation. Backend implementations are in module branches.

| Service | Source branch | Dockerfile | Dependency file | Health endpoint | Port | Image | Startup command | Required secrets | Deployable now |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| merchant-service | `origin/module/merchant` | `Dockerfile` | `pyproject.toml`, `uv.lock` | `/health/live`, `/health/ready` | 8000 | `ghcr.io/kubereats/merchant-service:dev` TODO publish | `uv run python scripts/migrate.py && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` | `DATABASE_URL`, `JWT_SECRET_KEY` | Manifest-ready; image registry/tag and secret required |
| committee-service | `origin/module/fuwei-system` | `Dockerfile` | `pyproject.toml`, `uv.lock` | `/health/live`, `/health/ready` | 8000 | `ghcr.io/kubereats/committee-service:dev` TODO publish | `uv run python scripts/migrate.py && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` | `DATABASE_URL`, `JWT_SECRET_KEY` | Manifest-ready; image registry/tag and secret required |
| notification-service | `origin/module/notification` | `Dockerfile` | `pyproject.toml`, `uv.lock` | `/health/live`, `/health/ready` | 8000 | `ghcr.io/kubereats/notification-service:dev` TODO publish | `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` | `DATABASE_URL`, `REDIS_URL`, `INTERNAL_SERVICE_TOKENS` | API manifest-ready; worker deployment TODO |
| finance-service | `origin/module/finance` | `Dockerfile` | `pyproject.toml`, `uv.lock` | `/health` | 8000 | `ghcr.io/kubereats/finance-service:dev` TODO publish | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | `DATABASE_URL`, `REDIS_URL` | Manifest-ready; image registry/tag and secret required |
| order-scheduler-service | `origin/module/order-scheduler` | `Dockerfile.dev` only | `pyproject.toml`, `uv.lock`, `package.json` | `/health` | 8000 | `ghcr.io/kubereats/order-scheduler-service:dev` TODO publish | `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` | `DATABASE_URL`, `RABBITMQ_URL`, `INTERNAL_TASK_TOKEN` | Needs production Dockerfile or approved dev image |
| recommendation-service | `origin/module/recommend` | `Dockerfile.dev` only | `pyproject.toml`, `uv.lock`, `package.json` | `/health` | 8000 | `ghcr.io/kubereats/recommendation-service:dev` TODO publish | `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` | `DATABASE_URL`, `OPENROUTER_API_KEY` | Needs production Dockerfile or approved dev image |
| tagging-service | `origin/module/tagging` | `Dockerfile` | `pyproject.toml`, `uv.lock` | `/health` | 8000 | `ghcr.io/kubereats/tagging-service:dev` TODO publish | `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` | `DATABASE_URL`, `REDIS_URL` | Manifest-ready; image registry/tag and secret required |
| verification-service | `origin/module/verification` | `Dockerfile` | `pyproject.toml`, `uv.lock` | `/healthz`, `/readyz`, `/health/live`, `/health/ready` | 8000 | `ghcr.io/kubereats/kubereats-verification:dev` TODO publish | `python scripts/migrate.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}` | `DATABASE_URL`, `JWT_SECRET_KEY`, optional SMTP/Mailgun values | Manifest-ready; image registry/tag and secret required |
| employee-order | `origin/module/employee-order` | missing | missing | TODO | TODO | TODO | TODO | TODO | Not deployable from current repo contents |

Existing GitHub Actions mostly run tests and local Docker builds. Only `module/verification` has a GHCR-style image name in CI; most services still need a publish workflow or registry convention.

## Prerequisites

- SSH access to control plane `192.168.17.11`.
- SSH user `kubereats`.
- SSH private key `tf-cloud-init` available via `SSH_KEY`, `$HOME/.ssh/tf-cloud-init`, or `./tf-cloud-init`.
- `kubectl` works on the control plane for user `kubereats`.
- The cluster can pull the chosen GHCR images.
- External PostgreSQL/Patroni/VM DB connection strings are ready.
- External Redis/RabbitMQ/OpenRouter/SMTP credentials are ready where required.

## Bootstrap Argo CD

```bash
chmod +x deploy/argocd/bootstrap/install-argocd.sh
SSH_KEY=~/.ssh/tf-cloud-init ./deploy/argocd/bootstrap/install-argocd.sh
```

The script runs `kubectl` through SSH on the control plane. It does not use local kubeconfig and does not expose Argo CD publicly.

## Log In To Argo CD

Start a tunnel and remote port-forward:

```bash
ssh -i ~/.ssh/tf-cloud-init -L 8080:127.0.0.1:8080 kubereats@192.168.17.11   'kubectl port-forward svc/argocd-server -n argocd 8080:443 --address 127.0.0.1'
```

Open:

```text
https://localhost:8080
```

Get the initial admin password:

```bash
ssh -i ~/.ssh/tf-cloud-init kubereats@192.168.17.11   "kubectl -n argocd get secret argocd-initial-admin-secret   -o jsonpath='{.data.password}' | base64 -d && echo"
```

## Apply The Argo CD Project And Root App

If this repo exists on the control plane:

```bash
ssh -i ~/.ssh/tf-cloud-init kubereats@192.168.17.11   "kubectl apply -f <repo-path>/deploy/argocd/projects/kubereats-project.yaml &&    kubectl apply -f <repo-path>/deploy/argocd/apps/root-app.yaml"
```

If the repo is not on the control plane, stream manifests over SSH stdin:

```bash
ssh -i ~/.ssh/tf-cloud-init kubereats@192.168.17.11   'kubectl apply -f -' < deploy/argocd/projects/kubereats-project.yaml

ssh -i ~/.ssh/tf-cloud-init kubereats@192.168.17.11   'kubectl apply -f -' < deploy/argocd/apps/root-app.yaml
```

Alternatively, copy the YAML files to the control plane and apply them there.

## Create Secrets

Do not commit real secrets. Create each required secret in `kubereats-dev` before expecting pods to become Ready.

Example:

```bash
ssh -i ~/.ssh/tf-cloud-init kubereats@192.168.17.11   "kubectl create secret generic merchant-service-secret     -n kubereats-dev     --from-literal=DATABASE_URL='postgresql://...'     --from-literal=JWT_SECRET_KEY='...'     --dry-run=client -o yaml | kubectl apply -f -"
```

Repeat for each `deploy/k8s/base/<service>/secret.example.yaml`. Later, replace manual secrets with Sealed Secrets, SOPS, or External Secrets.

## Update Image Tags

1. Build and push the service image from the relevant module branch.
2. Update `deploy/k8s/overlays/dev/<service>/patch-image.yaml` with the immutable tag or short SHA.
3. Commit and push.
4. Argo CD auto-sync applies the new desired state.

## Rollback

Preferred rollback:

```bash
git revert <image-tag-commit>
```

Then let Argo CD sync back to the previous image. If Argo CD CLI or UI is available, a manual rollback can also be triggered there.

## Verify Deployment

```bash
chmod +x deploy/scripts/verify-k8s-deploy.sh
SSH_KEY=~/.ssh/tf-cloud-init ./deploy/scripts/verify-k8s-deploy.sh
```

The script checks nodes, namespaces, workloads, Argo CD Applications, rollout status, and in-cluster service health checks.

You can also run ad hoc remote kubectl commands:

```bash
./deploy/scripts/remote-kubectl.sh get nodes -o wide
./deploy/scripts/remote-kubectl.sh get applications -n argocd
./deploy/scripts/remote-kubectl.sh get deploy,svc -n kubereats-dev
```

## Validate Manifests

If local `kubectl` exists:

```bash
kubectl kustomize deploy/k8s/overlays/dev
kubectl apply --dry-run=client -k deploy/k8s/overlays/dev
```

If only the control plane has `kubectl` and the repo exists there:

```bash
ssh -i ~/.ssh/tf-cloud-init kubereats@192.168.17.11   "cd <repo-path> && kubectl kustomize deploy/k8s/overlays/dev"
```

If the repo is not on the control plane, stream a rendered manifest from a machine with `kubectl` or copy the repo first. Do not claim validation until one of these commands succeeds.

## Common Issues

- SSH key not found: set `SSH_KEY=/path/to/tf-cloud-init`, or place the key at `$HOME/.ssh/tf-cloud-init` or `./tf-cloud-init`.
- `kubectl` permission denied: on the control plane check `kubectl config current-context`, `~/.kube/config`, `/etc/kubernetes/admin.conf`, and `/etc/rancher/k3s/k3s.yaml`. Fix by granting `kubereats` a valid kubeconfig rather than overwriting cluster state.
- `ImagePullBackOff`: confirm the image tag exists, GHCR auth is configured if private, and any `imagePullSecrets` are present.
- `CrashLoopBackOff`: inspect env, DB connectivity, startup migrations, and logs.
- DB connection failed: verify `DATABASE_URL`, network route, DB firewall, SSL mode, and credentials.
- Argo CD `OutOfSync`: check repo URL, branch, path, Kustomize render errors, and project permissions.
- Ingress 404: confirm ingress controller, host header, path routing, service name, and service port.
- Secret missing: create the required `<service>-secret` in the target namespace.
- Health check failed: confirm the endpoint for that service and whether readiness depends on DB.
- Git repo URL wrong: update `deploy/argocd/projects/kubereats-project.yaml` and `deploy/argocd/apps/*.yaml`.
- GHCR private image pull secret missing: create a Docker registry secret and patch the service account or deployments.

## Next Steps

- Add GHCR publish workflows and image tags for every module branch.
- Add `imagePullSecrets` if GHCR images are private.
- Replace manual secrets with External Secrets, Sealed Secrets, or SOPS.
- Split notification worker into its own Deployment if async email delivery is required now.
- Add HPA once CPU/memory and request traffic are understood.
- Add Prometheus metrics scraping and Grafana dashboards.
- Add DB monitoring for Patroni/PostgreSQL.
- Add Ingress TLS and internal DNS.
- Define a production promotion flow from dev image tags to prod overlays.
