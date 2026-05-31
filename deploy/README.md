# Kubereats GitOps Deployment

This directory defines the first-pass on-prem Kubernetes deployment for Kubereats backend services using Argo CD + Kustomize + GitOps.

## Architecture

- Argo CD is installed in `argocd` and syncs this Git repository.
- Kustomize `base` contains common Deployment, Service, ConfigMap, and secret examples.
- Kustomize `overlays/dev` currently runs the phase 1 services plus Phase 2a in `kubereats-dev`: `merchant-service`, `committee-service`, `verification-service`, `tagging-service`, and `finance-service`.
- Kustomize `overlays/prod` is sample-only until production promotion is explicitly enabled.
- The remaining backend services stay in `base` and per-service overlays, but are intentionally excluded from dev sync until their images, secrets, and external dependencies are ready.
- CI should build and publish images, then commit image tag changes to Git. CI should not directly run `kubectl apply` against production because Git must remain the auditable desired state and Argo CD must own drift correction and rollback.

## Repository Inventory

Current `main` has only repo-level documentation. Backend implementations are in module branches.

| Service | Source branch | Dockerfile | Dependency file | Health endpoint | Port | Image | Startup command | Required secrets | Deployable now |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| merchant-service | `origin/module/merchant` | `Dockerfile` | `pyproject.toml`, `uv.lock` | `/health/live`, `/health/ready` | 8000 | `ghcr.io/kubereats/merchant-service:dev` TODO publish | `uv run python scripts/migrate.py && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` | `DATABASE_URL`, `JWT_SECRET_KEY` | Manifest-ready; image registry/tag and secret required |
| committee-service | `origin/module/fuwei-system` | `Dockerfile` | `pyproject.toml`, `uv.lock` | `/health/live`, `/health/ready` | 8000 | `ghcr.io/kubereats/committee-service:dev` TODO publish | `uv run python scripts/migrate.py && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` | `DATABASE_URL`, `JWT_SECRET_KEY` | Manifest-ready; image registry/tag and secret required |
| notification-service | `origin/module/notification` | `Dockerfile` | `pyproject.toml`, `uv.lock` | `/health/live`, `/health/ready` | 8000 | `ghcr.io/kubereats/notification-service:dev` TODO publish | `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` | `DATABASE_URL`, `REDIS_URL`, `INTERNAL_SERVICE_TOKENS` | API manifest-ready; worker deployment TODO |
| finance-service | `origin/module/finance` | `Dockerfile` | `pyproject.toml`, `uv.lock` | `/health` | 8000 | `ghcr.io/kubereats/finance-service:dev` | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | `kubereats-db-app/DATABASE_URL` | Phase 2a dev overlay enabled |
| order-scheduler-service | `origin/module/order-scheduler` | `Dockerfile.dev` only | `pyproject.toml`, `uv.lock`, `package.json` | `/health` | 8000 | `ghcr.io/kubereats/order-scheduler-service:dev` TODO publish | `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` | `DATABASE_URL`, `RABBITMQ_URL`, `INTERNAL_TASK_TOKEN` | Needs production Dockerfile or approved dev image |
| recommendation-service | `origin/module/recommend` | `Dockerfile.dev` only | `pyproject.toml`, `uv.lock`, `package.json` | `/health` | 8000 | `ghcr.io/kubereats/recommendation-service:dev` TODO publish | `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` | `DATABASE_URL`, `OPENROUTER_API_KEY` | Needs production Dockerfile or approved dev image |
| tagging-service | `origin/module/tagging` | `Dockerfile` | `pyproject.toml`, `uv.lock` | `/health` | 8000 | `ghcr.io/kubereats/tagging-service:dev` | `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` | `kubereats-db-app/DATABASE_URL` | Phase 2a dev overlay enabled |
| verification-service | `origin/module/verification` | `Dockerfile` | `pyproject.toml`, `uv.lock` | `/healthz`, `/readyz`, `/health/live`, `/health/ready` | 8000 | `ghcr.io/kubereats/kubereats-verification:dev` TODO publish | `python scripts/migrate.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}` | `DATABASE_URL`, `JWT_SECRET_KEY`, optional SMTP/Mailgun values | Manifest-ready; image registry/tag and secret required |
| employee-order | `origin/module/employee-order` | missing | missing | TODO | TODO | TODO | TODO | TODO | Not deployable from current repo contents |

