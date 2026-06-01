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

api.kubereats.click/tagging/*
  -> backend-service-tagging
  -> hybrid-neg-tagging
  -> k8s-worker-a1:31084, k8s-worker-a2:31084, k8s-worker-b1:31084, k8s-worker-b2:31084

api.kubereats.click/finance/*
  -> backend-service-finance
  -> hybrid-neg-finance
  -> k8s-worker-a1:31085, k8s-worker-a2:31085, k8s-worker-b1:31085, k8s-worker-b2:31085

api.kubereats.click/recommendation/*
  -> backend-service-recommendation
  -> hybrid-neg-recommendation
  -> k8s-worker-a1:31086, k8s-worker-a2:31086, k8s-worker-b1:31086, k8s-worker-b2:31086

api.kubereats.click/order-scheduler/*
  -> backend-service-order-scheduler
  -> hybrid-neg-order-scheduler
  -> k8s-worker-a1:31087, k8s-worker-a2:31087, k8s-worker-b1:31087, k8s-worker-b2:31087
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
| tagging-service | 31084 | `/health` | k8s-worker-a1 | 192.168.17.21 | 192.168.17.21:31084 |
| tagging-service | 31084 | `/health` | k8s-worker-a2 | 192.168.17.22 | 192.168.17.22:31084 |
| tagging-service | 31084 | `/health` | k8s-worker-b1 | 192.168.17.31 | 192.168.17.31:31084 |
| tagging-service | 31084 | `/health` | k8s-worker-b2 | 192.168.17.32 | 192.168.17.32:31084 |
| finance-service | 31085 | `/health` | k8s-worker-a1 | 192.168.17.21 | 192.168.17.21:31085 |
| finance-service | 31085 | `/health` | k8s-worker-a2 | 192.168.17.22 | 192.168.17.22:31085 |
| finance-service | 31085 | `/health` | k8s-worker-b1 | 192.168.17.31 | 192.168.17.31:31085 |
| finance-service | 31085 | `/health` | k8s-worker-b2 | 192.168.17.32 | 192.168.17.32:31085 |
| recommendation-service | 31086 | `/health` | k8s-worker-a1 | 192.168.17.21 | 192.168.17.21:31086 |
| recommendation-service | 31086 | `/health` | k8s-worker-a2 | 192.168.17.22 | 192.168.17.22:31086 |
| recommendation-service | 31086 | `/health` | k8s-worker-b1 | 192.168.17.31 | 192.168.17.31:31086 |
| recommendation-service | 31086 | `/health` | k8s-worker-b2 | 192.168.17.32 | 192.168.17.32:31086 |
| order-scheduler-service | 31087 | `/health` | k8s-worker-a1 | 192.168.17.21 | 192.168.17.21:31087 |
| order-scheduler-service | 31087 | `/health` | k8s-worker-a2 | 192.168.17.22 | 192.168.17.22:31087 |
| order-scheduler-service | 31087 | `/health` | k8s-worker-b1 | 192.168.17.31 | 192.168.17.31:31087 |
| order-scheduler-service | 31087 | `/health` | k8s-worker-b2 | 192.168.17.32 | 192.168.17.32:31087 |

## GCP Health Check Recommendations

Use one GCP health check per backend service:

- merchant backend service: HTTP health check path `/health/live`, port `31081`
- committee backend service: HTTP health check path `/health/live`, port `31082`
- verification backend service: HTTP health check path `/healthz`, port `31083`
- tagging backend service: HTTP health check path `/health`, port `31084`
- finance backend service: HTTP health check path `/health`, port `31085`
- recommendation backend service: HTTP health check path `/health`, port `31086`
- order scheduler backend service: HTTP health check path `/health`, port `31087`

The Kubernetes readiness probes use DB-aware paths where applicable, but the GCP load balancer should use lightweight liveness paths unless production policy requires dependency-aware readiness.

## Firewall Checklist

Allow only the GCP Load Balancer / health check source ranges to reach on-prem worker NodePorts.

Required destination ports:

- `31081` for merchant-service
- `31082` for committee-service
- `31083` for verification-service
- `31084` for tagging-service
- `31085` for finance-service
- `31086` for recommendation-service
- `31087` for order-scheduler-service

Checklist:

- Permit GCP LB / health check source ranges to the worker node InternalIPs on `31081-31087`.
- Confirm the on-prem firewall path from GCP to `192.168.17.21`, `192.168.17.22`, `192.168.17.31`, and `192.168.17.32`.
- Do not open NodePort access to the whole internet unless another firewall layer restricts traffic to the GCP LB path.
- Keep Argo CD private; do not expose Argo CD through this public load balancer.

## Path Rewrite Notes

The current services do not necessarily implement the same public prefix that the GCP URL map receives. For example, if GCP sends `/merchant/health` unchanged to merchant-service, but the service only serves `/health/live`, the backend will return `404`.

Choose one path strategy before productionizing:

1. Configure the GCP URL map to rewrite `/merchant/*`, `/committee/*`, and `/verification/*` to `/*` before forwarding.
2. Add explicit prefix routes in each backend service, such as `/merchant/health/live`.
3. Put an API gateway or Kubernetes ingress in front later and route `/api/merchant/*` with rewrite there.

Do not change business API routes during Phase 1.5; keep this documented until API routing is finalized.
