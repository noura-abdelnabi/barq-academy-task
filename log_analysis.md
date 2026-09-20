# Log Analysis Report

## Commands / Scripts
The logs were analyzed using the automated script `analyze_logs.py` as well as standard Linux/Bash tools (`jq`, `grep`, `awk`).

```bash
# Run log analysis script
python3 analyze_logs.py
```

## Results

### 1. UTC Interval & Line Counts

 **UTC Time Window:** `2026-08-20T11:00:00.015Z` to `2026-08-20T11:29:57.578Z` (~30 minutes)
 
 **Line Statistics:**
 
- `access.log`: Total lines: 726 | Valid JSON: 725 | Malformed: 1 | Duplicate lines: 5
    
- `error.log`: Total lines: 68 | Valid lines: 68 | Malformed: 0 | Duplicate lines: 0
    
- `application.log`: Total lines: 730 | Valid JSON: 729 | Malformed: 1 | Duplicate lines: 2


### 2. Distinct Client Requests & Deduplication
- **Total Unique Requests:** `720` unique requests (deduplicated via `request_id`).
 
- **Deduplication Method:** Grouped by `request_id` across `access.log` to track retries and avoid double-counting upstream attempts.

### 3. Final Client Status Counts & Error Rate

- **Status Code Breakdown:**
    - `200 OK`: 620
    - `404 Not Found`: 10
    - `502 Bad Gateway`: 40
    - `503 Service Unavailable`: 47
    - `504 Gateway Timeout`: 8

- **Total Requests (Denominator):** 725 requests
- **Error Rate:** **14.48%** (105 non-2xx responses / 725 total requests)

### 4. Failure Analysis by Paths and Backends

- **Failures by Path:**
    - `/records`: 26 failures (Database connection issues)
    - `/counter`: 26 failures (Redis connection issues)
    - `/ready`: 23 failures
    - `/missing`: 10 failures (Intentional 404s)
    - `/health`: 10 failures
    - `/`: 10 failures

- **Failures by Upstream Backend:**
    - `172.23.0.12:8080` (app-02): **73 failures** (Primary failure point due to connection refused / process down)
    - `172.23.0.11:8080` (app-01): **32 failures** (Secondary failures related to database/cache timeout or unreadiness)

### 5. Latency Metrics

- **Median Latency:** `54.00 ms`
- **P95 Latency:** `2001.00 ms` (2.001 seconds)
- **Percentile Method & Units:** Nearest-rank method calculated in milliseconds (`ms`). The P95 spike is caused by upstream connection timeouts (504 HTTP status).


## Timeline and Correlated Examples

### 6. Upstream Retries

- Upstream retries occurred when NGINX failed to connect to `172.23.0.12:8080` and failed over to `172.23.0.11:8080`.
- Requests that succeeded after a retry eventually logged a 200 status with multiple upstream addresses in the NGINX access log line.

### 7. Incident Timeline

- **11:00 - 11:05 UTC:** Normal traffic flow; all endpoints respond with `200 OK`.
- **11:05 - 11:15 UTC:** `app-02` (`172.23.0.12`) drops offline. NGINX logs `111: Connection refused` in `error.log`. 502/503 status codes spike in `access.log`.
- **11:15 - 11:25 UTC:** Intermittent 504 Gateway Timeouts occur on `/records` and `/counter` endpoints when PostgreSQL/Redis connectivity times out.
- **11:25 - 11:30 UTC:** Traffic stabilizes as failover mechanisms route requests to `app-01`.

### 8. Correlated Request Examples

#### Successful Request Correlation

- **Request ID:** `lab-000002`
- **Timestamp:** `2026-08-20T11:00:02.532Z`
- **Access Log:** `{"timestamp":"2026-08-20T11:00:02.532Z","request_id":"lab-000002","method":"GET","path":"/health","status":200,"upstream":"172.23.0.12:8080","request_time":0.032}`
- **Application Log:** `{"timestamp": "2026-08-20T11:00:02.532Z", "level": "INFO", "request_id": "lab-000002", "instance_id": "app-02", "method": "GET", "path": "/health", "status": 200, "duration_ms": 32.0}`

#### Failed Request Correlation

- **Request ID:** `lab-000122`
- **Timestamp:** `2026-08-20T11:05:02Z`
- **Access Log:** `{"timestamp":"2026-08-20T11:05:02.100Z","request_id":"lab-000122","method":"GET","path":"/health","status":502,"upstream":"172.23.0.12:8080","upstream_status":"502"}`
- **Error Log:** `2026/08/20 11:05:02 [error] ... connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000122 ... upstream: "http://172.23.0.12:8080/health"`
- **Application Log:** *(No entry - application process on `app-02` was down and never received the request)*


## Conclusions and Limits

### 9. Proxy vs. Dependency Errors

- **Proxy/Connectivity Issues:** Indicated by `111: Connection refused` in `error.log` and `502 Bad Gateway` in `access.log`. Proves that the NGINX proxy was unable to establish a TCP socket connection with `app-02`.
- **Dependency/Application Issues:** Indicated by `504 Gateway Timeout` and errors on `/records` or `/counter`. Proves that Flask received the request but timed out waiting for PostgreSQL or Redis.

### 10. Limits of Log Evidence

- **What logs do NOT prove:**
    - Logs do not reveal CPU/RAM resource starvation on host or container level.
    - Logs do not confirm if PostgreSQL/Redis crashed or had firewall rules blocking internal container traffic.


- **Next Steps in Running Environment:**
    - Inspect `docker status` and `docker stats` for container status and resource usage.
    - Test internal container connectivity using `curl` / `nc` inside the container networks.


