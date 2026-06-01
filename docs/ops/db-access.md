# KuberEats DB Access

This document defines the approved internal path for engineers and DBAs to
inspect the KuberEats PostgreSQL HA database with local DBeaver or local
pgAdmin. Do not expose PostgreSQL or pgAdmin to the public Internet.

## Current Topology

- Kubernetes namespace: `kubereats-dev`
- Runtime DB secret: `kubereats-db-app`, key `DATABASE_URL`
- Kubernetes DB service: `kubereats-postgres`
- Service type: `ClusterIP`
- Current service IP: `10.100.98.5`
- Writer port: `5432`
- Reader port: `5433`
- HAProxy deployment: `kubereats-postgres-proxy`
- Patroni nodes:
  - `pg1` `192.168.16.221`, currently Leader
  - `pg2` `192.168.16.222`, Sync Standby
  - `pg3` `10.250.0.3`, Replica

Use the HAProxy writer endpoint for write-capable tools. Do not pin tools to
`pg1`; Patroni can fail over.

## Approved Access Pattern

Use SSH tunneling from an engineer workstation to the Kubernetes master, then
forward to the internal HAProxy ClusterIP. The database remains private.

Preferred writer tunnel:

```bash
ssh -i tf-cloud-init \
  -L 15432:10.100.98.5:5432 \
  kubereats@192.168.17.11
```

Optional reader tunnel for read-only investigations:

```bash
ssh -i tf-cloud-init \
  -L 15433:10.100.98.5:5433 \
  kubereats@192.168.17.11
```

If the workstation cannot route to `192.168.17.11`, use the GCP VM as the jump
host. Replace `<gcp-user>` and `<gcp-vm-public-host>` with the real SSH target:

```bash
ssh -J <gcp-user>@<gcp-vm-public-host> \
  -i tf-cloud-init \
  -L 15432:10.100.98.5:5432 \
  kubereats@192.168.17.11
```

Two-step tunnel alternative:

```bash
# Terminal 1, on the GCP VM:
ssh -i tf-cloud-init \
  -N -L 15432:10.100.98.5:5432 \
  kubereats@192.168.17.11

# Terminal 2, from the workstation to the GCP VM:
ssh -N -L 15432:127.0.0.1:15432 <gcp-user>@<gcp-vm-public-host>
```

Use direct `pg1` tunneling only for Patroni/node troubleshooting when HAProxy is
unavailable and the DBA explicitly accepts that the tunnel is pinned to one
node:

```bash
ssh -i tf-cloud-init \
  -L 15432:192.168.16.221:5432 \
  kubereats@192.168.17.11
```

## DBeaver Or Local pgAdmin Profile

Use these values after opening the tunnel:

| Field | Value |
| --- | --- |
| Host | `127.0.0.1` |
| Port | `15432` for writer, `15433` for reader |
| Database | `kubereats` |
| Username | `qa_readonly` for inspection, `qa_seed` only for approved non-production seed work |
| Password | From the approved secret store or DBA handoff, never from Git |
| SSL | Disabled inside the SSH tunnel unless DBA enables DB-side SSL |

Do not use the application DB user (`kubereats_app`) for manual maintenance.
That user is for backend services only.

## Internal Kubernetes pgAdmin

An internal-only pgAdmin instance can run in Kubernetes for DBA/debug use. It
must stay private:

- Namespace: `db-tools`
- Deployment: `pgadmin`
- Service: `pgadmin`
- Service type: `NodePort`
- NodePort: `31091`
- Allowed source CIDR: `192.168.16.0/20`
- Public Ingress: none
- Public LoadBalancer: none

Preferred access is from the internal network only. Because the Service uses
`externalTrafficPolicy: Local`, connect to the internal IP of the node currently
hosting the pgAdmin pod:

```bash
ssh -i tf-cloud-init kubereats@192.168.17.11 \
  'kubectl -n db-tools get pod -l app.kubernetes.io/name=pgadmin -o wide'
```

Then open:

```text
http://<pgadmin-node-internal-ip>:31091
```

Current example at the time of writing:

```text
http://192.168.17.22:31091
```

The SSH tunnel remains available as a fallback:

```bash
ssh -i tf-cloud-init \
  -L 8080:127.0.0.1:8080 \
  kubereats@192.168.17.11 \
  'kubectl -n db-tools port-forward --address 127.0.0.1 svc/pgadmin 8080:80'
```

Then open:

```text
http://127.0.0.1:8080
```

pgAdmin login:

| Field | Value |
| --- | --- |
| Email | `dba@kubereats.internal` |
| Password | Stored in Kubernetes Secret `db-tools/pgadmin-secret`, key `PGADMIN_DEFAULT_PASSWORD` |

Retrieve the password only from an authorized shell; do not paste it into chat
or commit it:

```bash
ssh -i tf-cloud-init kubereats@192.168.17.11 \
  "kubectl -n db-tools get secret pgadmin-secret \
    -o jsonpath='{.data.PGADMIN_DEFAULT_PASSWORD}' | base64 -d; echo"
```

After logging in, add a server manually:

| Field | Writer value | Reader value |
| --- | --- | --- |
| Host | `10.100.98.5` | `10.100.98.5` |
| Port | `5432` | `5433` |
| Database | `kubereats` | `kubereats` |
| Username | `qa_readonly` for inspection, `qa_seed` only for approved non-production seed work | `qa_readonly` |
| Password | From the approved secret store or DBA handoff | From the approved secret store or DBA handoff |

Do not store the application DB user password in pgAdmin.

## Account Usage

- `qa_readonly`: SELECT-only troubleshooting, reporting, and schema inspection.
- `qa_seed`: staging/dev/acceptance seed-data DML only, after approval.
- `kubereats_app`: backend runtime only; no human logins.
- `postgres` or DBA admin role: DBA-only emergency and migration operations.

Testing data should normally be created through seed scripts, backend APIs, or
the admin UI. pgAdmin and DBeaver are internal debug tools, not normal product
data entry paths.

## Validation Commands

From the GCP VM:

```bash
ssh -i tf-cloud-init kubereats@192.168.17.11 \
  'kubectl -n kubereats-dev get svc kubereats-postgres -o wide'

ssh -i tf-cloud-init kubereats@192.168.17.11 \
  'timeout 3 bash -lc "</dev/tcp/10.100.98.5/5432" && echo writer-ok'

ssh -i tf-cloud-init kubereats@192.168.17.11 \
  'timeout 3 bash -lc "</dev/tcp/10.100.98.5/5433" && echo reader-ok'
```

From the local machine after opening the tunnel:

```bash
psql 'postgresql://qa_readonly@127.0.0.1:15432/kubereats' \
  -c 'select current_database(), current_user, pg_is_in_recovery();'
```

Do not paste passwords into shell history. Prefer `.pgpass`, a password manager,
or the DBeaver/pgAdmin encrypted password store.

## Prohibited

- Do not expose PostgreSQL `5432` or `5433` with a public firewall rule.
- Do not create a public LoadBalancer or public Ingress for pgAdmin.
- Do not commit DB passwords, full `DATABASE_URL` values, or base64 Secret YAML.
- Do not use `kubereats_app` for human updates.
- Do not seed, reset, or bulk-edit production directly.
