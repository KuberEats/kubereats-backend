# KuberEats DB Maintenance Runbook

This runbook is for internal engineering and DBA troubleshooting. It is not a
normal path for test-data creation.

## Principles

- Prefer seed scripts, backend APIs, or admin UI flows for test data.
- Use local DBeaver or local pgAdmin through SSH tunnels for inspection only.
- Keep PostgreSQL, HAProxy, and pgAdmin private.
- Never commit passwords, full connection strings, or Kubernetes Secret values.
- Never use the application role for manual data changes.

## Normal Inspection Flow

1. Open an SSH tunnel as documented in `docs/ops/db-access.md`.
2. Connect with `qa_readonly`.
3. Run SELECT-only checks.
4. Capture query purpose and result summary in the ticket or incident notes.

## Seed-Data Flow

Use this only for dev, staging, or acceptance:

1. Prefer an existing seed script or backend API.
2. If SQL is required, use `qa_seed`.
3. Keep SQL scoped to business tables only.
4. Do not touch migration or outbox tables manually.
5. Verify through the app/API after the seed completes.

## Emergency Production Fix Flow

Manual production changes require explicit approval.

1. Open or link a ticket/work item.
2. Identify affected users/orders/merchants without dumping unrelated data.
3. Take or verify a recent backup/snapshot.
4. Write SQL with a rollback plan.
5. Get SQL review from another engineer or DBA.
6. Use an approved DBA/admin role, not `kubereats_app`.
7. Execute the smallest possible change.
8. Verify with SELECT queries and application behavior.
9. Record exact commands, timestamps, and verification evidence.
10. Monitor application logs and DB health.

## Rollback Expectations

Every manual change must have one of:

- A transaction rollback before commit.
- A reverse SQL statement reviewed with the forward SQL.
- A restore plan from backup when data volume or risk is high.

## Prohibited Actions

- Publicly exposing PostgreSQL `5432` or `5433`.
- Publicly exposing pgAdmin through LoadBalancer or Ingress.
- Running seed/reset scripts against production.
- Sharing DBA or application credentials in chat, tickets, docs, or Git.
- Running `ALTER`, `DROP`, or bulk `UPDATE/DELETE` without review.
- Restarting PostgreSQL, Patroni, or HAProxy without an approved maintenance
  window or explicit incident command.

## pgAdmin

The default approach is local pgAdmin or local DBeaver over SSH tunnel. A
Kubernetes pgAdmin deployment is not currently required.

If pgAdmin is added later:

- Use a private namespace such as `db-tools`.
- Use a `ClusterIP` service only.
- Do not create Ingress.
- Do not create LoadBalancer.
- Store the pgAdmin password in a Kubernetes Secret.
- Access it only with:

```bash
kubectl -n db-tools port-forward svc/pgadmin 8080:80
```

## Quick Health Checks

From the GCP VM:

```bash
ssh -i tf-cloud-init kubereats@192.168.17.11 \
  'kubectl -n kubereats-dev rollout status deployment/kubereats-postgres-proxy'

ssh -i tf-cloud-init kubereats@192.168.17.11 \
  'kubectl -n kubereats-dev get svc,endpoints kubereats-postgres -o wide'

ssh kubereats@192.168.16.221 \
  'sudo patronictl -c /etc/patroni/patroni.yml list'
```

Expected current state:

- `pg1` is Leader.
- `pg2` is Sync Standby.
- `pg3` is Replica.
- `kubereats-postgres` is ClusterIP and has endpoints.
