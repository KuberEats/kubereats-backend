# kubereats-backend

# Notice 
checkout module/<branch>
git pull and push

## Observability

Order Consumer exposes Prometheus metrics from the worker process on `/metrics`.
In Kubernetes this is scraped through the internal `order-consumer-service`
ClusterIP Service on port `9100` and the `ServiceMonitor` under
`deploy/k8s/base/order-consumer-service/servicemonitor.yaml`.

Key metrics:

- `order_consumer_up`
- `order_consumer_poll_total`
- `order_consumer_reservation_processed_total`
- `order_consumer_reservation_failed_total`
- `order_consumer_last_poll_timestamp_seconds`

SonarQube project key:

```text
kubereats-order-consumer-service
```

Run tests with coverage before scanning:

```bash
uv run pytest
npm run test:coverage
```

Run the scanner from a host that can reach the private SonarQube endpoint:

```bash
export SONAR_TOKEN='<token from SonarQube>'

docker run --rm --network host \
  -e SONAR_HOST_URL=http://192.168.17.11:31090 \
  -e SONAR_TOKEN \
  -v "$PWD:/usr/src" \
  sonarsource/sonar-scanner-cli
```
