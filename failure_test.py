#!/usr/bin/env python3
import sys
import time
import subprocess
import urllib.request
import json

HOST = "http://127.0.0.1:8090"

def log_result(check_name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    msg = f"[{status}] {check_name}"
    if detail:
        msg += f": {detail}"
    print(msg)
    if not passed:
        sys.exit(1)

def http_get(path):
    try:
        req = urllib.request.Request(f"{HOST}{path}")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = resp.read().decode('utf-8')
            return resp.status, json.loads(data) if data else {}
    except Exception as e:
        return 0, {}

def run_cmd(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

print("==========================================")
print("Starting Failure & Recovery Test Suite")
print("==========================================")

# 1. Stop app-01
print("[1/4] Stopping app-01 container...")
run_cmd("docker stop app-01")

# 2. Check availability during failure
print("[2/4] Measuring traffic & availability with app-01 down...")
successes = 0
errors = 0
observed_instances = set()

for _ in range(10):
    code, data = http_get("/instance")
    if code == 200 and "instance_id" in data:
        successes += 1
        observed_instances.add(data["instance_id"])
    else:
        errors += 1
    time.sleep(0.5)

log_result("Traffic Served During Failure", errors == 0 and "app-02" in observed_instances, 
           f"Successes: {successes}, Errors: {errors}, Served by: {observed_instances}")

# 3. Restore app-01
print("[3/4] Restoring app-01 container...")
run_cmd("docker start app-01")
time.sleep(5)  # Allow container to become healthy

# 4. Verify recovery
print("[4/4] Verifying recovery and traffic distribution...")
recovered_instances = set()
for _ in range(10):
    code, data = http_get("/instance")
    if code == 200 and "instance_id" in data:
        recovered_instances.add(data["instance_id"])
    time.sleep(0.5)

log_result("Backend Recovery Check", "app-01" in recovered_instances and "app-02" in recovered_instances, 
           f"Observed instances post-recovery: {recovered_instances}")

print("==========================================")
print("FAILURE AND RECOVERY TEST PASSED!")
print("==========================================")
sys.exit(0)
