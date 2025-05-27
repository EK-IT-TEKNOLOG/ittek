# A simple GPS library parsing the $GPGGA, $GPRMC and $GPZDA
# Developed on u-blox NEO-7M, milliseconds are not parsed
#
# Initialize parameters
#    UART number
#    Use all NMEA frames or not
#
# Available functions
#    get_utc_month()
#    get_utc_day()
#    get_utc_hours()
#    get_utc_minutes()
#    get_utc_seconds()
#
#    get_latitude()
#    get_longitude()
#    get_altitude()
#
#    get_fix_quality()
#    get_satellites()
#    get_hdop()
#    get_validity()
#
#    get_speed(unit)
#    get_course()
#
#    get_frames_received()
#    clear_frames_received()
#
#    get_latest_frame()
#
#    write(string)
#    receive_nmea_data(echo)

# Helper functions: Converts NMEA lat/long string to decimal degrees
def nmea2deg(string, quadrant):      # e.g. 1234.5678
    l_f = float(string)                # Convert the input string to a float
    l_i = int(l_f / 100)               # Get the degrees part
    l_d = (l_f - l_i * 100) / 60.0     # Convert the remainder to decimal degrees
    deg = l_i + l_d                    # Put the parts together
    if quadrant == 'S' or quadrant == 'W': # If south or west make the value negative
        deg = -deg
    return deg


def check_nmea_frame(string):

    string = string.strip()
    chk_sum_str = string[len(string) - 2:]
    frame_data = string[1:len(string) - 3]
    
    chk_sum = 0
    for ch in frame_data:
       chk_sum ^= ord(ch)
    
    if chk_sum == int(chk_sum_str, 16):
       return True

    return False


