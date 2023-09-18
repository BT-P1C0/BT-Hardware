from NMEA import NMEAparser
from machine import Pin, UART

gpsModule = UART(
    1,  # 1
    baudrate=9600,  # 9600
    tx=Pin(8),  # 4
    rx=Pin(9),  # 5
)

gpsParserObject = NMEAparser()


while True:
    if gpsModule.any():
        try:
            print((gpsModule.read(1)).decode("ASCII"), end="")
        except Exception as e:
            print("GPS Exception", e)
