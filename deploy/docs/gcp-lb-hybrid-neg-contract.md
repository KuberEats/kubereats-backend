# GCP External HTTPS Load Balancer Hybrid NEG Contract

Phase 1.5 uses GCP External HTTPS Load Balancer path routing with Hybrid NEG endpoints that target on-prem Kubernetes worker `NodeIP:NodePort`. Kubernetes Ingress is intentionally not used for dev in this mode.

## URL Routing Design

```text
api.kubereats.click/merchant/*
  -> backend-service-merchant
  -> hybrid-neg-merchant
  -> k8s-worker-a1:31081, k8s-worker-a2:31081, k8s-worker-b1:31081, k8s-worker-b2:31081

api.kubereats.click/committee/*
  -> backend-service-committee
  -> hybrid-neg-committee
  -> k8s-worker-a1:31082, k8s-worker-a2:31082, k8s-worker-b1:31082, k8s-worker-b2:31082

api.kubereats.click/verification/*
  -> backend-service-verification
  -> hybrid-neg-verification
  -> k8s-worker-a1:31083, k8s-worker-a2:31083, k8s-worker-b1:31083, k8s-worker-b2:31083

api.kubereats.click/finance/*
  -> finance-backend
  -> finance-service

api.kubereats.click/tagging/*
  -> tagging-backend
  -> tagging-service
```

## Worker Endpoint Table

| service | nodePort | health path | worker node | worker InternalIP | NEG endpoint IP:port |
| --- | ---: | --- | --- | --- | --- |
| merchant-service | 31081 | `/health/live` | k8s-worker-a1 | 192.168.17.21 | 192.168.17.21:31081 |
| merchant-service | 31081 | `/health/live` | k8s-worker-a2 | 192.168.17.22 | 192.168.17.22:31081 |
| merchant-service | 31081 | `/health/live` | k8s-worker-b1 | 192.168.17.31 | 192.168.17.31:31081 |
| merchant-service | 31081 | `/health/live` | k8s-worker-b2 | 192.168.17.32 | 192.168.17.32:31081 |
| committee-service | 31082 | `/health/live` | k8s-worker-a1 | 192.168.17.21 | 192.168.17.21:31082 |
| committee-service | 31082 | `/health/live` | k8s-worker-a2 | 192.168.17.22 | 192.168.17.22:31082 |
| committee-service | 31082 | `/health/live` | k8s-worker-b1 | 192.168.17.31 | 192.168.17.31:31082 |
| committee-service | 31082 | `/health/live` | k8s-worker-b2 | 192.168.17.32 | 192.168.17.32:31082 |
| verification-service | 31083 | `/healthz` | k8s-worker-a1 | 192.168.17.21 | 192.168.17.21:31083 |
| verification-service | 31083 | `/healthz` | k8s-worker-a2 | 192.168.17.22 | 192.168.17.22:31083 |
| verification-service | 31083 | `/healthz` | k8s-worker-b1 | 192.168.17.31 | 192.168.17.31:31083 |
| verification-service | 31083 | `/healthz` | k8s-worker-b2 | 192.168.17.32 | 192.168.17.32:31083 |

Phase 2a `finance-service` and `tagging-service` are routed by their GCP
backend services to the Kubernetes Services. Their public health paths are
`/finance/health` and `/tagging/health`; Kubernetes probes continue to use the
service-internal `/health` path.

## GCP Health Check Recommendations

Use one GCP health check per backend service:

- merchant backend service: HTTP health check path `/health/live`, port `31081`
- committee backend service: HTTP health check path `/health/live`, port `31082`
- verification backend service: HTTP health check path `/healthz`, port `31083`
- finance backend service: HTTP health check path `/finance/health`
- tagging backend service: HTTP health check path `/tagging/health`

The Kubernetes readiness probes use DB-aware paths where applicable, but the GCP load balancer should use lightweight liveness paths unless production policy requires dependency-aware readiness.

## Firewall Checklist

Allow only the GCP Load Balancer / health check source ranges to reach on-prem worker NodePorts.

Required destination ports for Phase 1.5 NodePort services:

- `31081` for merchant-service
- `31082` for committee-service
- `31083` for verification-service

Add the finance/tagging backend destination ports according to the selected
GCP backend type. The public URL map paths are `/finance/*` and `/tagging/*`.

Checklist:

- Permit GCP LB / health check source ranges to the worker node InternalIPs on `31081-31083`.
- Confirm the on-prem firewall path from GCP to `192.168.17.21`, `192.168.17.22`, `192.168.17.31`, and `192.168.17.32`.
- Do not open NodePort access to the whole internet unless another firewall layer restricts traffic to the GCP LB path.
- Keep Argo CD private; do not expose Argo CD through this public load balancer.

## Path Rewrite Notes

The current Phase 1 services do not necessarily implement the same public prefix
that the GCP URL map receives. For example, if GCP sends `/merchant/health`
unchanged to merchant-service, but the service only serves `/health/live`, the
backend will return `404`.

Choose one path strategy before productionizing:

1. Configure the GCP URL map to rewrite `/merchant/*`, `/committee/*`, and `/verification/*` to `/*` before forwarding.
2. Add explicit prefix routes in each backend service, such as `/merchant/health/live`.
3. Put an API gateway or Kubernetes ingress in front later and route `/api/merchant/*` with rewrite there.

Do not change business API routes during Phase 1.5; keep this documented until API routing is finalized.

Phase 2a finance/tagging target state:

```text
/finance/* -> finance-backend -> finance-service
/tagging/* -> tagging-backend -> tagging-service
```

No GCP URL rewrite is required for finance/tagging because those apps expose
`/finance/*` and `/tagging/*` directly. Only use rewrite temporarily if an older
image is still deployed:

```text
/finance/* rewrite to /api/finance/*
/tagging/* rewrite to /api/tagging/*
```

Remove that temporary rewrite after the route-contract images are deployed.