class GPS_SIMPLE:
    __nmea_buffer = ""                 # NMEA receive buffer
    
    __utc_year = 0                     # UTC
    __utc_month = 0
    __utc_day = 0
    __utc_hours = 0
    __utc_minutes = 0
    __utc_seconds = 0

    __latitude = -999.0                # Decimal degrees
    __longitude = -999.0               # Decimal degrees
    __altitude = 0.0                   # in m

    __validity = "V"                   # Void
    __fix_quality = 0                  # 0: invalid, 1: GPS, 2: DGPS
    __satellites = 0
    __hdop = 0.0
    
    __speed = 0.0
    __course = 0.0
    
    __latest_frame = ""
    __frames_received = 0              # May be queried to find out if even invalid frames have been received
                                       # GGA = 0x0001, RMC = 0x0002 and ZDA = 0x0004, see other bits below
    
    def __init__(self, uart, all_nmea = False):
        self.uart = uart
        self.all_nmea = all_nmea

        # Enable relevant and wanted NMEA frames
        uart.write("$PUBX,40,GGA,1,1,1,0*5B\n")     # Make sure the $GPGGA, $GPRMC and $GPZDA are always enabled
        uart.write("$PUBX,40,RMC,1,1,1,0*46\n")
        uart.write("$PUBX,40,ZDA,1,1,1,0*45\n")

        if self.all_nmea == True:
            uart.write("$PUBX,40,GLL,1,1,1,0*5D\n") # Enable the rest of the NMEA frames, 0x0008
            uart.write("$PUBX,40,GRS,1,1,1,0*5C\n") # 0x0010
            uart.write("$PUBX,40,GSA,1,1,1,0*4F\n") # 0x0020
            uart.write("$PUBX,40,GST,1,1,1,0*5A\n") # 0x0040
            uart.write("$PUBX,40,GSV,1,1,1,0*58\n") # 0x0080
            uart.write("$PUBX,40,VTG,1,1,1,0*5F\n") # 0x0100
        else:  
            uart.write("$PUBX,40,GLL,0,0,0,0*5C\n") # Disable all but the $GPGGA, $GPRMC and $GPZDA frames
            uart.write("$PUBX,40,GRS,0,0,0,0*5D\n")
            uart.write("$PUBX,40,GSA,0,0,0,0*4E\n")
            uart.write("$PUBX,40,GST,0,0,0,0*5B\n")
            uart.write("$PUBX,40,GSV,0,0,0,0*59\n")
            uart.write("$PUBX,40,VTG,0,0,0,0*5E\n")            

        self.__frames_received = 0     # Clear frames received just in case some frames were received before initialization was completed
    

    def __parse_nmea_frame(self, string):# Change to parse all relevant frames: http://aprs.gids.nl/nmea/, no checksum validation
        
        if check_nmea_frame(string) == True:# Validate the frame against the checksum
        
            subframe = string.split(',')   # Split the NMEA frame into parts
            
            # Parse $GPGGA
            if subframe[0] == "$GPGGA":    # $GPGGA,205019.00,5449.69634,N,01156.28487,E,1,12,0.98,29.3,M,39.7,M,,*6B
                self.__frames_received |= 0x0001 # Set the frame ID bit

                # UTC hours, minutes and seconds
                if len(subframe[1]) > 5:
                    self.__utc_hours = int(subframe[1][0:2])
                    self.__utc_minutes = int(subframe[1][2:4])
                    self.__utc_seconds = int(subframe[1][4:6])
                
                # Latitude
                if len(subframe[2]) > 0 and len(subframe[3]) > 0:
                    self.__latitude = nmea2deg(subframe[2], subframe[3])
                
                # Longitude
                if len(subframe[4]) > 0 and len(subframe[5]) > 0:
                    self.__longitude = nmea2deg(subframe[4], subframe[5])

                # Fix quality, higher is better
                if len(subframe[6]) > 0:
                    self.__fix_quality = int(subframe[6])
            
                # Number of satellites, higher is better
                if len(subframe[7]) > 0:
                    self.__satellites = int(subframe[7])
            
                # HDOP, less is better
                if len(subframe[8]) > 0:
                    self.__hdop = float(subframe[8])
            
                # Altitude
                if len(subframe[9]) > 0:
                    self.__altitude = float(subframe[9])
       

            # Parse $GPRMC                        
            elif subframe[0] == "$GPRMC":  # $GPRMC,081836.00,A,3751.65,S,14507.36,E,000.0,360.0,130998,011.3,E*62
                self.__frames_received |= 0x0002 # Set the frame ID bit
                
                # UTC hours, minutes and seconds
                if len(subframe[1]) > 5:
                    self.__utc_hours = int(subframe[1][0:2])
                    self.__utc_minutes = int(subframe[1][2:4])
                    self.__utc_seconds = int(subframe[1][4:6])
            
                # Validity
                if len(subframe[2]) > 0:
                    self.__validity = subframe[2]
                 
                # Latitude
                if len(subframe[3]) > 0 and len(subframe[4]) > 0:
                    self.__latitude = nmea2deg(subframe[3], subframe[4])
                
                # Longitude
                if len(subframe[5]) > 0 and len(subframe[6]) > 0:
                    self.__longitude = nmea2deg(subframe[5], subframe[6])                    
                    
                # Speed, m/s
                if len(subframe[7]) > 0:
                    self.__speed = float(subframe[7])
            
                # Course, °
                if len(subframe[8]) > 0:
                    self.__course = float(subframe[8])
            
                # UTC year, month, day
                if len(subframe[9]) > 5:
                    self.__utc_day = int(subframe[9][0:2])
                    self.__utc_month = int(subframe[9][2:4])
                    self.__utc_year = 2000 + int(subframe[9][4:6])


            # Parse $GPZDA
            elif subframe[0] == "$GPZDA":  # $GPZDA,143042.00,25,08,2005,,*6E
                self.__frames_received |= 0x0004 # Set the frame ID bit
                
                # UTC hours, minutes and seconds       
                if len(subframe[1]) > 5:
                    self.__utc_hours = int(subframe[1][0:2])
                    self.__utc_minutes = int(subframe[1][2:4])
                    self.__utc_seconds = int(subframe[1][4:6])
                
                # UTC day
                if len(subframe[2]) > 0:
                    self.__utc_day = int(subframe[2])
                    
                # UTC month
                if len(subframe[3]) > 0:
                    self.__utc_month = int(subframe[3])

                # UTC year
                if len(subframe[4]) > 0:
                    self.__utc_year = int(subframe[4])
                
            
            # Check if other frames are received and if so set the frame ID bit
            elif subframe[0] == "$GPGLL":
                self.__frames_received |= 0x0008 # Set the frame ID bit
            elif subframe[0] == "$GPGRS":
                self.__frames_received |= 0x0010 # Set the frame ID bit
            elif subframe[0] == "$GPGSA":
                self.__frames_received |= 0x0020 # Set the frame ID bit
            elif subframe[0] == "$GPGST":
                self.__frames_received |= 0x0040 # Set the frame ID bit
            elif subframe[0] == "$GPGSV":
                self.__frames_received |= 0x0080 # Set the frame ID bit
            elif subframe[0] == "$GPVTG":
                self.__frames_received |= 0x0100 # Set the frame ID bit
        
        
    # Get the UTC year
    def get_utc_year(self):
        return self.__utc_year


    # Get the UTC month
    def get_utc_month(self):
        return self.__utc_month


    # Get the UTC day
    def get_utc_day(self):
        return self.__utc_day
    
    
    # Get the UTC hours
    def get_utc_hours(self):
        return self.__utc_hours


    # Get the UTC minutes
    def get_utc_minutes(self):
        return self.__utc_minutes

    
    # Get the UTC seconds
    def get_utc_seconds(self):
        return self.__utc_seconds


    # Get the latitude, decimal degrees
    def get_latitude(self):
        return self.__latitude


    # Get the longitude, decimal degrees
    def get_longitude(self):
        return self.__longitude

    
    # Get the fix quality
    def get_fix_quality(self):
        return self.__fix_quality


    # Get the number of satellites used
    def get_satellites(self):
        return self.__satellites


    # Get the HDOP, lower value is better
    def get_hdop(self):
        return self.__hdop


    # Get the altitude, m
    def get_altitude(self):
        return self.__altitude
    
    # Get the validity of the signal
    def get_validity(self):
        return self.__validity

    
    # Get the speed, where unit controls which unit the speed is returned in
    def get_speed(self, unit = 0):
        if unit == 0:
            speed = self.__speed * 1852 / 3600 # m/s
        elif unit == 1:
            speed = self.__speed * 1.852       # km/s
        elif unit == 2:
            speed = self.__speed * 1.15077945  # miles/h, approx
        elif unit == 3:
            speed = self.__speed * 1.687810    # feet/s, approx            
        elif unit == 4:
            speed = self.__speed               # knots
        else:
            speed = -1                         # illegal unit
        return speed
    
    
    # Get the course
    def get_course(self):
        return self.__course
    
    
    # Get the latest frame received
    def get_latest_frame(self):
        return self.__latest_frame    

    
    # Get the bitmask of the NMEA frames received
    def get_frames_received(self):
        return self.__frames_received
    
    
    # Clear the received frames flags. See above which bit represent which frame
    def clear_frames_received(self):
        self.__frames_received = 0

    
    # Write a command string to the GPS receiver
    def write(self, string):
        self.uart.write(string, end = '')
        return 
    

    # The receiver funtion, call at least once per second
    def receive_nmea_data(self, echo = False): # Returns true if data was parsed, otherwise false
        self.__nmea_buffer
      
        if self.uart.any() > 0:
            string = self.uart.readline() # Collect incoming chars
            try:
                self.__nmea_buffer += string.decode("ascii")  # "utf-8" UART returns bytes. They have to be conv. to chars/a string
                if "\n" in self.__nmea_buffer:
                    if echo:
                        print(self.__nmea_buffer, end = '')   # Echo the received frame
                    self.__parse_nmea_frame(self.__nmea_buffer)
                    self.__latest_frame = self.__nmea_buffer
                    self.__nmea_buffer = ""
                    return True
            except:                    # Only happen when the first partial frame is received. No need to cause any alarm
                None                   # The problem is in the decode() MicroPython implementation
            
        return False
    
       
# EOF ##################################################################
