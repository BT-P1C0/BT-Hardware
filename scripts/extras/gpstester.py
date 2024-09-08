from NMEA import NMEAparser
from hardware import Hardware

print(
    """
##############################################
#  NEO6M Micropython Library Test Script     #
# -----------------------------------------  #
"""
)

gpsModule = Hardware.gps()

gpsParserObject = NMEAparser()

while True:
    if gpsModule.any():
        try:
            print((gpsModule.read(1)).decode("ASCII"), end="")
        except Exception as e:
            print("GPS Exception", e)
