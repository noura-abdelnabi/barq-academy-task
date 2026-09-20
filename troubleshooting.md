# Troubleshooting Journal

Keep chronological entries. Copy this block for each meaningful investigation.

## Entry 1 / 2026-09-20 / 18:15:00
- Symptom: NGINX returned HTTP 502 Bad Gateway and request errors during `python3 failure_test.py` when `app-01` was stopped.
- Hypothesis: NGINX upstream was configured to drop connections or not retry alternative available backends when an upstream host becomes unreachable.
- Command or test: `cat nginx/nginx.conf` and `python3 failure_test.py`.
- Actual output: `[FAIL] Traffic Served During Failure: Successes: 4, Errors: 6, Served by: {'app-02'}`.
- Failed attempt and what changed your thinking: Attempted to restart NGINX without modifying `nginx.conf`, assuming it was a temporary container startup delay. The failure persisted consistently across re-runs, proving it was a static configuration issue rather than a startup race condition.
- Root cause: `nginx/nginx.conf` had `max_fails=0;` and `proxy_next_upstream off;`, explicitly instructing NGINX never to mark an instance as down and never to failover to `app-02`.
- Fix: Updated `nginx/nginx.conf` upstream definition to `max_fails=1 fail_timeout=2s` and added `proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;` under `location /`.
- Retest evidence: Executed `docker compose restart nginx && python3 failure_test.py` resulting in `[PASS] Traffic Served During Failure: Successes: 10, Errors: 0, Served by: {'app-02'}`.
- Related commit: `fix(nginx): enable upstream proxy_next_upstream failover`
- Remaining uncertainty: None. Rerunning `failure_test.py` confirmed 0 errors during single-backend downtime.

---

## Entry 2 / 2026-09-20 / 18:35:00
- Symptom: PostgreSQL database connection errors or initial socket access issues during container initialization in early setup.
- Hypothesis: The application container attempted to execute database migrations/queries before the PostgreSQL service had finished opening port 5432.
- Command or test: `docker compose logs app-01` and `python3 validate.py`.
- Actual output: `[1/5] Waiting for application readiness (/ready)...` hanging or retrying before readiness check succeeded.
- Failed attempt and what changed your thinking: Adding simple delay `sleep` statements in scripts. Realized non-deterministic sleeps are flaky and an application-level `/ready` probe checking actual TCP/DB pinging is required.
- Root cause: Container start order (`depends_on`) only waits for container creation, not database engine readiness.
- Fix: Ensured the `/ready` endpoint in `app/server.py` performs active connection polling to both PostgreSQL and Redis, integrated with Docker compose `healthcheck` dependencies.
- Retest evidence: `python3 validate.py` passed step [1/5] `Service Readiness Check (/ready)` instantly once services became healthy.
- Related commit: `feat(app): enhance readiness probe with database health checks`
- Remaining uncertainty: Heavy database load at startup could slightly delay initial readiness verification under cold boots.
