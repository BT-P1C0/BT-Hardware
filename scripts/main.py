import utime
from machine import Pin, UART, I2C, WDT
from NMEA import NMEAparser
from SIM800L import Modem
from helper import env, httpGetUrl, debugUrl
from OLED import SSD1306_I2C
import _thread


class BusTracker(object):
    """
    Bus Tracker object class
    """

    def __init__(self) -> None:
        wdt.feed()

        self.env = env
        # Hardware Connection Status
        self.oled: SSD1306_I2C | None = None
        self.picoLed: Pin | None = None
        # self.imu: MPU6050 | None = None
        self.simModule: Modem | None = None
        self.gpsModule: UART | None = None
        self.gpsParserObject: NMEAparser | None = None

        self.last_display: str = ""
        self.httpUrl: str = ""
        self.lat, self.lng, self.utc = 0, 0, 0

        # Pico LED
        wdt.feed()
        self.led_state: bool = self.connectLED()
        # OLED Screen
        wdt.feed()
        self.oled_state: bool = self.connectOLED()
        # # IMU
        # wdt.feed()
        # self.imu_state: bool = self.connectIMU()
        # SIM Module
        wdt.feed()
        self.sim_state: bool = self.connectSIMmodule()
        # GPS Module
        wdt.feed()
        self.gps_state: bool = self.connectGPSmodule()
        wdt.feed()

        # Get battery status from SIM Module
        battChargeStatus, battLevel, battVoltage = self.simModule.battery_status()
        self.display(f"Battery: {battLevel}\nVoltage: {battVoltage}")
        print(
            f"Battery: {battChargeStatus}, Level: {battLevel}, Voltage: {battVoltage}"
        )

        # Connect to internet
        wdt.feed()
        self.connectToInternet()
        wdt.feed()

        self.ledBlink(3, 0.3)
        wdt.feed()

    def connectLED(self) -> bool:
        try:
            self.picoLed = Pin(env.hardware.led.pin, Pin.OUT)
            print("LED: OK")
            return True
        except Exception as e:
            self.picoLed = None
            print("LED: ERROR")
            print(e)
            return False

    def connectOLED(self) -> bool:
        try:
            self.oled = SSD1306_I2C(
                width=self.env.hardware.oled.resolution.width,  # 128
                height=self.env.hardware.oled.resolution.height,  # 32
                i2c=I2C(
                    id=self.env.hardware.oled.pin.i2c,  # 1
                    scl=Pin(self.env.hardware.oled.pin.scl),  # 15
                    sda=Pin(self.env.hardware.oled.pin.sda),  # 14
                    freq=self.env.hardware.oled.pin.frequency,  # 200000
                ),
            )
            print("OLED: OK")
            self.ledBlink(2, 0.1)
            return True
        except Exception as e:
            print("OLED: ERROR")
            print(e)
            self.ledBlink(5, 0.1)
            return False

    # def connectIMU(self) -> bool:
    #     try:
    #         self.imu = MPU6050(
    #             side_str=I2C(
    #                 id=self.env.hardware.imu.pin.i2c,  # 0
    #                 scl=Pin(self.env.hardware.imu.pin.scl),  # 17
    #                 sda=Pin(self.env.hardware.imu.pin.sda),  # 14
    #                 freq=self.env.hardware.imu.pin.frequency,  # 400000
    #             ),
    #         )
    #         self.display("IMU: OK")
    #         self.ledBlink(2, 0.1)
    #         return True
    #     except Exception as e:
    #         self.display("IMU: ERROR")
    #         print(e)
    #         self.ledBlink(5, 0.1)
    #         return False

    def connectSIMmodule(self) -> bool:
        try:
            self.simModule = Modem(
                uart=UART(
                    self.env.hardware.sim.pin.uart,  # 0
                    baudrate=self.env.hardware.sim.pin.baudrate,  # 9600
                    tx=Pin(self.env.hardware.sim.pin.tx),  # 0
                    rx=Pin(self.env.hardware.sim.pin.rx),  # 1
                ),
                MODEM_RST_PIN=self.env.hardware.sim.pin.rst,  # 2
                showSpecificErrors=True,
            )
            self.simModule.initialize()
            self.display("SIM: OK")
            self.ledBlink(2, 0.1)
            return True
        except Exception as e:
            self.display("SIM: ERROR")
            print(e)
            self.ledBlink(5, 0.1)
            return False

    def connectGPSmodule(self) -> bool:
        try:
            self.gpsModule = UART(
                self.env.hardware.gps.pin.uart,  # 1
                baudrate=self.env.hardware.gps.pin.baudrate,  # 9600
                tx=Pin(self.env.hardware.gps.pin.tx),  # 8
                rx=Pin(self.env.hardware.gps.pin.rx),  # 9
            )
            self.gpsParserObject = NMEAparser()
            self.display("GPS: OK")
            self.ledBlink(2, 0.1)
            return True
        except Exception as e:
            self.display("GPS: ERROR")
            print(e)
            self.ledBlink(5, 0.1)
            return False

    def connectToInternet(self) -> None:
        self.display(
            "Connecting to internet...",
        )
        retires: int = 0

        while True:
            print("Try", retires + 1)
            if retires < 10:
                wdt.feed()

            try:
                assert self.sim_state == 1
                ip = self.simModule.connect(apn="airtelgprs.net")
                RSSI, BER = self.simModule.get_signal_strength()
                self.display(f"IP: {ip}\nRSSI: {RSSI}%")
                # 99 is "not know or not detectable"
                print(f"BER: {BER}")
                break
            except Exception as e:
                self.display(f"\nConnection failed\ntry {retires + 1}/10")
                print(f"Internet Connection Exception: {e}")

            retires += 1

    def ledBlink(self, times: int = 1, delay: int = 1) -> None:
        if self.led_state:
            self.picoLed.value(0)  # turn off led if open
            for _ in range(times * 2 - 1):
                self.picoLed.toggle()
                utime.sleep(delay)
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
            if self.last_display != text:
                print("\n" + text)
                if self.oled_state:
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
                    self.last_display = text
        except Exception as e:
            print("Display exception", e)

    def onlineDebugMessage(self) -> None:
        response = self.simModule.http_request(mode="GET", url=debugUrl("online"))
        self.display(f"Device Online\nStatus Code: {response.status_code}\n")

    # Networking Thread
    def networkingThread(self) -> None:
        """
        Networking Thread that handels network requests
        """

        currRequestUrl = ""
        lastRequestUrl = ""

        while self.sim_state:
            try:
                if self.httpUrl:
                    currRequestUrl = self.httpUrl
                    if currRequestUrl != lastRequestUrl:
                        self.display(f"\nSending Location")
                        print("Url =", currRequestUrl)
                        self.picoLed.value(1)
                        t = utime.ticks_ms()
                        response = self.simModule.http_request(
                            mode="GET", url=currRequestUrl
                        )
                        self.picoLed.value(0)
                        self.display(
                            f"Status Code: {response.status_code}\nTime Delta:\n{utime.ticks_diff(utime.ticks_ms(),t)/1000} s"
                        )
                        print("Response:", response.content)
                        lastRequestUrl = currRequestUrl

            except Exception as e:
                self.display("Networking Exception")
                print(e)

    # GPS Thread
    def gpsThread(self) -> None:
        """
        GPS Thread that handels reading and parsing GPS data
        """

        while self.gps_state:
            wdt.feed()
            if self.gpsModule.any():
                try:
                    if self.gpsParserObject.update(
                        (self.gpsModule.read(1)).decode("ASCII")
                    ):
                        if self.gpsParserObject.utc_time:
                            if self.gpsParserObject.lat and self.gpsParserObject.lng:
                                self.lat = self.gpsParserObject.lat
                                self.lng = self.gpsParserObject.lng
                                self.utc = self.gpsParserObject.utc_time
                                self.httpUrl = httpGetUrl(
                                    self.lat,
                                    self.lng,
                                    self.utc,
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
        wdt.feed()
        self.display("Initialising HTTP connection")
        self.simModule.http_init()
        wdt.feed()
        self.onlineDebugMessage()
        wdt.feed()
        self.display("Starting Main Loop")
        _thread.start_new_thread(self.networkingThread, ())
        self.gpsThread()


if __name__ == "__main__":
    # Watchdog Timer
    print("Boot 5 sec hold")
    utime.sleep(5)
    print("Starting Bus Tracker")
    wdt: WDT = WDT(timeout=8000)  # 8 seconds (8388 is max)
    tracker: BusTracker = BusTracker()
    tracker.start()
