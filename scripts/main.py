import time
from machine import Pin, UART, I2C, reset
from NMEA import NMEAparser
from helper import *
from OLED import SSD1306_I2C
import _thread
from hardware import Hardware
from SIM800L import SIM800L


class Tracker(object):
    """
    Bus Tracker object class
    """

    oled: SSD1306_I2C | None = None
    picoLed: Pin
    simModule: SIM800L
    gpsModule: UART
    gpsParserObject: NMEAparser
    lastDisplayedText: str = ""
    httpUrl: str = ""
    lat, lng, utc_time = 0, 0, 0
    RISSI, BER = 0, 0

    def __init__(self) -> None:
        self.env = env

        self.__connectLED()
        self.__connectOLED()
        assert self.__connectSIMmodule(), "SIM Module Connection Error"
        assert self.__connectGPSmodule(), "GPS Module Connection Error"

        # Get battery status from SIM Module
        battChargeStatus, battLevel, battVoltage = self.simModule.batteryStatus()
        self.display(f"Battery: {battLevel}\nVoltage: {battVoltage}")
        print(
            f"Battery: {battChargeStatus}, Level: {battLevel}, Voltage: {battVoltage}"
        )

        self.ledBlink(3, 1)

    def hardReset(self) -> None:
        """
        Hard reset the device
        """
        self.simModule.reset()
        reset()

    def __connectLED(self) -> None:
        try:
            self.picoLed = Hardware.led()

        except Exception as e:
            print("LED: ERROR")
            print(e)

        else:
            print("LED: OK")

    def __connectOLED(self) -> None:
        try:
            self.oled = SSD1306_I2C(
                width=Hardware.oled_resolution[0],  # 128
                height=Hardware.oled_resolution[1],  # 32
                i2c=Hardware.oled(),
            )

        except Exception as e:
            print("OLED: ERROR")
            print(e)
            self.ledBlink(5, 0.1)

        else:
            print("OLED: OK")
            self.ledBlink(2, 0.1)

    def __connectSIMmodule(self) -> bool:
        try:
            self.simModule = SIM800L(
                Hardware.sim(),
                Hardware.sim_rst(),
                True,
            )
            assert self.simModule.initialize()

        except Exception as e:
            self.display("SIM: ERROR")
            print(e)
            self.ledBlink(5, 0.1)
            return False

        else:
            self.display("SIM: OK")
            self.ledBlink(2, 0.1)
            return True

    def __connectGPSmodule(self) -> bool:
        try:
            self.gpsModule = Hardware.gps()

        except Exception as e:
            self.display("GPS: ERROR")
            print(e)
            self.ledBlink(5, 0.1)
            self.hardReset()
            return False

        else:
            self.display("GPS: OK")
            self.ledBlink(2, 0.1)
            self.gpsParserObject = NMEAparser()
            return True

    def getSignalStrength(self) -> None:
        self.RSSI, self.BER = self.simModule.getSignalStrength()

    def checkNetworkRegistered(self) -> None:
        while x := self.simModule.networkRegisterationStatus():
            self.display(x[2])
            if x[0] == True:
                return
            time.sleep(1)

    def connectToInternet(self) -> None:
        self.display(
            "Connecting to internet...",
        )
        retires: int = 1

        while retires < 11:
            try:
                ip = self.simModule.connectGPRS(apn="airtelgprs.net")
                self.getSignalStrength()
                self.display(f"IP: {ip}\nRSSI: {self.RSSI}%")
                print(f"BER: {self.BER}")
                return

            except Exception as e:
                retires += 1
                self.display(f"\nConnection failed\ntry: {retires}/10")
                print(f"Internet Connection Exception: {e}")
                time.sleep(1)

        self.hardReset()

    def ledBlink(self, times: int = 1, delay: float = 1) -> None:
        if self.picoLed:
            self.picoLed.value(0)  # turn off led if open
            for _ in range(times * 2 - 1):
                self.picoLed.toggle()
                time.sleep(delay)
            self.picoLed.value(0)  # turn off led if somehow left on

    def display(
        self, text: str, x: int = 0, y: int = 0, color: int = 1, overflow: str = "wrap"
    ) -> None:
        """
        Display text on OLED screen

        Overflow Behaviours
        eol : chop the sentance
        wrap : wrap to next line
        """

        try:
            if self.lastDisplayedText != text:
                print("\n" + text)
                if self.oled:
                    self.oled.fill(0)
                    lines = text.splitlines()
                    for index in range(4):
                        if index < len(lines):
                            line = lines[index]
                            if len(line) > 16:
                                if overflow == "eol":
                                    line = line[:16]
                                else:
                                    lines.insert(index + 1, line[16:])
                                    line = line[:16]
                            self.oled.text(line.strip(), x, y, 1)
                            y += 8
                            self.oled.show()
                    self.lastDisplayedText = text
        except Exception as e:
            print("Display exception", e)

    def onlineDebugMessage(self, retry: bool = True) -> None:
        gsmLocation = self.simModule.getGsmLocation()
        failedRequests = 0

        while True:
            if failedRequests > 10:
                self.hardReset()
            try:
                url = debugPostUrl()
                self.display(f"\nSending Debug Message")
                print("Url =", url)
                self.picoLed.value(1)

                response = self.simModule.makeHTTPRequest(
                    method="POST",
                    url=url,
                    data=debugPostPayload(
                        status="online",
                        RSSI=self.RSSI,
                        lat=gsmLocation.lat,
                        lng=gsmLocation.lng,
                    ),
                )

                self.picoLed.value(0)

                print(response.status_code, ":", response.status)
                print("Response: ", response.content)

                if response.status_code == 200:
                    self.display(f"Device Online")
                    break
                else:
                    self.display(
                        f"Sending error\nStatus Code: {response.status_code}\n"
                    )
                    failedRequests += 1
            except Exception as e:
                failedRequests += 1
                self.display("Networking Exception")
                print(e)
            if not retry:
                break

    # Networking Thread
    def networkingThread(self) -> None:
        """
        Networking Thread that handels network requests
        """

        currRequestUrl: str = ""
        lastRequestUrl: str = ""

        failedRequests: int = 0

        while failedRequests < 10:
            try:
                if self.httpUrl:
                    currRequestUrl = self.httpUrl

                    if currRequestUrl != lastRequestUrl:
                        self.display(f"\nSending Location")
                        print("Url =", currRequestUrl)
                        self.picoLed.value(1)
                        t1: int = time.ticks_ms()
                        response = self.simModule.makeHTTPRequest(
                            method="GET",
                            url=currRequestUrl,
                        )
                        t2: int = time.ticks_ms()
                        self.picoLed.value(0)
                        self.display(
                            f"Status Code: {response.status_code}\nTime Delta:\n{time.ticks_diff(t1,t2)/1000} s"
                        )
                        print(response.status_code, ":", response.status)
                        print("Response:", response.content)

                        if response.status_code == 200:
                            failedRequests = 0
                            lastRequestUrl = currRequestUrl
                        else:
                            failedRequests += 1

                    else:
                        self.getSignalStrength()
                        self.onlineDebugMessage(retry=False)

            except Exception as e:
                failedRequests += 1
                self.display("Networking Exception")
                print(e)

        print("Too many filed requests, resetting...")
        self.hardReset()

    # GPS Thread
    def gpsThread(self) -> None:
        """
        GPS Thread that handels reading and parsing GPS data
        """

        while self.gpsModule:
            if data := self.gpsModule.read(1):
                try:
                    if self.gpsParserObject.update(data.decode("ASCII")):
                        if self.gpsParserObject.utc_time:
                            if self.gpsParserObject.lat and self.gpsParserObject.lng:
                                self.lat = self.gpsParserObject.lat
                                self.lng = self.gpsParserObject.lng
                                self.utc_time = self.gpsParserObject.utc_time
                                self.httpUrl = httpGetUrl(
                                    self.lat,
                                    self.lng,
                                    self.utc_time,
                                )
                            else:
                                self.display("GPS: No Location Fix")
                        else:
                            self.display("GPS: No Time Fix")

                except Exception as e:
                    print("GPS Exception", e)

    def start(self) -> None:
        """
        Starts the tracker by initializing http connection and starting the threads
        """
        # Connect to internet
        self.connectToInternet()
        self.display("Initialising HTTP connection")
        self.simModule.initHTTP()
        self.display("Initialised HTTP connection")

        self.onlineDebugMessage(retry=False)

        self.display("Starting Main Loop")
        _thread.start_new_thread(self.networkingThread, ())
        self.gpsThread()


if __name__ == "__main__":
    print("Starting Bus Tracker")
    # try:
    tracker: Tracker = Tracker()
    tracker.start()
    # except Exception as e:
    #     print("Main Exception", e)
    #     reset()
