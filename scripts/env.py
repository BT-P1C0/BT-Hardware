from mqtt import create_connect_packet


class env:
    bus: str = "c"
    id: str = "bus_" + bus
    mqtt_topic: str = "bus/" + bus
    mqtt_server: str = "test.mosquitto.org"
    mqtt_port: int = 1883
    mqtt_user: str = "user"
    mqtt_pass: str = "pass"
    mqtt_keep_alive: int = 60

    connection_payload: bytes = None

    def __init__(self):
        self.connection_payload = (
            create_connect_packet(self.id, self.mqtt_keep_alive) + b"\x1A"
        )


if __name__ == "__main__":
    print("Environment Variables\nRun using main.py")
