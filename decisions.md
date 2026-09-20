# Technical Decisions

Record at least 5 decisions. Include assumptions and limits.

## Decision 1: NGINX Failover & Upstream Retry Strategy
- Choice: Configured NGINX upstream with `max_fails=1 fail_timeout=2s` and enabled `proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;`.
- Why: Ensures seamless high availability. If `app-01` drops, NGINX reroutes requests to `app-02` immediately without returning HTTP 502/504 errors to the end user.
- Alternative: Leaving default NGINX configuration (`proxy_next_upstream off;`), which dropped requests during backend failure.
- Trade-off: Slight sub-second latency increase for the single request that hits a failing container before rerouting to the healthy node.
- Evidence / commit: `nginx/nginx.conf` updated and verified via passing `python3 failure_test.py` [PASS].
- Production improvement: Introduce external health checks (e.g., Consul or Keepalived) and auto-scaling upstream pools.

---

## Decision 2: Multi-Stage Docker Build with Non-Root Security Enforcement
- Choice: Used `python:3.10-slim` base image and explicitly configured a non-privileged `appuser` system user to run the Flask application.
- Why: Reduces container image footprint and prevents potential privilege escalation / host takeover if an app vulnerability is exploited.
- Alternative: Standard root execution on `python:3.10` full image.
- Trade-off: Requires strict permission management (`chown`/`chmod`) during image build for log/temp directories.
- Evidence / commit: `Dockerfile` instructions and successful Trivy security scan in CI workflow.
- Production improvement: Use distroless base images (`gcr.io/distroless/python3`) and sign images with Cosign.

---

## Decision 3: Multi-Tier Network Isolation & Strict Port Binding
- Choice: Placed PostgreSQL and Redis on an isolated internal `backend` Docker network, exposing only NGINX on public port `8080`.
- Why: Ensures zero exposure of database (`5432`) and cache (`6379`) ports to the host network or public interface.
- Alternative: Binding PostgreSQL and Redis ports directly to `127.0.0.1` on the host for easier local access.
- Trade-off: Prevents developers from directly connecting host GUI tools (like DBeaver/Redis Insight) without using container exec or SSH tunnels.
- Evidence / commit: `docker-compose.yml` networks section and passing step [4/5] in `python3 validate.py`.
- Production improvement: Implement automated mTLS encryption between services using a Service Mesh (Istio/Linkerd).

---

## Decision 4: Application-Level Readiness Verification (`/ready`)
- Choice: Implemented an active `/ready` HTTP endpoint that checks live TCP/DB connection pinging to PostgreSQL and Redis.
- Why: Ensures traffic is only routed to backend containers that are fully initialized and capable of executing data transactions.
- Alternative: Basic process-level health checks (`/health` or simple HTTP ping).
- Trade-off: Introduces minimal CPU/connection overhead during frequent readiness polling.
- Evidence / commit: `app/server.py` implementation and passing step [1/5] in `python3 validate.py`.
- Production improvement: Implement structured readiness probes with circuit breakers to handle partial dependency degradation.

---

## Decision 5: Docker Volume Persistence & Scripted Physical Backups
- Choice: Utilized Docker named volumes (`postgres_data`) for state persistence across container restarts, paired with `backup.sh`/`restore.sh` using `pg_dump`.
- Why: Guarantees zero data loss during container recreation (`docker compose down && docker compose up -d`) while providing instant disaster recovery capability.
- Alternative: Host bind-mounts (`./data:/var/lib/postgresql/data`) or ephemeral in-memory storage.
- Trade-off: `pg_dump` logical backups can take longer to restore as database size grows into gigabytes compared to physical snapshotting.
- Evidence / commit: Successful persistence test during `backup.sh` / `restore.sh` execution and verified database record #5 persistence.
- Production improvement: Automate encrypted incremental S3 backups with WAL streaming (e.g., pgBackRest / AWS RDS Automated Snapshots).
