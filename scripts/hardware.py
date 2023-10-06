from machine import Pin, UART, I2C


class Hardware:
    gps = UART(
        id=1,
        tx=Pin(8),
        rx=Pin(9),
        baudrate=9600,
    )

    sim = UART(
        id=0,
        tx=Pin(0),
        rx=Pin(1),
        baudrate=9600,
    )

    sim_rst = Pin(2, Pin.OUT)

    oled = I2C(
        1,
        scl=Pin(19),
        sda=Pin(18),
        freq=200000,
    )

    oled_resolution = (128, 32)

    imu = I2C(
        0,
        scl=Pin(17),
        sda=Pin(16),
        freq=400000,
    )

    led = Pin(25, Pin.OUT)
