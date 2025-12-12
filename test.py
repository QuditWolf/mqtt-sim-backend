import time
import requests

BACKEND = "http://localhost:8000/api"

def list_devices():
    try:
        r = requests.get(f"{BACKEND}/devices", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("Error listing devices:", e)
        return []

def get_latest(imei):
    try:
        r = requests.get(f"{BACKEND}/devices/{imei}/latest", timeout=5)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error fetching latest for {imei}:", e)
        return None

def main():
    print("Monitoring device updates...\n")
    last_seen = {}  # imei → last id printed

    while True:
        devices = list_devices()
        if not devices:
            print("No devices yet. Waiting...")
            time.sleep(2)
            continue

        for dev in devices:
            imei = dev["imei"]
            latest = get_latest(imei)
            if not latest:
                continue
            
            # Only print when a new DB row appears
            row_id = latest["id"]
            if imei not in last_seen or row_id != last_seen[imei]:
                last_seen[imei] = row_id
                print(f"[{imei}]  time={latest['time']}  val={latest['q11']}  batt={latest['battery']}  id={row_id}")

        time.sleep(1)

if __name__ == "__main__":
    main()

