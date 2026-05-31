# Security Hardening TODO

## Verification Service Numeric Non-Root User

Phase 1.5 keeps `verification-service` deployable by not setting `runAsNonRoot: true` in the Kubernetes Deployment. The current image uses a named non-root user (`USER app`) rather than a numeric UID, so kubelet cannot verify that the container is non-root when `runAsNonRoot: true` is enabled.

Production hardening TODO:

- Update the verification image to use a fixed numeric non-root UID/GID, for example `10001:10001`.
- Update the Dockerfile to create the user/group with that fixed UID/GID.
- Set `USER 10001:10001` in the Dockerfile.
- Add `runAsNonRoot: true` back to the Kubernetes securityContext.
- Optionally add `runAsUser: 10001` and `runAsGroup: 10001` in the Deployment.

This is not a Phase 1.5 blocker, but it must be fixed before production promotion.