GitHub Actions build and publish GHCR images for the phase 1 services and Phase 2a services.

## Phase 1 Deployment Scope

Phase 1 deployed:

- `merchant-service`
- `committee-service`
- `verification-service`

After Phase 2a, temporarily excluded from dev sync:

- `notification-service`
- `order-scheduler-service`
- `recommendation-service`
- `employee-order`

This keeps the first Argo CD sync focused on validating the GitOps path, image pull, secrets, and health checks without letting services with missing production Dockerfiles or external dependencies degrade the whole app.

## Phase 2a Deployment Scope

Phase 2a adds only:

- `tagging-service`
- `finance-service`

Both services are exposed in dev with fixed NodePorts for the GCP Load Balancer Hybrid NEG path:

| service | nodePort | health path | public route intent |
| --- | ---: | --- | --- |
| `tagging-service` | `31084` | `/health` | `https://api.kubereats.click/tagging/*` |
| `finance-service` | `31085` | `/health` | `https://api.kubereats.click/finance/*` |

Both services read database configuration from the existing Kubernetes Secret `kubereats-db-app` key `DATABASE_URL`. No per-service secret is required for the Phase 2a API pods.

Still intentionally excluded from dev sync:

- `notification-service`: Redis and worker deployment need a separate phase.
- `order-scheduler-service`: ownership conflict and active branch work; do not touch in Phase 2a.
- `recommendation-service`: external API secret and production image readiness need a separate phase.
- `employee-order`: no deployable service inventory in current repo contents.

Run the Phase 2a smoke test from this repository:

```bash
SSH_KEY=/home/edtsai/tf-cloud-init ./deploy/scripts/smoke-test-phase2a.sh
```

## Phase 1.5 - GCP Load Balancer Hybrid NEG Mode

Dev does not use Kubernetes Ingress in Phase 1.5. Public HTTPS and path routing are handled by the GCP External HTTPS Load Balancer. Kubernetes exposes fixed NodePorts on the worker nodes so GCP Hybrid NEG endpoints can target `WorkerInternalIP:NodePort`.

Argo CD still owns the Kubernetes desired state under `deploy/k8s/overlays/dev`. GCP Load Balancer, backend services, health checks, firewall rules, and Hybrid NEG resources should be managed separately, preferably by Terraform.

Phase 1.5 fixed NodePorts:

| service | nodePort | health path | public route intent |
| --- | ---: | --- | --- |
| `merchant-service` | `31081` | `/health/live` | `https://api.kubereats.click/merchant/*` |
| `committee-service` | `31082` | `/health/live` | `https://api.kubereats.click/committee/*` |
| `verification-service` | `31083` | `/healthz` | `https://api.kubereats.click/verification/*` |
| `tagging-service` | `31084` | `/health` | `https://api.kubereats.click/tagging/*` |
| `finance-service` | `31085` | `/health` | `https://api.kubereats.click/finance/*` |

Check Argo CD and services:

```bash
SSH_KEY=/home/edtsai/tf-cloud-init ./deploy/scripts/remote-kubectl.sh get applications -n argocd
SSH_KEY=/home/edtsai/tf-cloud-init ./deploy/scripts/remote-kubectl.sh get svc -n kubereats-dev
```

Run NodePort verification from your workstation:

```bash
SSH_KEY=/home/edtsai/tf-cloud-init ./deploy/scripts/verify-nodeport-phase1.sh
```

GCP LB examples after Hybrid NEGs, backend services, URL map, and firewall rules are configured:

```bash
curl -fsS https://api.kubereats.click/merchant/health/live
curl -fsS https://api.kubereats.click/committee/health/live
curl -fsS https://api.kubereats.click/verification/healthz
```

