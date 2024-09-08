from SIM800L import SIM800L, Commands
from mqtt import create_connect_packet, create_publish_packet

from hardware import Hardware


print(
    """
##############################################
#  SIM800L Micropython Library Test Script   #
# -----------------------------------------  #
"""
)

print("Initializing SIM800L Module...")

simModule = SIM800L(
    uart=Hardware.sim(),
    reset_pin=Hardware.sim_rst(),
    showErrors=True,
    debugMode=False,
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

try:
    simModule.execute(Commands.closeTcp())
except Exception as e:
    print(e)

simModule.init_tcp("test.mosquitto.org", 1883)
print("TCP Initialized")


connect_data = create_connect_packet("client123", keep_alive_duration=10)
simModule.send_tcp_data(connect_data)
print("Connect Packet Sent")


publish_data = create_publish_packet("hello", "Hello, mglsj ")
simModule.send_tcp_data(publish_data)


print("SIM800L Test Script Complete")
