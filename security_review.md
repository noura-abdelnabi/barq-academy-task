# Security and Production-Readiness Review

Record at least 8 concrete risks or improvements relevant to your final solution.

---

### Finding 1: Secrets Management & Hardcoded Credentials
- **Risk and evidence:** Environment configuration and database credentials stored in local text files or example templates without runtime secrets injection (`config/app.env`).
- **Impact:** Credentials could be inadvertently committed to version control, leading to unauthorized database access.
- **Implemented fix / commit:** Created `config/app.env.example` as a template, added actual `.env` files to `.gitignore`, and set default environment variable overrides in `docker-compose.yml`.
- **Production follow-up:** Migrate secret management to HashiCorp Vault or AWS Secrets Manager with dynamic credential rotation.
- **How to verify:** Check Git status/history to verify no sensitive `.env` files with production keys are tracked in the repository.

---

### Finding 2: Unnecessary Database and Cache Port Exposure
- **Risk and evidence:** Exposing storage layer ports (`5432` for PostgreSQL and `6379` for Redis) directly on host network interfaces (`0.0.0.0`).
- **Impact:** Exposes data stores to external network scanning, brute-force attacks, or direct unauthorized access bypassing application authorization.
- **Implemented fix / commit:** Enforced internal network isolation in `docker-compose.yml`. Ports `5432` and `6379` are bound strictly within the internal `backend` Docker network and excluded from host `ports` mapping.
- **Production follow-up:** Apply Kubernetes NetworkPolicies or cloud security group rules to restrict traffic to/from database instances.
- **How to verify:** Run `python3 validate.py` (Step [4/5]) or `nc -zv 127.0.0.1 5432` from the host to confirm host connection refusal.

---

### Finding 3: Privileged Container User Execution
- **Risk and evidence:** Container applications default to running as the system `root` user inside the container environment.
- **Impact:** If an application Remote Code Execution (RCE) vulnerability is exploited, the attacker gains root-level access inside the container and increases the risk of host breakout.
- **Implemented fix / commit:** Updated `Dockerfile` to create a dedicated, non-privileged system user (`appuser`) and switched runtime execution via `USER appuser`.
- **Production follow-up:** Enforce Kubernetes security contexts (`runAsNonRoot: true`, `readOnlyRootFilesystem: true`, and drop all Linux capabilities `CAP_DROP_ALL`).
- **How to verify:** Execute `docker exec app-01 whoami` to confirm execution as `appuser` (UID $\neq 0$).

---

### Finding 4: Container Base Image Selection & Vulnerability Surface
- **Risk and evidence:** Using bloated base images containing unneeded system utilities increases image size and CVE exposure surface.
- **Impact:** Outdated base packages increase susceptibility to known critical or high severity OS vulnerabilities.
- **Implemented Fix / Commit:** Adopted `python:3.10-slim` as the standard base image and integrated **Trivy Vulnerability Scanner** directly into the GitHub Actions CI workflow (`.github/workflows/ci.yml`).
- **Production follow-up:** Migrate to Distroless base images (`gcr.io/distroless/python3`), implement image signing via Cosign, and enable automated vulnerability scans in container registries (ECR/GCR).
- **How to verify:** Inspect GitHub Actions CI workflow logs under the `Run Trivy Vulnerability Scanner` step.

---

### Finding 5: Single Point of Failure in Application Failover
- **Risk and evidence:** Initial NGINX proxy configuration used `max_fails=0` and `proxy_next_upstream off;`.
- **Impact:** Stopping or crashing one backend instance (`app-01`) immediately caused user-facing HTTP 502/504 Bad Gateway errors instead of seamless load distribution.
- **Implemented fix / commit:** Reconfigured `nginx/nginx.conf` with `max_fails=1 fail_timeout=2s` and enabled `proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;`.
- **Production follow-up:** Deploy redundant NGINX instances across availability zones behind an AWS ALB / Cloudflare Global Load Balancer.
- **How to verify:** Run `python3 failure_test.py` to confirm zero dropped requests when `app-01` is stopped.

---

### Finding 6: Unpersistent Database Storage & Disaster Recovery Risks
- **Risk and evidence:** Ephemeral database containers risk total data destruction upon container deletion or host reboots.
- **Impact:** Permanent loss of user transactions, operational records, and database state.
- **Implemented fix / commit:** Bound PostgreSQL container data to Docker named volume `postgres_data` and implemented automated disaster recovery scripts (`backup.sh` and `restore.sh`).
- **Production follow-up:** Implement continuous Point-in-Time Recovery (PITR), WAL archiving, and automated offsite encrypted S3 backups.
- **How to verify:** Run `./backup.sh`, destroy containers via `docker compose down -v`, restore with `./restore.sh backups/latest.sql`, and query `http://127.0.0.1:8080/records`.

---

### Finding 7: Unstructured Logging & Data Leakage Risks
- **Risk and evidence:** Standard application stdout logs lacking structured format and potential exposure of sensitive query strings/headers.
- **Impact:** Hinders automated log ingestion/parsing and raises security/privacy risks if tokens or PII are printed in plain text logs.
- **Implemented fix / commit:** Standardized NGINX logging in `nginx/nginx.conf` using JSON formatting with explicit string escaping (`escape=json`), capturing critical request metrics (`request_id`, `upstream_status`, `request_time`).
- **Production follow-up:** Stream JSON logs to a centralized ELK or Datadog cluster with automated PII masking and log retention policies.
- **How to verify:** Inspect NGINX logs via `docker compose logs nginx` to verify structured valid JSON log outputs.

---

### Finding 8: Passive Monitoring & Blind Service Startup
- **Risk and evidence:** Relying solely on TCP port checks or basic process status can report an application as "healthy" before its database dependencies are reachable.
- **Impact:** Load balancer forwards live user requests to containers that throw 500 errors due to unestablished database connections.
- **Implemented fix / commit:** Implemented an active `/ready` probe in `app/server.py` that executes live ping checks to both PostgreSQL and Redis, integrated with Docker Compose healthchecks.
- **Production follow-up:** Implement Prometheus metrics endpoints (`/metrics`) and Grafana alerting for dynamic SLA/SLO tracking.
- **How to verify:** Query `curl http://127.0.0.1:8080/ready` and verify HTTP 200 response with underlying dependency status checks.