Path rewrite warning: if the GCP URL map forwards `/merchant/health/live` unchanged, merchant-service may return `404` because the service currently serves `/health/live`. Configure GCP URL map path rewrite, add backend prefix routes later, or introduce an API gateway/ingress layer in a later phase. See `deploy/docs/gcp-lb-hybrid-neg-contract.md`.

## GHCR Image Build And Publish

`.github/workflows/backend-ghcr.yml` builds the phase 1 services and Phase 2a services:

- `merchant-service` from `module/merchant` -> `ghcr.io/kubereats/merchant-service`
- `committee-service` from `module/fuwei-system` -> `ghcr.io/kubereats/committee-service`
- `verification-service` from `module/verification` -> `ghcr.io/kubereats/kubereats-verification`
- `tagging-service` from `module/tagging` -> `ghcr.io/kubereats/tagging-service`
- `finance-service` from `module/finance` -> `ghcr.io/kubereats/finance-service`

Pull requests run dependency install, tests, and Docker build checks without pushing images. Phase 1 services also run the existing lint step. Pushes to `main`, `deploy/*`, `infra/*`, or `module/*` build and push both tags:

- `<short-sha>` for immutable GitOps deployment
- `dev` for fast dev testing

The workflow lowercases the GitHub repository owner before building the image path, so `KuberEats` becomes `kubereats`. After a successful push build, it updates the dev overlay service `kustomization.yaml` image `newTag` to `<short-sha>` and commits:

```text
chore(gitops): update backend image tags <short-sha> [skip ci]
```

CI does not run `kubectl apply`; Argo CD remains responsible for sync. For `module/*` pushes, the workflow uses `main` as the GitOps update branch because the service branches are source branches and may not contain `deploy/`.

Confirm package existence in GitHub:

```text
GitHub repo or org -> Packages -> merchant-service / committee-service / kubereats-verification / tagging-service / finance-service
```

Or from a machine with Docker access:

```bash
docker pull ghcr.io/kubereats/merchant-service:<short-sha>
docker pull ghcr.io/kubereats/committee-service:<short-sha>
docker pull ghcr.io/kubereats/kubereats-verification:<short-sha>
docker pull ghcr.io/kubereats/tagging-service:<short-sha>
docker pull ghcr.io/kubereats/finance-service:<short-sha>
```

## Prerequisites

- SSH access to control plane `192.168.17.11`.
- SSH user `kubereats`.
- SSH private key `tf-cloud-init` available via `SSH_KEY`, `$HOME/.ssh/tf-cloud-init`, or `./tf-cloud-init`.
- `kubectl` works on the control plane for user `kubereats`.
- The cluster can pull the chosen GHCR images.
- The shared DB Secret points to the Kubernetes ClusterIP Service `kubereats-postgres`, not directly to DB VM IPs.
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

After the GHCR workflow commits image SHA tags and required secrets exist, let Argo CD sync `kubereats-backend-dev` from the UI or check auto-sync status:

```bash
SSH_KEY=/home/edtsai/tf-cloud-init ./deploy/scripts/remote-kubectl.sh get applications -n argocd
SSH_KEY=/home/edtsai/tf-cloud-init ./deploy/scripts/remote-kubectl.sh get pods -n kubereats-dev -o wide
```

## Create Secrets

Do not commit real secrets. Create `kubereats-db-app` first, then create service-specific secrets for non-DB values.

```bash
ssh -i ~/.ssh/tf-cloud-init kubereats@192.168.17.11   "kubectl create secret generic kubereats-db-app     -n kubereats-dev     --from-literal=DATABASE_URL='postgresql://kubereats_app:<password>@kubereats-postgres:5432/kubereats'     --dry-run=client -o yaml | kubectl apply -f -"
```

For phase 1, create only the secrets required by `merchant-service`, `committee-service`, and `verification-service` in `kubereats-dev` before expecting pods to become Ready.

Example:

```bash
ssh -i ~/.ssh/tf-cloud-init kubereats@192.168.17.11   "kubectl create secret generic merchant-service-secret     -n kubereats-dev     --from-literal=JWT_SECRET_KEY='...'     --dry-run=client -o yaml | kubectl apply -f -"
```

