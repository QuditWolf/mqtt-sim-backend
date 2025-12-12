FROM python:3.11-slim

WORKDIR /sim

COPY requirements.txt .
RUN pip install uv && uv pip install --system --no-cache-dir -r requirements.txt

COPY simulator.py .

ENV MQTT_HOST=mosquitto
ENV MQTT_PORT=1883
ENV MQTT_TOPIC=devices/telemetry
ENV DEVICE_COUNT=5
ENV PUBLISH_INTERVAL=1

CMD ["python", "simulator.py"]

