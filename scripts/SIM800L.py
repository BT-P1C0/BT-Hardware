"""
SIM800L Driver for MicroPython 1.20 on Raspberry Pi Pico

sources: https://github.com/pythings/Drivers/blob/master/SIM800L.py
"""

import time, json
from machine import Pin, UART


class GenericATError(Exception):
    pass


class SpecificATError(Exception):
    pass


class TimeoutError(Exception):
    pass


httpaction_status_codes = {
    "000": "Unknown HTTPACTION error",
    "100": "Continue",
    "101": "Switching Protocols",
    "200": "OK",
    "201": "Created",
    "202": "Accepted",
    "203": "Non-Authoritative Information",
    "204": "No Content",
    "205": "Reset Content",
    "206": "Partial Content",
    "300": "Multiple Choices",
    "301": "Moved Permanently",
    "302": "Found",
    "303": "See Other",
    "304": "Not Modified",
    "305": "Use Proxy",
    "307": "Temporary Redirect",
    "400": "Bad Request",
    "401": "Unauthorized",
    "402": "Payment Required",
    "403": "Forbidden",
    "404": "Not Found",
    "405": "Method Not Allowed",
    "406": "Not Acceptable",
    "407": "Proxy Authentication Required",
    "408": "Request Time-out",
    "409": "Conflict",
    "410": "Gone",
    "411": "Length Required",
    "412": "Precondition Failed",
    "413": "Request Entity Too Large",
    "414": "Request-URI Too Large",
    "415": "Unsupported Media Type",
    "416": "Requested range not satisfiable",
    "417": "Expectation Failed",
    "500": "Internal Server Error",
    "501": "Not Implemented",
    "502": "Bad Gateway",
    "503": "Service Unavailable",
    "504": "Gateway Time-out",
    "505": "HTTP Version not supported",
    "600": "Not HTTP PDU",
    "601": "Network Error",
    "602": "No memory",
    "603": "DNS Error",
    "604": "Stack Busy",
    "605": "SSL failed to establish channels",
    "606": "SSL fatal alert message with immediate connection termination",
}


class Response(object):
    def __init__(self, status_code, content) -> None:
        self.status_code: int = int(status_code)
        self.status: str = httpaction_status_codes.get(str(self.status_code), "Unknown")
        self.content: str = content


class ATCommand(object):
    def __init__(self, string: str, timeout: int, end: str) -> None:
        self.string: str = string
        self.timeout: int = timeout
        self.end: str = end


class Network(object):
    def __init__(self, name: str, shortname: str, id: str) -> None:
        self.name: str = name
        self.shortname: str = shortname
        self.id: str = id


