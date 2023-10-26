from SIM800L import SIM800L, ATCommand, Commands
from machine import UART, Pin

print(
    """
##############################################
#  SIM800L Micropython Library Test Script   #
# -----------------------------------------  #
"""
)

print("Initializing SIM800L Module...")

simModule = SIM800L(
    uart=UART(
        0,
        tx=Pin(0),
        rx=Pin(1),
        baudrate=9600,
    ),
    reset_pin=Pin(2, Pin.OUT),
    showErrors=True,
)

simModule.initialize()

battChargeStatus, battLevel, battVoltage = simModule.batteryStatus()
print(f"Battery: {battChargeStatus}, Level: {battLevel}, Voltage: {battVoltage}")

RSSI, BER = simModule.getSignalStrength()
print(f"RSSI: {RSSI}, BER: {BER}\n")

scan = simModule.scanNetworks()
print(f"Scan: {scan}\n")

currentNetwork = simModule.getCurrentNetwork()
print(f"Current Network: {currentNetwork}")

network = simModule.getServiceProviderName()
print(f"Network: {network}")


ip = simModule.connectGPRS()
print(f"IP: {ip}")

print("Gsm loc:", simModule.getGsmLocation())

print("\n", simModule.getCellTowerInfo(), "\n")