For phase 1, repeat only for `committee-service-secret` and `verification-service-secret`. Create secrets for the other services when they are added to the dev overlay. Later, replace manual secrets with Sealed Secrets, SOPS, or External Secrets.

## GHCR Image Pull Secret

The phase 1 dev overlays do not reference an image pull secret by default. A public GitHub repository is not enough for anonymous Kubernetes pulls: each GHCR package must also be public. The workflow attempts to set package visibility to public after pushing images, but organization/package permissions may still require setting this manually in GitHub Packages.

If pods show `401 Unauthorized` while pulling from `ghcr.io`, either set these packages to public in GitHub Packages or add this to the phase 1 Deployment overlay patches:

```yaml
imagePullSecrets:
  - name: ghcr-pull-secret
```

Then create the secret before syncing. Do not commit GitHub tokens.

SSH to the control plane:

```bash
ssh -i /home/edtsai/tf-cloud-init kubereats@192.168.17.11
```

Then run:

```bash
kubectl create secret docker-registry ghcr-pull-secret \
  -n kubereats-dev \
  --docker-server=ghcr.io \
  --docker-username='<GITHUB_USERNAME>' \
  --docker-password='<PAT_WITH_READ_PACKAGES>' \
  --docker-email='<EMAIL>' \
  --dry-run=client -o yaml | kubectl apply -f -
```

## Update Image Tags

1. Build and push the service image from the relevant module branch.
2. Update `deploy/k8s/overlays/dev/<service>/kustomization.yaml` image `newTag` with the immutable tag or short SHA.
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
- `ImagePullBackOff`: confirm the image tag exists, GHCR auth is configured if private, and `ghcr-pull-secret` is present. Useful commands:

```bash
SSH_KEY=/home/edtsai/tf-cloud-init ./deploy/scripts/remote-kubectl.sh get pods -n kubereats-dev -o wide
SSH_KEY=/home/edtsai/tf-cloud-init ./deploy/scripts/remote-kubectl.sh describe pod <pod-name> -n kubereats-dev
SSH_KEY=/home/edtsai/tf-cloud-init ./deploy/scripts/remote-kubectl.sh get secret ghcr-pull-secret -n kubereats-dev
SSH_KEY=/home/edtsai/tf-cloud-init ./deploy/scripts/remote-kubectl.sh get events -n kubereats-dev --sort-by=.lastTimestamp
```
- `CrashLoopBackOff`: inspect env, DB connectivity, startup migrations, and logs.
- DB connection failed: verify `DATABASE_URL`, network route, DB firewall, SSL mode, and credentials.
- Argo CD `OutOfSync`: check repo URL, branch, path, Kustomize render errors, and project permissions.
- Ingress 404: confirm ingress controller, host header, path routing, service name, and service port.
- Secret missing: create the required `<service>-secret` in the target namespace.
- Health check failed: confirm the endpoint for that service and whether readiness depends on DB.
- Git repo URL wrong: update `deploy/argocd/projects/kubereats-project.yaml` and `deploy/argocd/apps/*.yaml`.
- GHCR private image pull secret missing: create a Docker registry secret and patch the service account or deployments.

## Next Steps

- Phase in remaining services one at a time: add or harden production Dockerfile, publish GHCR image, add required external dependency secrets, include the service in `deploy/k8s/overlays/dev/kustomization.yaml`, then validate Argo CD health before moving to the next service. Suggested order after Phase 2a: notification, recommendation, order-scheduler.
- Add `imagePullSecrets` if GHCR images are private.
- Replace manual secrets with External Secrets, Sealed Secrets, or SOPS.
- Split notification worker into its own Deployment if async email delivery is required now.
- Add HPA once CPU/memory and request traffic are understood.
- Add Prometheus metrics scraping and Grafana dashboards.
- Add DB monitoring for Patroni/PostgreSQL.
- Add Ingress TLS and internal DNS.
- Define a production promotion flow from dev image tags to prod overlays.
