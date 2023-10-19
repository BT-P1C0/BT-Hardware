"""
Modified microGPS
Original File: https://github.com/inmcm/micropyGPS/blob/master/micropyGPS.py
Used under MIT License
"""


class NMEAparser(object):
    """GPS NMEA Sentence Parser. Creates object that stores all relevant GPS data and statistics.
    Parses sentences one character at a time using update()."""

    # Max Number of Characters a valid sentence can be (based on GGA sentence)
    __NMEA_MAX_CHAR_COUNT = 90
    __HEMISPHERES = ("N", "S", "E", "W")

    def __init__(self):
        #####################
        # Object Status Flags
        self.sentence_active: bool = False
        self.active_segment: int = 0
        self.process_crc: bool = False
        self.gps_segments: list[str] = []
        self.crc_xor: int = 0
        self.char_count: int = 0

        #####################
        # Custom Data
        self.utc_time: float = 0
        self.lat: float = 0
        self.lng: float = 0

        self.valid: bool = False

    ########################################
    # Sentence Parsers
    ########################################
    def gprmc(self) -> bool:
        """Parse Recommended Minimum Specific GPS/Transit data (RMC)Sentence.
        Updates UTC timestamp, latitude, longitude, Course, Speed, Date, and fix status
        """

        # UTC Timestamp
        try:
            self.utc_time = float(self.gps_segments[1])

        except ValueError:  # Bad Timestamp value present
            return False

        # Check Receiver Data Valid Flag
        if self.gps_segments[2] == "A":  # Data from Receiver is Valid/Has Fix
            if self.gps_segments[4] not in self.__HEMISPHERES:
                return False

            if self.gps_segments[6] not in self.__HEMISPHERES:
                return False

            # Longitude / Latitude
            try:
                # Latitude
                self.lat = (
                    int(self.gps_segments[3][0:2])
                    + (float(self.gps_segments[3][2:]) / 60)
                ) * (1 if self.gps_segments[4] == "N" else -1)

                # Longitude
                self.lng = (
                    int(self.gps_segments[5][0:3])
                    + (float(self.gps_segments[5][3:]) / 60)
                ) * (1 if self.gps_segments[6] == "E" else -1)
            except ValueError:
                return False

            # Update Object Data
            self.valid = True

        else:  # Clear Position Data if Sentence is 'Invalid'
            self.lat = 0
            self.lng = 0
            self.valid = False

        return True

    def gpgll(self):
        """Parse Geographic Latitude and Longitude (GLL)Sentence. Updates UTC timestamp, latitude,
        longitude, and fix status"""

        # UTC Timestamp
        try:
            self.utc_time = float(self.gps_segments[5])

        except ValueError:  # Bad Timestamp value present
            return False

        # Check Receiver Data Valid Flag
        if self.gps_segments[6] == "A":  # Data from Receiver is Valid/Has Fix
            if self.gps_segments[2] not in self.__HEMISPHERES:
                return False

            if self.gps_segments[4] not in self.__HEMISPHERES:
                return False

            # Longitude / Latitude
            try:
                # Latitude
                self.lat = (
                    int(self.gps_segments[1][0:2])
                    + (float(self.gps_segments[1][2:]) / 60)
                ) * (1 if self.gps_segments[2] == "N" else -1)

                # Longitude
                self.lng = (
                    int(self.gps_segments[3][0:3])
                    + (float(self.gps_segments[3][3:]) / 60)
                ) * (1 if self.gps_segments[4] == "E" else -1)
            except ValueError:
                return False

            # Update Object Data
            self.valid = True

        else:  # Clear Position Data if Sentence is 'Invalid'
            self.lat = 0
            self.lng = 0
            self.valid = False

        return True

    def gpgga(self):
        """Parse Global Positioning System Fix Data (GGA) Sentence. Updates UTC timestamp, latitude, longitude,
        fix status, satellites in use, Horizontal Dilution of Precision (HDOP), altitude, geoid height and fix status
        """

        # UTC Timestamp
        try:
            self.utc_time = float(self.gps_segments[1])

            # Get Fix Status
            fix_stat = int(self.gps_segments[6])

        except (ValueError, IndexError):
            return False

        # Process Location and Speed Data if Fix is GOOD
        if fix_stat:
            if self.gps_segments[3] not in self.__HEMISPHERES:
                return False

            if self.gps_segments[5] not in self.__HEMISPHERES:
                return False

            # Longitude / Latitude
            try:
                # Latitude
                self.lat = (
                    int(self.gps_segments[2][0:2])
                    + (float(self.gps_segments[2][2:]) / 60)
                ) * (1 if self.gps_segments[3] == "N" else -1)

                # Longitude
                self.lng = (
                    int(self.gps_segments[4][0:3])
                    + (float(self.gps_segments[4][3:]) / 60)
                ) * (1 if self.gps_segments[5] == "E" else -1)
            except ValueError:
                return False

        return True

    ##########################################
    # Data Stream Handler Functions
    ##########################################

    def new_sentence(self) -> None:
        """Adjust Object Flags in Preparation for a New Sentence"""
        self.gps_segments = [""]
        self.active_segment = 0
        self.crc_xor = 0
        self.sentence_active = True
        self.process_crc = True
        self.char_count = 0

    def update(self, new_char) -> bool:
        """Process a new input char and updates GPS object if necessary based on special characters ('$', ',', '*')
        Function builds a list of received string that are validate by CRC prior to parsing by the  appropriate
        sentence function. Returns sentence type on successful parse, None otherwise"""

        valid_sentence = False

        # Validate new_char is a printable char
        ascii_char = ord(new_char)

        if 10 <= ascii_char <= 126:
            self.char_count += 1

            # Check if a new string is starting ($)
            if new_char == "$":
                self.new_sentence()
                return False

            elif self.sentence_active:
                # Check if sentence is ending (*)
                match new_char:
                    case "*":
                        self.process_crc = False
                        self.active_segment += 1
                        self.gps_segments.append("")
                        return False

                    # Check if a section is ended (,), Create a new substring to feed
                    # characters to
                    case ",":
                        self.active_segment += 1
                        self.gps_segments.append("")

                    # Store All Other printable character and check CRC when ready
                    case _:
                        self.gps_segments[self.active_segment] += new_char

                        # When CRC input is disabled, sentence is nearly complete
                        if not self.process_crc:
                            if len(self.gps_segments[self.active_segment]) == 2:
                                try:
                                    final_crc = int(
                                        self.gps_segments[self.active_segment], 16
                                    )
                                    if self.crc_xor == final_crc:
                                        valid_sentence = True
                                except ValueError:
                                    pass  # CRC Value was deformed and could not have been correct

                # Update CRC
                if self.process_crc:
                    self.crc_xor ^= ascii_char

                # If a Valid Sentence Was received and it's a supported sentence, then parse it!!
                if valid_sentence:
                    self.sentence_active = False  # Clear Active Processing Flag

                    if self.gps_segments[0] in self.supported_sentences:
                        # parse the Sentence Based on the message type, return True if parse is clean
                        if self.supported_sentences[self.gps_segments[0]](self):
                            # Let host know that the GPS object was updated by returning parsed sentence type
                            return True

                # Check that the sentence buffer isn't filling up with Garage waiting for the sentence to complete
                if self.char_count > self.__NMEA_MAX_CHAR_COUNT:
                    self.sentence_active = False

        # Tell Host no new sentence was parsed
        return False

    # All the currently supported NMEA sentences
    supported_sentences = {
        "GPRMC": gprmc,
        "GLRMC": gprmc,
        "GNRMC": gprmc,
    }


if __name__ == "__main__":
    pass
