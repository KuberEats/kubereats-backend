# Phase 2a: Tagging And Finance

Phase 2a deploys only `tagging-service` and `finance-service` to the `kubereats-dev` namespace. It does not change notification, order-scheduler, recommendation, or employee-order.

## Services

| Service | Source branch | Image | Kubernetes Service | Type | Service port | NodePort | Container port | Health endpoint |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |
| `tagging-service` | `origin/module/tagging` | `ghcr.io/kubereats/tagging-service:<short-sha>` and `:dev` | `tagging-service` | `NodePort` | 80 | 31084 | 8000 | `/health` |
| `finance-service` | `origin/module/finance` | `ghcr.io/kubereats/finance-service:<short-sha>` and `:dev` | `finance-service` | `NodePort` | 80 | 31085 | 8000 | `/health` |

Phase 2a uses fixed NodePorts to match the existing GCP Load Balancer Hybrid NEG pattern:

- `tagging-service`: `31084`
- `finance-service`: `31085`

## Secret Mapping

Do not decode, print, or commit secret values.

| App env var | Kubernetes Secret | Secret key |
| --- | --- | --- |
| `DATABASE_URL` | `kubereats-db-app` | `DATABASE_URL` |

The Phase 2a API pods do not require `tagging-service-secret` or `finance-service-secret`. Non-sensitive settings are provided by `tagging-service-config` and `finance-service-config`.

## Runtime Configuration

Both services run FastAPI on port `8000`.

- `tagging-service` starts with `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- `finance-service` starts with `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

`tagging-service` readiness uses `/health`, which performs a lightweight DB check in the current service code. Its liveness probe uses `/` so liveness does not depend on DB. `finance-service` uses `/health`, which is an in-process health response in the current service code.

## Argo CD Verification

```bash
SSH_KEY=/home/edtsai/tf-cloud-init ./deploy/scripts/remote-kubectl.sh get applications -n argocd
SSH_KEY=/home/edtsai/tf-cloud-init ./deploy/scripts/remote-kubectl.sh get deploy,svc,pod -n kubereats-dev -o wide
SSH_KEY=/home/edtsai/tf-cloud-init ./deploy/scripts/remote-kubectl.sh rollout status deployment/tagging-service -n kubereats-dev --timeout=180s
SSH_KEY=/home/edtsai/tf-cloud-init ./deploy/scripts/remote-kubectl.sh rollout status deployment/finance-service -n kubereats-dev --timeout=180s
```

## Smoke Test

```bash
SSH_KEY=/home/edtsai/tf-cloud-init ./deploy/scripts/smoke-test-phase2a.sh
```

The smoke test checks Phase 1 health endpoints plus `tagging-service` and `finance-service` health endpoints. It uses read-only HTTP health checks only and does not write to the database.

## Not Included

- `notification-service`: Redis and worker deployment should be handled in a separate phase.
- `order-scheduler-service`: intentionally untouched because active branch work is in progress.
- `recommendation-service`: external API secret and production image readiness should be handled separately.
- `employee-order`: not deployable from current repo inventory.
