from machine import Pin, UART, I2C


class Hardware:
    @staticmethod
    def gps():
        return UART(
            1,
            tx=Pin(8),
            rx=Pin(9),
            baudrate=9600,
        )

    @staticmethod
    def sim():
        return UART(
            0,
            tx=Pin(0),
            rx=Pin(1),
            baudrate=9600,
        )

    @staticmethod
    def sim_rst():
        return Pin(2, Pin.OUT)

    @staticmethod
    def oled():
        return I2C(
            1,
            scl=Pin(19),
            sda=Pin(18),
            freq=200000,
        )

    oled_resolution = (128, 32)

    @staticmethod
    def imu():
        return I2C(
            0,
            scl=Pin(17),
            sda=Pin(16),
            freq=400000,
        )

    @staticmethod
    def led():
        return Pin(25, Pin.OUT)


if __name__ == "__main__":
    pass
