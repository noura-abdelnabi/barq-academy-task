
```markdown
# Barq Academy - DevOps Assessment (Part 1 to 4 Complete)

## 1. Quick Start & Operational Runbook

### Setup Environment
```bash
cp config/app.env.example config/app.env

```

### Build and Start Services

```bash
docker compose up -d --build

```

### Check Service Status & Logs

```bash
docker compose ps
docker compose logs -f

```

### Run Validation Suite

```bash
python3 validate.py

```

### Run Failure and Recovery Tests

```bash
python3 failure_test.py

```

### Backup and Restore Database

```bash
# Create Backup
./backup.sh

# Restore Backup
./restore.sh backups/latest.sql

```

### Cleanup Environment

```bash
docker compose down -v

```

---

## 2. Assessment Questions & Architecture Answers

### Q1: What failed first? What proved the cause? Which failed attempt taught you something?

* **What Failed First:** The NGINX load balancer initially returned `502 Bad Gateway` and HTTP errors during container failure tests rather than failing over cleanly.
* **Proof of Cause:** Reviewing `nginx/nginx.conf` revealed `max_fails=0` and `proxy_next_upstream off;`, which explicitly prevented NGINX from rerouting failed requests to `app-02`.
* **Lesson Learned:** Misconfigured reverse proxies can completely negate high-availability container architecture. Enabling proper `proxy_next_upstream` settings is essential for zero-downtime failover.

### Q2: What patterns did the logs reveal? How did you avoid double-counting requests?

* **Log Patterns:** Standardized JSON access logs showed timestamp, `upstream_addr`, and status codes, clearly tracking request distribution between `app-01` and `app-02`.
* **Avoiding Double-Counting:** Retried requests through NGINX generate multiple log entries (one for the failed upstream and one for the successful backup). We filtered unique request IDs (`X-Request-ID`) in `log_analysis.md` to ensure each client request was counted exactly once.

### Q3: How do requests flow? Why these ports, networks, and readiness checks?

* **Request Flow:** `Client` $\rightarrow$ `NGINX (Port 8080)` $\rightarrow$ `Flask Backends (app-01 / app-02 on Port 8080 internal)` $\rightarrow$ `PostgreSQL (Port 5432 internal)` & `Redis (Port 6379 internal)`.
* **Ports & Networks:** Only port `8080` is exposed to the host for security. Database and Cache ports (`5432`, `6379`) are isolated inside the `backend` Docker network and prohibited from host binding.
* **Readiness Checks:** The `/ready` endpoint verifies active connectivity to both PostgreSQL and Redis before considering an app instance healthy, preventing NGINX from routing traffic to unready instances.

### Q4: Why these timeouts, retries, restart settings, and resource limits?

* **Timeouts & Retries:** `proxy_connect_timeout 2s` and `proxy_next_upstream error timeout http_502 http_503` ensure sub-second failover to `app-02` if `app-01` fails, preventing end-user HTTP errors.
* **Restart Policy:** `restart: unless-stopped` guarantees container auto-healing upon runtime crash without needing manual host intervention.
* **Resource Limits:** Limits memory and CPU per container to prevent memory leaks in one instance from crashing the entire host server.

### Q5: When should validation fail? What does green CI prove, or not prove?

* **Validation Fails When:** Endpoint status code $\neq 200$, `/ready` reports database/redis disconnect, traffic load balancing fails to hit all instances, or backend ports (5432/6379) are exposed to the host.
* **What Green CI Proves:** Proves build reproducibility, environment startup, network isolation, database persistence, and end-to-end operational functionality in a clean environment.
* **What Green CI Does NOT Prove:** Does not guarantee performance under extreme stress (>10k RPS), long-term disk growth handling, or zero zero-day security vulnerabilities.

### Q6: Which single points of failure (SPOF) remain? How would you fix them in production?

* **Current SPOFs:**
1. Single NGINX entrypoint.
2. Single PostgreSQL database instance.
3. Single Redis node.


* **Production Fixes:**
1. Deploy multiple NGINX instances behind a cloud Load Balancer (AWS ALB / Cloudflare).
2. Implement PostgreSQL Primary-Replica replication with automated failover (Patroni / AWS RDS Multi-AZ).
3. Deploy Redis Sentinel or Redis Cluster for high availability.



### Q7: What would you improve? How did you verify AI-assisted work?

* **Improvements:** Implement Prometheus/Grafana monitoring, centralized logging via ELK stack, and automated database backup rotation to S3.
* **Verification of AI-Assisted Work:** Every code change and configuration script generated was tested locally using `validate.py`, `failure_test.py`, and verified in the GitHub Actions CI environment before finalizing.

---

## 3. Verification & CI Status

* **GitHub Actions Status:** Passed (Green)
* **Trivy Vulnerability Scan:** Completed
* **Disaster Recovery Test:** Verified via `backup.sh` & `restore.sh`

```

---

