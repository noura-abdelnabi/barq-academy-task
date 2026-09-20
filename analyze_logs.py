import json
import re
from datetime import datetime
import statistics

access_file = "logs/access.log"
error_file = "logs/error.log"
app_file = "logs/application.log"

print("=== 1. UTC Interval & Line Counts ===")
def analyze_file(filename, is_json=True):
    total = 0
    valid = 0
    malformed = 0
    lines_seen = set()
    duplicates = 0
    timestamps = []

    with open(filename, 'r') as f:
        for line in f:
            total += 1
            raw_line = line.strip()
            if not raw_line:
                continue
            if raw_line in lines_seen:
                duplicates += 1
            else:
                lines_seen.add(raw_line)

            if is_json:
                try:
                    data = json.loads(raw_line)
                    valid += 1
                    if "timestamp" in data:
                        timestamps.append(data["timestamp"])
                except Exception:
                    malformed += 1
            else:
                if "[error]" in raw_line or "[warn]" in raw_line or "connect() failed" in raw_line:
                    valid += 1
                    match = re.match(r"^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})", raw_line)
                    if match:
                        timestamps.append(match.group(1))
                else:
                    valid += 1

    return total, valid, malformed, duplicates, timestamps

acc_tot, acc_val, acc_mal, acc_dup, acc_ts = analyze_file(access_file, True)
err_tot, err_val, err_mal, err_dup, err_ts = analyze_file(error_file, False)
app_tot, app_val, app_mal, app_dup, app_ts = analyze_file(app_file, True)

print(f"access.log: Total={acc_tot}, Valid={acc_val}, Malformed={acc_mal}, Duplicates={acc_dup}")
print(f"error.log:  Total={err_tot}, Valid={err_val}, Malformed={err_mal}, Duplicates={err_dup}")
print(f"application.log: Total={app_tot}, Valid={app_val}, Malformed={app_mal}, Duplicates={app_dup}")

all_ts = sorted(acc_ts + app_ts)
if all_ts:
    print(f"Overall UTC Time Range: {all_ts[0]} to {all_ts[-1]}")

print("\n=== 2. Distinct Client Requests & Deduplication ===")
req_ids = set()
retries = 0
with open(access_file, 'r') as f:
    for line in f:
        try:
            d = json.loads(line)
            rid = d.get("request_id")
            if rid:
                if rid in req_ids:
                    retries += 1
                else:
                    req_ids.add(rid)
        except:
            pass
print(f"Total Unique Requests (by request_id): {len(req_ids)}")

print("\n=== 3. Status Counts, Error Rate, Latencies (Median & P95) ===")
statuses = {}
latencies = []
with open(access_file, 'r') as f:
    for line in f:
        try:
            d = json.loads(line)
            st = d.get("status")
            statuses[st] = statuses.get(st, 0) + 1
            if "request_time" in d:
                latencies.append(d["request_time"] * 1000)
        except:
            pass

print(f"Status Counts: {statuses}")
total_requests = sum(statuses.values())
error_requests = sum(v for k, v in statuses.items() if k and k >= 400)
print(f"Total Requests (Denominator): {total_requests}")
if total_requests > 0:
    print(f"Error Rate: {(error_requests/total_requests)*100:.2f}%")

if latencies:
    sorted_lat = sorted(latencies)
    median_lat = statistics.median(sorted_lat)
    p95_index = int(len(sorted_lat) * 0.95)
    p95_lat = sorted_lat[p95_index]
    print(f"Median Latency: {median_lat:.2f} ms")
    print(f"P95 Latency: {p95_lat:.2f} ms (Method: Nearest-rank)")

print("\n=== 4. Failures by Path and Upstream Backend ===")
path_failures = {}
upstream_failures = {}
with open(access_file, 'r') as f:
    for line in f:
        try:
            d = json.loads(line)
            if d.get("status", 0) and d.get("status") >= 400:
                p = d.get("path")
                u = d.get("upstream")
                path_failures[p] = path_failures.get(p, 0) + 1
                upstream_failures[u] = upstream_failures.get(u, 0) + 1
        except:
            pass
print(f"Failures by Path: {path_failures}")
print(f"Failures by Upstream Backend: {upstream_failures}")
