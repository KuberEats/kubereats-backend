# Verification Kubernetes Deployment

This directory is the baseline Kubernetes deployment template for the KuberEats verification backend service. It deploys only the application. PostgreSQL must run outside Kubernetes and be exposed through a stable endpoint such as Patroni, HAProxy, VIP, or DNS, not a single database node address.

## Structure

```text
deploy/k8s/
  base/
    configmap.yaml
    deployment.yaml
    service.yaml
    verification-secret.example.yaml
    kustomization.yaml
  overlays/
    dev/
      kustomization.yaml
    prod/
      kustomization.yaml
```

## Prerequisites

- `kubectl` context points to the target cluster.
- Target namespace exists, for example `kubereats-dev` or `kubereats-prod`.
- The image exists in the registry, for example `ghcr.io/kubereats/kubereats-verification:dev`.
- External PostgreSQL is reachable from the cluster node or pod CIDR.
- PostgreSQL `pg_hba.conf` and firewall rules allow the cluster to connect to port 5432.

## Configuration

Non-sensitive settings live in `base/configmap.yaml`:

| Variable | Description | Default |
| --- | --- | --- |
| `APP_ENV` | Runtime environment | `production` |
| `LOG_LEVEL` | Uvicorn log level | `info` |
| `PORT` | Container HTTP port | `8000` |
| `DB_POOL_SIZE` | SQLAlchemy pool size per pod | `5` |
| `DB_MAX_OVERFLOW` | Extra DB connections per pod | `10` |
| `DB_POOL_TIMEOUT` | Pool wait timeout in seconds | `30` |
| `AUTO_CREATE_TABLES` | Keep current `create_all` startup behavior | `true` |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL | `7` |

Sensitive settings must be created as a Kubernetes Secret and must not be committed:

| Variable | Description |
| --- | --- |
| `DATABASE_URL` | External PostgreSQL URL |
| `JWT_SECRET_KEY` | Shared JWT signing secret |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` | Future SMTP provider settings |
| `MAILGUN_API_KEY`, `MAILGUN_DOMAIN` | Future Mailgun provider settings |

With 2 replicas and the default pool settings, the service can open up to 30 PostgreSQL connections (`(DB_POOL_SIZE + DB_MAX_OVERFLOW) * replicas`). Tune these values against PostgreSQL `max_connections` before increasing replicas.

## Create Secret

Use `base/verification-secret.example.yaml` only as a reference. Create the real Secret from your environment or secret manager:

```bash
kubectl -n kubereats-dev create secret generic verification-secret \
  --from-literal=DATABASE_URL='postgresql+psycopg2://user:password@postgres.example.internal:5432/kubereats' \
  --from-literal=JWT_SECRET_KEY='replace-with-real-shared-secret'
```

Add SMTP or Mailgun keys only when the application starts using them.

## Deploy Dev

```bash
kubectl apply -k deploy/k8s/overlays/dev
kubectl -n kubereats-dev rollout status deploy/verification
```

## Check Status

```bash
kubectl -n kubereats-dev get pods -l app.kubernetes.io/name=verification
kubectl -n kubereats-dev describe pod -l app.kubernetes.io/name=verification
kubectl -n kubereats-dev logs deploy/verification
kubectl -n kubereats-dev rollout status deploy/verification
```

## Smoke Test

```bash
kubectl -n kubereats-dev port-forward svc/verification 8080:80
curl http://localhost:8080/healthz
curl http://localhost:8080/readyz
curl http://localhost:8080/metrics
```

`/healthz` checks only that the process is alive. `/readyz` checks PostgreSQL connectivity with `SELECT 1`.

## Rollback

```bash
kubectl -n kubereats-dev rollout undo deploy/verification
kubectl -n kubereats-dev rollout status deploy/verification
```

## Optional Ingress

Ingress is intentionally not part of the baseline because this repo does not define an ingress controller or gateway standard yet. A future overlay can add something like:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: verification
spec:
  rules:
    - host: api.kubereats.click
      http:
        paths:
          - path: /api/verification
            pathType: Prefix
            backend:
              service:
                name: verification
                port:
                  number: 80
```

## Troubleshooting

`ImagePullBackOff`: confirm the image tag exists, imagePullSecret is configured if the registry is private, and the overlay uses the expected tag.

`CrashLoopBackOff`: inspect `kubectl logs deploy/verification`. Common causes are missing `DATABASE_URL`, invalid `JWT_SECRET_KEY`, or DB connectivity errors during startup.

`readiness failed`: `/readyz` requires PostgreSQL. Check `DATABASE_URL`, DNS resolution, network routing, PostgreSQL availability, and pool limits.

`DB connection failed`: verify that `DATABASE_URL` points to the stable external PostgreSQL endpoint, not a single transient node.

`wrong DATABASE_URL`: use the SQLAlchemy-compatible driver prefix already used by the service, for example `postgresql+psycopg2://...`.

`pg_hba/firewall denied`: allow the Kubernetes node or pod CIDR to connect to PostgreSQL on 5432.

## Next Steps

- Replace startup `Base.metadata.create_all` with a real migration flow such as Alembic.
- Add NetworkPolicy after the cluster baseline is defined, limiting egress to PostgreSQL 5432 and required platform services.
- Publish images through a standard release workflow with immutable tags.
