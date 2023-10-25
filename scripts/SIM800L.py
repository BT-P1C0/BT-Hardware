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


network_registration: dict[str, str] = {
    "0": "Not registered, MT is not currently searching a new operator to register to",
    "1": "Registered, home network",
    "2": "Not registered, but MT is currently searching a new operator to register to",
    "3": "Registration denied",
    "4": "Unknown",
    "5": "Registered, roaming",
}

apn_list: dict[str, str] = {
    "airtel": "airtelgprs.com",
    "bsnl": "bsnlnet",
    "idea": "internet",
    "jio": "jionet",
}

http_action_status_codes: dict[str, str] = {
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


class LocationResponse(object):
    def __init__(
        self, code: int, lat: float, lng: float, acc: int, date: str, time: str
    ) -> None:
        self.code: int = code
        self.lat: float = lat
        self.lng: float = lng
        self.acc: int = acc
        self.date: str = date
        self.time: str = time

    def __str__(self) -> str:
        return f"LocationResponse({self.code}, {self.lat}, {self.lng}, {self.acc}, {self.date}, {self.time})"

    def __repr__(self) -> str:
        return self.__str__()


class Response(object):
    def __init__(self, status_code, content) -> None:
        self.status_code: int = int(status_code)
        self.status: str = http_action_status_codes.get(
            str(self.status_code), "Unknown"
        )
        self.content: str = content

    def __str__(self) -> str:
        return f"Response({self.status_code}, {self.status}, {self.content})"

    def __repr__(self) -> str:
        return self.__str__()


class ATCommand(object):
    def __init__(self, string: str, timeout: int, end: str) -> None:
        self.string: str = string
        self.timeout: int = timeout
        self.end: str = end

    def __str__(self) -> str:
        return f'ATCommand("{self.string}", {self.timeout}, "{self.end}")'

    def __repr__(self) -> str:
        return self.__str__()


class Network(object):
    def __init__(self, name: str, shortname: str, id: str) -> None:
        self.name: str = name
        self.shortname: str = shortname
        self.id: str = id

    def __str__(self) -> str:
        return f"Network({self.name}, {self.shortname}, {self.id})"

    def __repr__(self) -> str:
        return self.__str__()


class CellInfo(object):
    def __init__(
        self,
        operator: str,
        mcc: int,
        mnc: int,
        rxlev: int,
        cellId: int,
        afcn: int,
        lac: int,
        bsic: int,
    ):
        self.operator: str = operator
        self.mcc: int = mcc
        self.mnc: int = mnc
        self.lac: int = lac
        self.cellId: int = cellId
        self.bsic: int = bsic
        self.rxlev: int = rxlev
        self.afcn: int = afcn

    def __str__(self):
        return f"CellInfo(Operator: {self.operator}, MCC: {self.mcc}, MNC: {self.mnc}, LAC: {self.lac}, CellId: {self.cellId}, BSIC: {self.bsic}, RXLEV: {self.rxlev}, AFCN: {self.afcn})"

    def __repr__(self):
        return self.__str__()


class Commands(object):
    # sources:
    # https://cdn-shop.adafruit.com/datasheets/sim800_series_at_command_manual_v1.01.pdf
    # https://www.elecrow.com/wiki/images/2/20/SIM800_Series_AT_Command_Manual_V1.09.pdf
    # https://www.avnet.com/wps/wcm/connect/onesite/5ddc2831-b698-44ac-92f5-50d79a14cb3f/Heracles-SIMCOM_GSM+Location_Application+Note_V1.02.pdf?MOD=AJPERES&CVID=m31n15G&CVID=m31n15G&CVID=m31jwAj&CVID=m31jwAj
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
    def scanCellInfo() -> ATCommand:
        """Scan Cell Tower Info"""
        return ATCommand("AT+CNETSCAN", 60, "OK")

    @staticmethod
    def setCellInfoDetails(show: int) -> ATCommand:
        """Set Cell Tower Info\nShow:1 Hide:0"""
        return ATCommand(f"AT+CNETSCAN={show}", 3, "OK")

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
    def GSMLocation() -> ATCommand:
        """Get GSM Location & Time"""
        return ATCommand("AT+CLBS=4,1", 45, "OK")

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

        # Check if SIM card is inserted
        x = self.execute(Commands.isSIMInserted())
        if x != "+CSMINS: 0,1":
            raise Exception(f"SIM card is not inserted, Module Response: {x}")

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
                line_str: str = str(line, "UTF-8")

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
        if battChargeStatus == "0":
            battChargeStatus = "Not charging"
        elif battChargeStatus == "1":
            battChargeStatus = "Charging"
        elif battChargeStatus == "2":
            battChargeStatus = "Finished charging"
        else:
            battChargeStatus = "Power fault"

        # More conversions
        battLevel = f"{battLevel}%"
        battVoltage = f"{int(battVoltage)/1000}V"
        return battChargeStatus, battLevel, battVoltage

    def scanNetworks(self) -> list[Network]:
        """Scan networks"""
        output = self.execute(Commands.scanOperators())
        print(output)
        networks: list[Network] = []
        raw_networks = output.split(":", 1)[1].strip().split(",,")[0].split(",(")

        for raw_network in raw_networks:
            raw_networks = (
                raw_network.replace('"', "")
                .replace("(", "")
                .replace(")", "")
                .split(",")
            )
            if len(raw_networks) != 4:
                continue
            networks.append(
                Network(
                    name=raw_networks[1],
                    shortname=raw_networks[2],
                    id=raw_networks[3],
                )
            )

        return networks

    def getCurrentNetwork(self) -> dict | None:
        """Get current network"""
        output = self.execute(Commands.currentOperator())
        network = output.split(":")[1].strip().split(",")

        if len(network) != 3:
            return None

        return {
            "mode": network[0],
            "format": network[1],
            "oper": network[2].replace('"', ""),
        }

    def getServiceProviderName(self) -> str:
        """Get Service Provider Name"""
        output = self.execute(Commands.getServiceProviderName())
        return output.split(":")[1].split(",")[0].replace('"', "").strip()

    def networkRegisterationStatus(self) -> tuple[bool, str, str]:
        """Check if network is registered"""
        output = self.execute(Commands.checkNetworkRegistration())
        code = output.split(",")[1]
        return (code == "1" or code == "5", code, network_registration[code])

    def getAPN(self) -> str:
        provider = self.getServiceProviderName().lower()
        if provider in apn_list:
            return apn_list[provider]
        else:
            raise Exception(f'APN for "{provider}" not found')

    def getCellTowerInfo(self) -> list[CellInfo]:
        """Get Cell Tower Info"""
        self.execute(Commands.setCellInfoDetails(1))
        output: str = self.execute(Commands.scanCellInfo())
        lines: list[str] = output.split("\n")
        cells: list[CellInfo] = []

        for line in lines:
            rawCell: list[str] = line.split(",")
            if len(rawCell) != 8:
                continue
            cells.append(
                CellInfo(
                    operator=rawCell[0].split('"')[1],
                    mcc=int(rawCell[1].split(":")[1]),
                    mnc=int(rawCell[2].split(":")[1]),
                    rxlev=int(rawCell[3].split(":")[1]),
                    cellId=int(rawCell[4].split(":")[1], 16),
                    afcn=int(rawCell[5].split(":")[1]),
                    lac=int(rawCell[6].split(":")[1], 16),
                    bsic=int(rawCell[7].split(":")[1], 16),
                )
            )

        return cells

    def getSignalStrength(self) -> tuple[float, str]:
        """Get signal strength"""
        output = self.execute(Commands.signalQuality())
        rssi, rxQual = output.split(":")[1].split(",")
        # 30 is the maximum value (2 is the minimum)
        RSSI = float(rssi) * 100 / float(30) if rssi != "99" else 99
        # RxQual to BER conversion
        rxQual = int(rxQual)
        if rxQual == 0:
            ber = "BER < 0.2%"
        elif rxQual == 1:
            ber = "0.2% < BER < 0.4%"
        elif rxQual == 2:
            ber = "0.4% < BER < 0.8%"
        elif rxQual == 3:
            ber = "0.8% < BER < 1.6%"
        elif rxQual == 4:
            ber = "1.6% < BER < 3.2%"
        elif rxQual == 5:
            ber = "3.2% < BER < 6.4%"
        elif rxQual == 6:
            ber = "6.4% < BER < 12.8%"
        elif rxQual == 7:
            ber = "12.8% < BER"
        else:
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

    def getGsmLocation(self):
        """Get GSM Location & Time*\nTime is in the format of triangulation server, CST (UTC + 8) by default"""
        output = self.execute(Commands.GSMLocation())
        pieces = output.split(":", 1)[1].strip().split(",")

        if len(pieces) != 6:
            raise Exception(f'Cannot parse "{output}" to get GSM location')

        return LocationResponse(
            code=int(pieces[0]),
            lat=float(pieces[1]),
            lng=float(pieces[2]),
            acc=int(pieces[3]),
            date=pieces[4],
            time=pieces[5],
        )

    def connectGPRS(self, apn: str = "", username: str = "", password: str = "") -> str:
        """Connect to GPRS \n If no APN is provided, the APN will be automatically set based on the service provider name"""
        # If no APN is provided, the APN will be automatically set based on the service provider name
        if not apn:
            apn = self.getAPN()

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
        if username:
            self.execute(Commands.setBearerUsername(username))
        if password:
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
        contentType: str = "application/json",
    ) -> Response:
        """Make HTTP GET or POST request. NOTE: Initiale HTTP before making a request."""
        if not self.HTTPinitialized:
            raise Exception("HTTP service is not initialized")

        # Set url
        self.execute(Commands.setHTTPParameterURL(url))

        if method == "GET":
            # GET
            output = self.execute(Commands.HTTPActionGET())
        elif method == "POST":
            # Send data
            self.execute(Commands.setHTTPParameterContent(contentType))
            self.execute(Commands.HTTPData(len(data)))
            self.execute(Commands.dumpData(data))
            # POST
            output = self.execute(Commands.HTTPActionPOST())
        else:
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


if __name__ == "__main__":
    print("SIM800L driver\nRun using main.py")
