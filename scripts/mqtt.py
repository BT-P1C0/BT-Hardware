import struct


def create_connect_packet(client_id: str, keep_alive_duration: int = 60) -> bytes:
    # Fixed Header: Connect command (0x10) and Remaining Length
    fixed_header: bytes = struct.pack("!BB", 0x10, 12 + len(client_id))

    # Variable Header: Protocol Name (MQTT), Protocol Level (4), Connect Flags, Keep Alive
    protocol_name: bytes = b"\x00\x04MQTT"
    protocol_level: bytes = struct.pack("!B", 4)  # Protocol level 4 (MQTT 3.1.1)
    connect_flags: bytes = struct.pack("!B", 0x02)  # Connect flags (Clean session)
    keep_alive: bytes = struct.pack("!H", keep_alive_duration)  # Keep alive

    # Payload: Client Identifier
    client_id_len: bytes = struct.pack("!H", len(client_id))
    client_id_bytes: bytes = client_id.encode()

    # Combine all parts to form the Connect Packet
    connect_packet: bytes = (
        fixed_header
        + protocol_name
        + protocol_level
        + connect_flags
        + keep_alive
        + client_id_len
        + client_id_bytes
    )
    return connect_packet


def create_publish_packet(topic: str, message: str, qos: int = 0, retain: bool = False):
    # Fixed Header: Publish command (0x30), Retain flag, QoS, and Remaining Length
    retain_flag = 1 if retain else 0
    fixed_header_byte = 0x30 | (qos << 1) | retain_flag  # Set retain flag (LSB)
    fixed_header = struct.pack("!B", fixed_header_byte)

    # Variable Header: Topic Name (ensure it's properly encoded)
    topic_len = struct.pack("!H", len(topic))  # 2 bytes for topic length
    topic_bytes = topic.encode("utf-8")  # Topic should be UTF-8 encoded

    # Payload: Message (also encoded as UTF-8)
    message_bytes = message.encode("utf-8")

    # Remaining Length calculation: 2 bytes for topic length + length of topic + length of message
    remaining_length = (
        len(topic_bytes) + len(message_bytes) + 2
    )  # 2 bytes for the topic length

    # Fixed header + remaining length byte
    fixed_header += struct.pack("!B", remaining_length)

    # Combine all parts to form the Publish Packet
    publish_packet = fixed_header + topic_len + topic_bytes + message_bytes
    return publish_packet
