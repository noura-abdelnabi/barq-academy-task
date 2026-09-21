#!/usr/bin/env python3
import sys
import time
import socket
import json
import urllib.request
import urllib.error

HOST = "http://127.0.0.1:8090"
MAX_RETRIES = 15
SLEEP_SEC = 2

def log_result(check_name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    msg = f"[{status}] {check_name}"
    if detail:
        msg += f": {detail}"
    print(msg)
    if not passed:
        sys.exit(1)

def http_get(path):
    url = f"{HOST}{path}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = resp.read().decode('utf-8')
            return resp.status, json.loads(data) if data else {}
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, {}

print("==========================================")
print("Starting Validation Suite for Barq App")
print("==========================================")

# 1. Bounded wait for readiness
print("[1/5] Waiting for application readiness (/ready)...")
ready = False
for _ in range(MAX_RETRIES):
    code, data = http_get("/ready")
    if code == 200 and data.get("status") == "ready":
        ready = True
        break
    time.sleep(SLEEP_SEC)

log_result("Service Readiness Check (/ready)", ready)

# 2. Test Required Endpoints
print("[2/5] Testing Required Endpoints...")
endpoints = ["/", "/health", "/ready", "/counter", "/records"]
for ep in endpoints:
    code, _ = http_get(ep)
    log_result(f"Endpoint GET {ep}", code == 200, f"HTTP {code}")

# 3. Verify Load Balancing
print("[3/5] Verifying Load Balancing across app instances...")
instances = set()
for _ in range(10):
    _, data = http_get("/instance")
    if "instance_id" in data:
        instances.add(data["instance_id"])

is_balanced = "app-01" in instances and "app-02" in instances
log_result("Load Balancing Check", is_balanced, f"Observed instances: {instances}")

# 4. Check Prohibited Host Ports (Network Isolation)
print("[4/5] Checking Network Isolation (Prohibited Host Ports)...")
def check_port_closed(port, name):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    # connect_ex returns 0 if port is open
    return result != 0

log_result("Port 5432 Isolated (PostgreSQL)", check_port_closed(5432, "PostgreSQL"))
log_result("Port 6379 Isolated (Redis)", check_port_closed(6379, "Redis"))

# 5. Test Record Creation (POST /records)
print("[5/5] Testing Record Creation (POST /records)...")
try:
    payload = json.dumps({"title": "CI Validation Task"}).encode('utf-8')
    req = urllib.request.Request(f"{HOST}/records", data=payload, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=3) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        created = "record" in data and data["record"].get("title") == "CI Validation Task"
        log_result("Record Creation (POST /records)", created, f"Response: {data}")
except Exception as e:
    log_result("Record Creation (POST /records)", False, str(e))

print("==========================================")
print("ALL VALIDATION CHECKS PASSED SUCCESSFULLY!")
print("==========================================")
sys.exit(0)
