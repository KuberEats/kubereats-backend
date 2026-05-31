# Kubernetes-Local Monitoring

Kubereats has two monitoring scopes:

- Central monitoring VM `10.250.0.4`: main Grafana, Alertmanager, central Prometheus, DB dashboards, and GCS backup dashboards.
- Kubernetes-local monitoring: kube-prometheus-stack inside the Kubernetes cluster for node, pod, workload, kubelet, cAdvisor, kube-state-metrics, and selected DB network-path checks from inside the cluster.

The Kubernetes stack does not replace the central monitoring VM. It adds observability from the cluster's own network perspective.

## Why This Exists

A test pod inside Kubernetes can reach pg3 Patroni at:

```text
http://10.250.0.3:8008/patroni
```

The central monitoring VM currently times out when scraping pg3 Patroni. A cluster-local Prometheus can therefore observe Kubernetes health and selected database network paths that may differ from the monitoring VM path.

## Deployment Method

This repo uses Argo CD for GitOps. Monitoring is split into two Argo CD Applications:

- `kubereats-monitoring-stack`: Helm chart `prometheus-community/kube-prometheus-stack` in namespace `monitoring`.
- `kubereats-monitoring-db-network`: Kustomize resources for DB endpoint Services, EndpointSlices, ServiceMonitors, and PrometheusRules.

The monitoring project is defined in:

```text
deploy/argocd/projects/kubereats-monitoring-project.yaml
```

The Helm values file is:

```text
deploy/monitoring/kube-prometheus-stack/values.yaml
```

Grafana is disabled in the cluster-local stack. Use the central Grafana on `10.250.0.4` as the main dashboard entry point. Prometheus and Alertmanager are ClusterIP-only.

## What Gets Monitored

kube-prometheus-stack provides:

- Prometheus Operator
- Prometheus
- Alertmanager with placeholder/default routing only
- kube-state-metrics
- node-exporter
- kubelet and cAdvisor scraping
- default Kubernetes alert rules

Kubereats adds ServiceMonitors for these DB network targets:

| target | endpoint | purpose |
| --- | --- | --- |
| pg1 Patroni | `192.168.16.221:8008/metrics` | DB HA state from K8s network path |
| pg2 Patroni | `192.168.16.222:8008/metrics` | DB HA state from K8s network path |
| pg3 Patroni | `10.250.0.3:8008/metrics` | GCP DB node path from K8s |
| postgres_exporter | `:9187/metrics` | prepared only; may be down until exporter is installed |
| node_exporter | `:9100/metrics` | prepared only; may be down until exporter is installed |

`/patroni` was tested for pg3 reachability, but Prometheus scrapes `/metrics`. If `/patroni` works and `/metrics` does not, enable Patroni metrics or adjust the monitoring design.

## Alerts

Custom Kubernetes warning alerts:

- `KubernetesNodeNotReady`
- `KubernetesPodCrashLooping`
- `KubernetesDeploymentReplicasMismatch`
- `KubernetesPodRestartHigh`
- `KubeletDown`
- `KubernetesPersistentVolumeUsageHigh`

Custom DB network warning alerts:

- `KubereatsK8sPatroniTargetDown`
- `KubereatsK8sPatroniPg3Unreachable`

The full DB alert rules remain in the central monitoring repo. Do not duplicate the full DB alert policy here until postgres_exporter metrics are installed and verified on the DB nodes.

## Safe Access

Do not expose Prometheus or Alertmanager publicly. Use port-forward from the control plane or through SSH:

```bash
ssh -i tf-cloud-init kubereats@192.168.17.11
kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090:9090 --address 127.0.0.1
```

Then open:

```text
http://localhost:9090
```

If accessing from your local workstation through the jump host, tunnel to the control plane and run the port-forward there.

## Verify From The Cluster

Check monitoring pods:

```bash
kubectl get pods -n monitoring -o wide
kubectl get svc -n monitoring
kubectl get servicemonitor,prometheusrule -n monitoring
```

Check pg3 Patroni reachability from an ephemeral pod:

```bash
kubectl run patroni-pg3-check \
  --rm -i --restart=Never \
  --image=curlimages/curl:latest \
  -n monitoring \
  -- curl -fsS http://10.250.0.3:8008/patroni
```

Check whether Prometheus metrics path is available:

```bash
kubectl run patroni-pg3-metrics-check \
  --rm -i --restart=Never \
  --image=curlimages/curl:latest \
  -n monitoring \
  -- curl -fsS http://10.250.0.3:8008/metrics
```

In Prometheus, open **Status > Targets** and verify:

- kube-state-metrics is UP
- node-exporter targets are UP
- kubelet/cAdvisor targets are UP
- pg3 Patroni is UP if `/metrics` exists
- postgres_exporter and node_exporter DB targets may be DOWN until those exporters are deployed on DB nodes

## Central Monitoring Integration Plan

### Option 1: Federation

Central Prometheus on `10.250.0.4` can scrape selected metrics from K8s Prometheus `/federate`. Do not expose K8s Prometheus publicly. Use a private route, restricted NodePort, or internal ingress only after access control is defined.

Example metric families to federate later:

- selected `up` series
- Kubernetes node readiness
- Kubernetes deployment availability
- pg3 Patroni target reachability from inside Kubernetes

### Option 2: Remote Write

K8s Prometheus can remote-write selected metrics to a central backend later. This should be added only after the central storage target, retention, and tenant/security model are chosen.

## Intentionally Not Included

- No public Prometheus or Grafana exposure
- No cluster-local Grafana
- No Loki, ELK, Tempo, or OpenTelemetry
- No backend application code changes
- No application `/metrics` endpoint work
- No committed secrets
- No central Prometheus federation yet