class Commands(object):
    # sources:
    # https://cdn-shop.adafruit.com/datasheets/sim800_series_at_command_manual_v1.01.pdf
    # https://www.elecrow.com/wiki/images/2/20/SIM800_Series_AT_Command_Manual_V1.09.pdf
    @staticmethod
    def enableErrorCodes() -> ATCommand:
        """Report Mobile Equipment Error"""
        return ATCommand("AT+CMEE=2", 3, "OK")

    @staticmethod
    def productInfo() -> ATCommand:
        """Display Product Identification Information"""
        return ATCommand("ATI", 10, "OK")

    @staticmethod
    def firmwareRevision() -> ATCommand:
        """Request TA revision identification of software release"""
        return ATCommand("AT+CGMR", 3, "OK")

    @staticmethod
    def isSIMInserted() -> ATCommand:
        """Check if SIM card is inserted"""
        return ATCommand("AT+CSMINS?", 3, "OK")

    @staticmethod
    def isNetworkRegistered() -> ATCommand:
        """Check if network is registered"""
        return ATCommand("AT+CREG?", 3, "OK")

    @staticmethod
    def batteryCharge() -> ATCommand:
        """Battery Charge"""
        return ATCommand("AT+CBC", 3, "OK")

    @staticmethod
    def scanOperators() -> ATCommand:
        return ATCommand("AT+COPS=?", 60, "OK")

    @staticmethod
    def currentOperator() -> ATCommand:
        """TA returns the current mode and the currently selected operator."""
        return ATCommand("AT+COPS?", 3, "OK")

    @staticmethod
    def readOpeartorNames() -> ATCommand:
        """Read Operator Names"""
        return ATCommand("AT+COPN", 60, "OK")

    @staticmethod
    def signalQuality() -> ATCommand:
        """Signal Quality Report"""
        return ATCommand("AT+CSQ", 3, "OK")

    @staticmethod
    def getServiceProviderName() -> ATCommand:
        """Get Service Provider Name"""
        return ATCommand("AT+CSPN?", 3, "OK")

    @staticmethod
    def checkNetworkRegistration() -> ATCommand:
        """Network Registration Status"""
        return ATCommand("AT+CREG?", 3, "OK")

    @staticmethod
    def setBearerAPN(apn: str) -> ATCommand:
        """Set bearer APN"""
        return ATCommand(f'AT+SAPBR=3,1,"APN","{apn}"', 3, "OK")

    @staticmethod
    def setBearerUsername(username: str) -> ATCommand:
        """Set bearer Username"""
        return ATCommand(f'AT+SAPBR=3,1,"USER","{username}"', 3, "OK")

    @staticmethod
    def setBearerPassword(password: str) -> ATCommand:
        """Set bearer Password"""
        return ATCommand(f'AT+SAPBR=3,1,"PWD","{password}"', 3, "OK")

    @staticmethod
    def setBearerGPRS() -> ATCommand:
        """Set bearer GPRS"""
        return ATCommand('AT+SAPBR=3,1,"CONTYPE","GPRS"', 3, "OK")

    @staticmethod
    def openBearer() -> ATCommand:
        """Open bearer"""
        return ATCommand("AT+SAPBR=1,1", 3, "OK")

    @staticmethod
    def closeBearer() -> ATCommand:
        """Close bearer"""
        return ATCommand("AT+SAPBR=0,1", 3, "OK")

    @staticmethod
    def bearerStatus() -> ATCommand:
        """Bearer status"""
        return ATCommand("AT+SAPBR=2,1", 30, "OK")

    @staticmethod
    def initHTTP() -> ATCommand:
        """Initialize HTTP service"""
        return ATCommand("AT+HTTPINIT", 3, "OK")

    @staticmethod
    def closeHTTP() -> ATCommand:
        """Terminate HTTP service"""
        return ATCommand("AT+HTTPTERM", 3, "OK")

    @staticmethod
    def setHTTPParameterURL(url: str) -> ATCommand:
        """Set HTTP parameter url"""
        return ATCommand(f'AT+HTTPPARA="URL","{url}"', 3, "OK")

    @staticmethod
    def setHTTPParameterCID(cid: int) -> ATCommand:
        """Set HTTP parameter cid"""
        return ATCommand(f'AT+HTTPPARA="CID",{cid}', 3, "OK")

    @staticmethod
    def setHTTPParameterContent(content: str) -> ATCommand:
        """Set HTTP parameter content"""
        return ATCommand(f'AT+HTTPPARA="CONTENT","{content}"', 3, "OK")

    @staticmethod
    def HTTPActionGET() -> ATCommand:
        """HTTP GET"""
        return ATCommand("AT+HTTPACTION=0", 30, "+HTTPACTION")

    @staticmethod
    def HTTPActionPOST() -> ATCommand:
        """HTTP POST"""
        return ATCommand("AT+HTTPACTION=1", 30, "+HTTPACTION")

    @staticmethod
    def HTTPData(data_len: int) -> ATCommand:
        """HTTP Data Length"""
        return ATCommand(f"AT+HTTPDATA={data_len},5000", 3, "DOWNLOAD")

    @staticmethod
    def dumpData(data: str) -> ATCommand:
        """Dump Data"""
        return ATCommand(data, 3, "OK")

    @staticmethod
    def HTTPRead() -> ATCommand:
        """HTTP Read"""
        return ATCommand("AT+HTTPREAD", 30, "OK")

    @staticmethod
    def checkSSL() -> ATCommand:
        """Check SSL"""
        return ATCommand("AT+HTTPSSL?", 3, "OK")

    @staticmethod
    def setSSL(ssl: int) -> ATCommand:
        """Set SSL"""
        return ATCommand(f"AT+HTTPSSL={ssl}", 3, "OK")


