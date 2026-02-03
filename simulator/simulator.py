import os
import time
import random
from datetime import datetime
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "devices/telemetry")
DEVICE_COUNT = int(os.getenv("DEVICE_COUNT", 3))
SENSORS_PER_DEVICE = int(os.getenv("SENSORS_PER_DEVICE", 16))
PUBLISH_INTERVAL = float(os.getenv("PUBLISH_INTERVAL", 1.0))

# Sensor types available
SENSOR_TYPES = [
    "H2", "O2", "CO", "CH4", "NH3", "CL2", "SO2", "NO2",
    "LEL", "VOC", "CO2", "H2S", "O3", "PH3", "HCN", "HCL"
]

# Sensor data ranges (min, max) for realistic simulation
SENSOR_RANGES = {
    "H2": (0, 100),      # ppm
    "O2": (18, 23),      # %
    "CO": (0, 50),       # ppm
    "CH4": (0, 5),       # % LEL
    "NH3": (0, 50),      # ppm
    "CL2": (0, 1),       # ppm
    "SO2": (0, 5),       # ppm
    "NO2": (0, 5),       # ppm
    "LEL": (0, 100),     # %
    "VOC": (0, 500),     # ppb
    "CO2": (400, 2000),  # ppm
    "H2S": (0, 20),      # ppm
    "O3": (0, 0.1),      # ppm
    "PH3": (0, 1),       # ppm
    "HCN": (0, 10),      # ppm
    "HCL": (0, 5),       # ppm
}

# Alarm thresholds (low, high) for each sensor type
ALARM_THRESHOLDS = {
    "H2": (10.0, 50.0),
    "O2": (19.5, 23.5),
    "CO": (25.0, 50.0),
    "CH4": (10.0, 25.0),
    "NH3": (25.0, 50.0),
    "CL2": (0.5, 1.0),
    "SO2": (2.0, 5.0),
    "NO2": (3.0, 5.0),
    "LEL": (10.0, 50.0),
    "VOC": (100.0, 300.0),
    "CO2": (1000.0, 2000.0),
    "H2S": (10.0, 20.0),
    "O3": (0.05, 0.1),
    "PH3": (0.3, 1.0),
    "HCN": (4.7, 10.0),
    "HCL": (2.0, 5.0),
}


def rand_imei():
    """Generate a 15-digit IMEI-style numeric string."""
    return "".join(random.choice("0123456789") for _ in range(15))


def rand_device_id():
    """Generate a device ID."""
    return f"DEV{random.randint(1, 999):03d}"


def current_time_str():
    return datetime.now().strftime("%H:%M:%S")


def current_date_str():
    return datetime.now().strftime("%d/%m/%y")


def make_sensor_message(device: dict, sensor_type: str) -> str:
    """
    Create a sensor message in the new format:
    *,<status>,<device_id>,<imei>,<sensor_type>,<sensor_data>,<alarm_low>,<alarm_high>,
    <fault_status>,<temp>,<humidity>,<power_type>,<battery>,<rssi>,<time>,<date>
    """
    # Get range and thresholds for this sensor type
    data_range = SENSOR_RANGES.get(sensor_type, (0, 100))
    thresholds = ALARM_THRESHOLDS.get(sensor_type, (10.0, 50.0))
    
    # Generate sensor data
    sensor_data = round(random.uniform(data_range[0], data_range[1]), 2)
    alarm_low = thresholds[0]
    alarm_high = thresholds[1]
    
    # Determine fault status (rare faults)
    fault_status = 1 if random.random() < 0.02 else 0
    
    # Device-level data
    temperature = round(random.uniform(15.0, 45.0), 1)
    humidity = round(random.uniform(30.0, 80.0), 1)
    power_type = device["power_type"]
    battery = device["battery"] if power_type == "BATTERY" else 100
    rssi = random.randint(5, 31)
    
    # Status (11 = normal)
    status = 11
    
    parts = [
        "*",                    # Start marker
        str(status),            # Status
        device["device_id"],    # Device ID
        device["imei"],         # IMEI
        sensor_type,            # Sensor Type
        f"{sensor_data:.2f}",   # Sensor Data
        f"{alarm_low:.1f}",     # Alarm Low
        f"{alarm_high:.1f}",    # Alarm High
        str(fault_status),      # Fault Status
        f"{temperature:.1f}",   # Temperature
        f"{humidity:.1f}",      # Humidity
        power_type,             # Power Type
        str(battery),           # Battery %
        str(rssi),              # RSSI
        current_time_str(),     # Time
        current_date_str(),     # Date
    ]
    
    return ",".join(parts)


def main():
    """Main simulator entry point."""
    # Create devices
    devices = []
    for i in range(DEVICE_COUNT):
        # Select sensors for this device (up to SENSORS_PER_DEVICE)
        num_sensors = min(SENSORS_PER_DEVICE, len(SENSOR_TYPES))
        device_sensors = SENSOR_TYPES[:num_sensors]
        
        devices.append({
            "device_id": f"DEV{i+1:03d}",
            "imei": rand_imei(),
            "sensors": device_sensors,
            "power_type": random.choice(["DIRECT", "BATTERY"]),
            "battery": random.randint(50, 100),
        })
    
    # Connect to MQTT broker
    client = mqtt.Client(client_id=f"sim-{random.randint(1000, 9999)}")
    
    print(f"Connecting to MQTT broker: {MQTT_HOST}:{MQTT_PORT}")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()
    
    print(f"Simulating {len(devices)} devices with {SENSORS_PER_DEVICE} sensors each")
    print(f"Publishing to topic: {MQTT_TOPIC}")
    print(f"Interval: {PUBLISH_INTERVAL}s")
    
    try:
        while True:
            for device in devices:
                # Slowly drain battery for battery-powered devices
                if device["power_type"] == "BATTERY" and random.random() < 0.1:
                    device["battery"] = max(0, device["battery"] - 1)
                
                # Send message for each sensor
                for sensor_type in device["sensors"]:
                    msg = make_sensor_message(device, sensor_type)
                    client.publish(MQTT_TOPIC, msg)
                    # Small delay between sensor messages to avoid overwhelming
                    time.sleep(0.05)
            
            time.sleep(PUBLISH_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nShutting down simulator...")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
