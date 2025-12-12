import os
import time
import random
import string
import json
from datetime import datetime
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "devices/telemetry")
DEVICE_COUNT = int(os.getenv("DEVICE_COUNT", 5))
PUBLISH_INTERVAL = float(os.getenv("PUBLISH_INTERVAL", 1.0))

# helper randomization
def rand_imei():
    # 15-digit IMEI-style numeric string
    return "".join(random.choice("0123456789") for _ in range(15))

def rand_project():
    return str(random.randint(100000, 999999))

def rand_site():
    return random.choice(["AGRAI00", "SITE01", "SITE02", "NYC001", "DELTA1"])

def rand_device_id():
    return str(random.randint(1, 999))

def current_time_str():
    return datetime.now().strftime("%H:%M:%S")

def current_date_str():
    return datetime.now().strftime("%d/%m/%y")

def make_message_for_device(base):
    # Compose CSV message fields q0..q20
    # Keep q8 sensor as "0.00" per requirement
    q0 = "*"
    q1 = "11"
    q2 = "1001"
    q3 = base["imei"]
    q4 = base["project"]
    q5 = base["site"]
    q6 = base["device"]
    q7 = "2001"
    q8 = "0.00"
    q9 = f"{random.uniform(15.0, 25.0):.1f}"   # a1
    q10 = f"{random.uniform(30.0, 60.0):.1f}"  # a2
    q11 = f"{random.uniform(0.5, 10.0):.2f}"   # val
    q12 = current_time_str()
    q13 = current_date_str()
    q14 = str(random.randint(5, 31))  # csq like
    q15 = str(random.randint(0, 2))
    q16 = str(random.randint(1, 200))
    q17 = str(random.randint(5, 100))  # battery %
    q18 = "100"
    q19 = "0"
    q20 = "0"
    parts = [q0,q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11,q12,q13,q14,q15,q16,q17,q18,q19,q20]
    return ",".join(parts)

def main():
    # create devices
    devices = []
    for i in range(DEVICE_COUNT):
        devices.append({
            "imei": rand_imei(),
            "project": rand_project(),
            "site": rand_site(),
            "device": rand_device_id()
        })

    client = mqtt.Client(client_id=f"sim-{random.randint(1000,9999)}")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()
    print(f"Simulating {len(devices)} devices -> mqtt://{MQTT_HOST}:{MQTT_PORT}/{MQTT_TOPIC}")
    try:
        while True:
            for d in devices:
                msg = make_message_for_device(d)
                client.publish(MQTT_TOPIC, msg)
            time.sleep(PUBLISH_INTERVAL)
    except KeyboardInterrupt:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()

