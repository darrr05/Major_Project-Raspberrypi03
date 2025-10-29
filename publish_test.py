import time
import paho.mqtt.client as mqtt

broker_address = "172.20.10.3"
topic = "mismatch/data"

client = mqtt.Client()
client.connect(broker_address, port=1883)  # Default port is 1883 for non-TLS
count = 0
try:
    while True:
        message = f"Mismatch"
        client.publish(topic, message)
        print(f"Published: {message}")
        count += 1
        time.sleep(20)
except KeyboardInterrupt:
    print("Publisher stopped.")
