import paho.mqtt.client as mqtt



broker_address = "192.168.13.60"  

topic = "counter/data"



def on_connect(client, userdata, flags, rc):

    if rc == 0:

        print("Connected successfully")

        client.subscribe(topic)

    else:

        print(f"Connection failed with code {rc}")



def on_message(client, userdata, msg):

    print(f"Received message: {msg.payload.decode()}")



client = mqtt.Client()

client.on_connect = on_connect

client.on_message = on_message



client.connect(broker_address, port=1883)



client.loop_forever()