class SIM800L(object):
    """Modem class. Handles all the AT commands and responses."""

    def __init__(
        self,
        uart: UART,
        reset_pin: Pin | None = None,
        showErrors: bool = False,
    ) -> None:
        # Initialize UART
        self.uart: UART = uart
        # Initialize reset pin
        if reset_pin:
            self.reset_pin: Pin = reset_pin
            self.reset_pin.high()

        self.initialized = False
        self.modemInfo = None
        self.showSpecificErrors: bool = showErrors
        self.sslSupported: bool = False
        self.ipAddr: str | None = None
        self.GPRSinitialized: bool = False
        self.HTTPinitialized: bool = False

    def initialize(self) -> bool:
        retries = 0
        # Test AT commands
        while True:
            try:
                self.modemInfo = self.execute(Commands.productInfo())
            except:
                retries += 1
                if retries < 3:
                    time.sleep(3)
                else:
                    raise
            else:
                break
        # Set initialized flag and support vars
        self.initialized = True
        # Check if SSL is supported
        self.sslSupported = self.execute(Commands.checkSSL()) == "+CIPSSL: (0-1)"

        if self.showSpecificErrors:
            self.execute(Commands.enableErrorCodes())

        return self.initialized

    # ----------------------
    # Execute AT commands
    # ----------------------

    def execute(self, command: ATCommand, clean_output: bool = True) -> str:
        # Execute the AT command
        self.uart.write(bytes(command.string + "\r\n", "utf-8"))

        # Support vars
        pre_end: bool = True
        output: str = ""
        empty_reads: int = 0
        processed_lines: int = 0

        while True:
            line = self.uart.readline()

            if not line:
                time.sleep(1)
                empty_reads += 1
                if empty_reads > command.timeout:
                    raise TimeoutError(
                        f'Timeout for command "{command.string}" (timeout={command.timeout})'
                    )
            else:
                # Convert line to string
                line_str: str = line

                # Do we have an error?
                if line_str == "ERROR\r\n":
                    raise GenericATError("Got generic AT error")
                # Specific error
                if line_str.startswith("+CME ERROR"):
                    raise SpecificATError(
                        line_str + "\nError in command:" + command.string
                    )

                # If we had a pre-end, do we have the expected end?
                if line_str == f"{command.end}\r\n":
                    break
                if pre_end and line_str.startswith(command.end):
                    output += line_str
                    break

                # Do we have a pre-end?
                if line_str == "\r\n":
                    pre_end = True
                else:
                    pre_end = False

                # Keep track of processed lines and stop if exceeded
                processed_lines += 1

                # Save this line unless in particular conditions
                if command.string == "AT+HTTPREAD" and line_str.startswith(
                    "+HTTPREAD:"
                ):
                    pass
                else:
                    output += line_str

        # Remove the command string from the output
        output = output.replace(command.string + "\r\r\n", "")

        # ..and remove the last \r\n added by the AT protocol
        if output.endswith("\r\n"):
            output = output[:-2]

        # Also, clean output if needed
        if clean_output:
            output = output.replace("\r", "")
            output = output.replace("\n\n", "")
            if output.startswith("\n"):
                output = output[1:]
            if output.endswith("\n"):
                output = output[:-1]

        # Return
        return output

    # ----------------------
    #  Function commands
    # ----------------------

    def reset(self) -> None:
        """Reset the modem"""
        self.reset_pin.low()
        time.sleep(1)
        self.reset_pin.high()

    def getModemInfo(self) -> str:
        """Get modem info"""
        self.modem_info = self.execute(Commands.productInfo())
        return self.modem_info

    def batteryStatus(self) -> tuple[str, str, str]:
        """Get battery status"""
        output = self.execute(Commands.batteryCharge())

        battChargeStatus, battLevel, battVoltage = output.split(":")[1].split(",")
        # Map values to battery charge state
        match int(battChargeStatus):
            case 0:
                battChargeStatus = "Not charging"
            case 1:
                battChargeStatus = "Charging"
            case 2:
                battChargeStatus = "Finished charging"
            case _:
                battChargeStatus = "Power fault"

        # More conversions
        battLevel = f"{battLevel}%"
        battVoltage = f"{int(battVoltage)/1000}V"
        return battChargeStatus, battLevel, battVoltage

    def scanNetworks(self) -> list[Network]:
        """Scan networks"""
        output = self.execute(Commands.scanOperators())

        networks: list[Network] = []
        pieces = output.split("(", 1)[1].split(")")

        for piece in pieces:
            piece = piece.replace(",(", "")
            subpieces = piece.split(",")
            if len(subpieces) != 4:
                continue
            networks.append(
                Network(
                    name=json.loads(subpieces[1]),
                    shortname=json.loads(subpieces[2]),
                    id=json.loads(subpieces[3]),
                )
            )
        return networks

    def getCurrentNetwork(self) -> str | None:
        """Get current network"""
        output = self.execute(Commands.currentOperator())
        network = output.split(",")[-1]

        if network.startswith('"'):
            network = network[1:]
        if network.endswith('"'):
            network = network[:-1]

        # If after filtering we did not filter anything: there was no network
        if network.startswith("+COPS"):
            return None

        return network

    def getSignalStrength(self) -> tuple[float, str]:
        """Get signal strength"""
        output = self.execute(Commands.signalQuality())
        rssi, rxQual = output.split(":")[1].split(",")
        # 30 is the maximum value (2 is the minimum)
        RSSI = float(rssi) * 100 / float(30) if rssi != "99" else 99
        # RxQual to BER conversion
        match int(rxQual):
            case 0:
                ber = "BER < 0.2%"
            case 1:
                ber = "0.2% < BER < 0.4%"
            case 2:
                ber = "0.4% < BER < 0.8%"
            case 3:
                ber = "0.8% < BER < 1.6%"
            case 4:
                ber = "1.6% < BER < 3.2%"
            case 5:
                ber = "3.2% < BER < 6.4%"
            case 6:
                ber = "6.4% < BER < 12.8%"
            case 7:
                ber = "12.8% < BER"
            case _:
                ber = f"99"

        return RSSI, ber

    def getIP(self) -> str | None:
        """Get IP address"""
        output = self.execute(Commands.bearerStatus())
        output = output.split("+")[-1]
        pieces = output.split(",")
        if len(pieces) != 3:
            raise Exception(f'Cannot parse "{output}" to get an IP address')
        ip_addr = pieces[2].replace('"', "")
        if len(ip_addr.split(".")) != 4:
            raise Exception(f'Cannot parse "{output}" to get an IP address')
        if ip_addr == "0.0.0.0":
            return None
        return ip_addr

    def connectGPRS(self, apn: str, username: str = "", password: str = "") -> str:
        """Connect to GPRS"""
        if not self.initialized:
            raise Exception("Modem is not initialized, cannot connect")

        # Are we already connected?
        self.ipAddr = self.getIP()
        if self.ipAddr:
            return self.ipAddr

        # Closing bearer if left opened from a previous connect gone wrong:
        try:
            self.execute(Commands.closeBearer())
        except GenericATError:
            pass
        except SpecificATError:
            pass

        # Set bearer parameters
        self.execute(Commands.setBearerGPRS())
        self.execute(Commands.setBearerAPN(apn))
        self.execute(Commands.setBearerUsername(username))
        self.execute(Commands.setBearerPassword(password))
        # Then, open the GPRS connection.
        self.execute(Commands.openBearer())

        # Ok, now wait until we get a valid IP address
        retries = 0
        max_retries = 5
        while True:
            retries += 1
            self.ipAddr = self.getIP()
            if not self.ipAddr:
                retries += 1
                if retries > max_retries:
                    raise Exception(
                        "Cannot connect modem as could not get a valid IP address"
                    )
                time.sleep(1)
            else:
                break
        self.GPRSinitialized = True
        return self.ipAddr

    def disconnectGPRS(self):
        # Close bearer
        try:
            self.execute(Commands.closeBearer())
        except GenericATError:
            pass
        except SpecificATError:
            pass

        # Check that we are actually disconnected
        ip_addr = self.getIP()
        if ip_addr:
            raise Exception(
                "Error, we should be disconnected but we still have an IP address ({})".format(
                    ip_addr
                )
            )
        self.GPRSinitialized = False

    def initHTTP(self) -> None:
        """Initialize HTTP service"""
        # Close any previous http connections
        try:
            self.closeHTTP()
        except GenericATError:
            pass
        except SpecificATError:
            pass
        # Initialize HTTP Service
        self.execute(Commands.initHTTP())
        # Bearer profile identifier
        self.execute(Commands.setHTTPParameterCID(1))
        self.HTTPinitialized = True

    def closeHTTP(self) -> None:
        """Terminate HTTP service"""
        self.execute(Commands.closeHTTP())
        self.HTTPinitialized = False

    def makeHTTPRequest(
        self,
        url: str,
        method: str = "GET",
        data: str = "",
        contentType="application/json",
    ) -> Response:
        """Make HTTP GET or POST request"""
        if not self.HTTPinitialized:
            raise Exception("HTTP service is not initialized")

        # Set url
        self.execute(Commands.setHTTPParameterURL(url))

        match method:
            case "GET":
                # GET
                output = self.execute(Commands.HTTPActionGET())
            case "POST":
                # Send data
                self.execute(Commands.setHTTPParameterContent(contentType))
                self.execute(Commands.HTTPData(len(data)))
                self.execute(Commands.dumpData(data))
                # POST
                output = self.execute(Commands.HTTPActionPOST())
            case _:
                raise Exception(f'Unsupported HTTP method "{method}"')

        return Response(
            status_code=output.split(",")[1],
            content=self.execute(Commands.HTTPRead(), clean_output=False),
        )

    def enableSSL(self):
        """Enable SSL"""
        if not self.sslSupported:
            raise Exception("SSL is not supported by this modem")
        self.execute(Commands.setSSL(1))

    def disableSSL(self):
        """Disable SSL"""
        if not self.sslSupported:
            raise Exception("SSL is not supported by this modem")
        self.execute(Commands.setSSL(0))
