from SIM800L import SIM800L, ATCommand, Commands
from machine import UART, Pin

print("SIM800L Tester")

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
print(f"RSSI: {RSSI}, BER: {BER}")

network = simModule.getServiceProviderName()
print(f"Network: {network}")

apn = simModule.getAPN()
print(f"APN: {apn}")

ip = simModule.connectGPRS(apn=apn)  # Idea
print(f"IP: {ip}")

print(simModule.getGsmLocation())
