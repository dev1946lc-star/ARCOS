import requests
import json
import time

BASE_URL = "http://localhost:8000"

def get(path):
    print(f"GET {path}")
    resp = requests.get(f"{BASE_URL}{path}")
    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code}")
        return None
    return resp.json()

def post(path, payload={}):
    print(f"POST {path}")
    resp = requests.post(f"{BASE_URL}{path}", json=payload)
    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code} - {resp.text}")
        return None
    return resp.json()

def audit():
    print("--- STARTING AUDIT ---")
    
    # Let the simulation run for a few seconds to generate some transactions
    print("Waiting 5s for sim transactions...")
    time.sleep(5)
    
    health = get("/system/health")
    perf = get("/system/performance")
    persist = get("/system/persistence")
    valid = get("/system/validation")
    trans = get("/transactions")
    econ = get("/economics/summary")
    
    first_tx_job_id = None
    if trans and trans.get("transactions"):
        for t in trans["transactions"]:
            if t.get("job_id"):
                first_tx_job_id = t["job_id"]
                break
                
    replay = None
    if first_tx_job_id:
        replay = get(f"/transactions/replay/{first_tx_job_id}")

    test_overload = post("/system/test/overload", {"burst_size": 200, "queue_limit": 32, "processing_delay_ms": 15})
    
    print("\n--- AUDIT RESULTS ---")
    data = {
        "health": health,
        "performance": perf,
        "persistence": persist,
        "validation": valid,
        "transactions_count": len(trans.get("transactions", [])) if trans else 0,
        "transactions_summary": trans.get("summary", {}) if trans else {},
        "economics": econ,
        "replay": replay,
        "overload": test_overload
    }
    
    with open("audit_results.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Results saved to audit_results.json")

if __name__ == "__main__":
    audit()
