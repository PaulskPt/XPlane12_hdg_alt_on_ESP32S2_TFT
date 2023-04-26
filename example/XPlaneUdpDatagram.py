
# _*_ coding: utf-8 _*_
# SPDX-FileCopyrightText: 2023 Paulus Schulinck
#
# SPDX-License-Identifier: MIT
##############################
#
# Extracted from @PaulskPt's XPlaneUdpDatagramLCD.py
# Ver 11, 2019-08-13 10h22 UTC
# See: # Original see: I:\Raspberry_Pi\XPlane_datarefs\xp_data_outp_rx\XPlaneUdpDatagramLCDv11.py
#
# Class to get UDP Datagram packets from X-Plane 11 Flight Simulator via a (local area) network.
# License: GPLv3
# Original idea for the X-Plane UDP Data Output receiver, "XPlaneUdp.py", by charlylima
# See: https://github.com/charlylima/XPlaneUDP
# Charlylima's python script was to detect BECN packets and then to ask and receive DataRef packets.
#
# This python script is a modified and extended version of Charlylima's script.
# The target of this script is to detect UDP Datagram packets, sent by an X-Plane host to a Multicast group (LAN).
# The script also has a RaspiCheckCPUTemp Class to retrieve and print on the LCD the temperature of the CPU.
# Further this script has a functionality to print selected data to a 4x20 char LCD screen.
# This script has been developed and tested on a custom made Raspberry Pi CM IO board by Hasseb.fi, containing a Raspberry CM3 and a LCD from Hitachi.
#
# The XPlaneUdp.py example was downloaded from GitHub: https://github.com/charlylima/XPlaneUDP
# Charlylima states "that he witten it for Python 3 but I, Paulsk, have adapted it for running under Python 2(7.2)
#
# In Version 10 added implementation of LCD writing a string to a line,col. Example:
# lcd.lcd_display_string_pos('', 4, 20)
#
# In version 11 added a line in lcd_cleanup() to switch off the backlight.
#
# Comments, suggestions and feedback is welcome.
# 2019-04-24, Paulsk (mailto: ct7agr@live.com.pt)
# 2023-03-27, Adapted for an Adafruit Feather ESP32-S2 TFT
#type:ignore
from common import *
import time
import sys
import struct
import binascii
import gc

# ==========================================
#                                          =
# Class created and tested by Paulsk,      =
# has some parts originated by Charlylima  =
#                                          =
# ==========================================
class XPlaneUdpDatagram():
    '''
    Get data from XPlane via network.
    Use a class to implement RAI* Pattern for the UDP socket.

    Note Paulsk: I didn't know what was meant by "RAI". I googled. I came across this webpage from the University of Maastricht (NL)
    btw: the town where I was born and lately lived (2008-2012). Rai stands here for: "Robots, Agents and Interaction group".
    I don't know yet if Charlylima was referring to this group by mentioning "RAI Pattern" above.
    '''

    # udp_unpack_str01 = "<iffffifff"
    # udp_unpack_str02 = "<iffffiiii"
    # udp_unpack_str03 = "<ifffiiiff"
    # udp_unpack_str04 =  "iiiiiiiif"   old: "<iffffffffff"

    # <drive:>\Dropbox\<User>\Flightsimming\Sim Innovations\2019-04-10_other_tests_AP3.5_with_Raspi3bplus

    def __init__(self):

        TAG = tag_adjust("dg.__init__(): ")
        if not my_debug:
            print(TAG+'Entering...', file=sys.stderr)
        BUFFER_SIZE = 2000
        MESSAGE = ''
        DUMMY_STR_DOUBLE = ' ' * 8   # Data type FLOAT placeholder
        DUMMY_STR_FLOAT  = ' ' * 4   # Data type INT placeholder
        DUMMY_STR_INT    = ' ' * 4


        # list of requested datarefs with index number
        self.datarefidx = 0
        self.datarefs = {} # key = idx, value = dataref
        self.values = {}
        self.dataFLTSTS = []
        self.udp_host = str(wifi.radio.ipv4_address)
        self.use_udp_host = True if myVars.read("use_udp_host") == "1" else False
        if self.use_udp_host:
            self.MCAST_GRP = myVars.read("multicast_group1")
            self.MCAST_PORT = myVars.read("multicast_port1")
        else:
            self.MCAST_GRP = myVars.read("multicast_group2")
            self.MCAST_PORT = myVars.read("multicast_port2")
        if my_debug:
            print(TAG+'self.MCAST_GRP= {}'.format(self.MCAST_GRP), file=sys.stderr)
            print(TAG+'self.MCAST_PORT= {}'.format(self.MCAST_PORT), file=sys.stderr)

        self.START_TIME = time.time()
        self.GS_NIL = False
        self.GS_KTS = 0.0
        self.dme3_or_gs = False # If this flag is True then the dme-3_freq will be displayed on the LCD
                               # if this flag is False then the Groundspeed (GS) will be displayed on the LCD
        # See GetUDPDatagram()
        self.retval = []
        self.packet = []
        self.packet_length = 149  # Update 2023-02-02: Also with X-Plane 12 the Multicast to group 239.255.1.1 destination port 49707 had a length of 149 bytes
        self.sender = None
        self.sock = None # my_sock
        self.size = 0
        self.timeout_cnt = 0

        if my_have_tft:
            self.hdg_alt_lst = [] # Added for use with Adafruit Feather ESP32-S2 TFT
        self.udp_types = {
          3:  'Speeds',
         17: 'Pitch, roll, & headings',
         20: 'Latitude, longitude, & altitude',
        102: 'dme',
        }
        
        # Issue command 'sys.byteorder' to get the byteorder (little or big endian) that the operating system uses
        # sys.byteorder gave as result: 'little'

        self. udp_unpack_str_3 = "<iffffifff"   # i = unsigned int , standard size = 4 bytes. f = float, standard size = 4 bytes
        
        self.values_struct_3 = { # udp_unpack_str_3 = "iffffifff"
        'ID':          DUMMY_STR_INT,     # DATA and a NULL
        'vind_kias':   DUMMY_STR_FLOAT,   # FLOAT vind_kias   airspeed in knots indicated air speed
        'vind_keas':   DUMMY_STR_FLOAT,   # FLOAT vind_keas   airspeed in knots e... air speed
        'vtrue_ktas':  DUMMY_STR_FLOAT,   # FLOAT vtrue_ktas  true airspeed in knots
        'vtrue_ktgs':  DUMMY_STR_FLOAT,   # FLOAT vtrue_ktgs  true ground speed in knots
        'nothing':     DUMMY_STR_INT,     # INT filling
        'vind_mph':    DUMMY_STR_FLOAT,   # FLOAT vind_mph    indicated airspeed in miles-per-hour
        'vtrue_mphas': DUMMY_STR_FLOAT,   # FLOAT vtrue_mphas  true airspeed in miles-per-hour
        'vtrue_mphgs': DUMMY_STR_FLOAT    # FLOAT vtrue_mphgs  true groundspeed in miles-per-hour
        }

        self.udp_unpack_str_17 = "<ifffiffif"  # was: "iffffiiii"
        
        self.values_struct_17 = { # udp_unpack_str_17 = "ifffiffif"   was: "iffffiiii"
            'ID':         DUMMY_STR_INT,
            'pitch_deg':  DUMMY_STR_FLOAT,
            'roll_deg':   DUMMY_STR_FLOAT,
            'hding_true': DUMMY_STR_FLOAT,
            'nothing1':   DUMMY_STR_INT,                   
            'hding_mag':  DUMMY_STR_FLOAT,
            'mavar_deg':  DUMMY_STR_FLOAT,
            'nothing2':   DUMMY_STR_INT,
            'mag_comp':   DUMMY_STR_FLOAT
            }

        self.udp_unpack_str_20 = "<iffffffff"
        
        self.values_struct_20 = { # udp_unpack_str_20 = "iffffffff"
            'ID':          DUMMY_STR_INT,
            'lat_deg':     DUMMY_STR_FLOAT,
            'lon_deg':     DUMMY_STR_FLOAT,
            'CG_ftmsl':    DUMMY_STR_FLOAT,
            'gear_ftagl':  DUMMY_STR_FLOAT,
            'terrn_ftmsl': DUMMY_STR_FLOAT,
            'p-alt_ftmsl': DUMMY_STR_FLOAT,
            'lat_orign':   DUMMY_STR_FLOAT,
            'lon_orign':   DUMMY_STR_FLOAT
            }

        self.udp_unpack_str_102 = "<iffffffii"   # was: "iiiiiiiif"

        self.values_struct_102 = { # 2019-05-01 18h23PT udp_unpack_str_102 = iiiiiiiif  --> old: "<ifffiiiff"  --> old unpack string: "ifiifffif"
            'ID':         DUMMY_STR_INT,
            'dme_nav01':  DUMMY_STR_FLOAT, # dme of nav1
            'dme_mode':   DUMMY_STR_INT,   # dme mode (1 = dme1, 2= dme2)
            'dme_found':  DUMMY_STR_INT,   # dme found  1.0000
            'dme_dist':   DUMMY_STR_FLOAT, # dme distance (nm)
            'dme_speed':  DUMMY_STR_FLOAT, # dme speed    (kts)
            'dme_time':   DUMMY_STR_FLOAT, # dme_time (time-to-station)
            'dme_n-typ':  DUMMY_STR_INT,   # dme n-typ (3.0000)
            'dme-3_freq': DUMMY_STR_FLOAT, # dme3 freq (this is the 3rd, dme receiver (usually not reacheable)
            }
        
        self.udp_unpack_str5 = "<idddffffffffff"  # was: "iiiiiiiif"  4 + (3 x 8) + (10 x 4)   4 + 24 + 40 = 68 bytes
         
        self.values_struct5 = {    # udp_unpack_str5 = "ffffffffff"
            'ID':          DUMMY_STR_INT,        # RPOS and a NULL
            'dat_lon':     DUMMY_STR_DOUBLE,     # DOUBLE dat_long
            'dat_lat':     DUMMY_STR_DOUBLE,     # DOUBLE dat_lat
            'dat_ele':     DUMMY_STR_DOUBLE,     # DOUBLE dat_ele      elevation above sea level in meters
            'y_agl_mtr':   DUMMY_STR_FLOAT,      # FLOAT y_agl_mtr     elevation above the terrain in meters
            'veh_the_loc': DUMMY_STR_FLOAT,      # FLOAT veh_the_loc   pitch, degrees
            'veh_psi_loc': DUMMY_STR_FLOAT,      # FLOAT veh_psi_loc   true heading, in degrees
            'veh_phi_loc': DUMMY_STR_FLOAT,      # FLOAT veh_phi_loc   roll, in degrees
            'vx_wrl':      DUMMY_STR_FLOAT,      # FLOAT vx_wrl        speed in the x, EAST drection
            'vy_wrl':      DUMMY_STR_FLOAT,      # FLOAT vy_wrl        speed in the y, UP direction
            'vz_wrl':      DUMMY_STR_FLOAT,      # FLOAT vz_wrl        speed in the z, SOUTH direction
            'Prad':        DUMMY_STR_FLOAT,      # FLOAT Prad          roll rate in radians per second
            'Qrad':        DUMMY_STR_FLOAT,      # FLOAT Qrad          pitch rate in radians per second
            'Rrad':        DUMMY_STR_FLOAT       # FLOAT Rrad          yaw rate in radians per second
            }

        # values from xplane
        self.BeaconData = {}
        self.xplaneValues = {}
        self.defaultFreq = 1

        # The next line must be at the end, below all other constant definitions !!!
        self.LCDFill() # Print the framework on the LCD

    # The socket definitions in function OpenUDPSocket() were before inside the FindIp() function in Charlylima's file: XPlaneUdp.py
    def OpenUDPSocket(self, start):
        global pool
        TAG = tag_adjust("dg.OpenUDPSocket(): ")
        udp_host = None

        mcast_pack_str = "=4sl"
        # open socket to receive X-Plane 11's UDP Datagrams to a multicast group.

        try:
            if pool is None:
                if my_debug:
                    print(TAG+'pool is None. Going to create it', file=sys.stderr)
                pool = make_pool()
            if pool is not None:
                if my_debug:
                    print(TAG+'type(pool)= {}'.format(type(pool)), file=sys.stderr)
            else:
                raise ValueError(f"pool must be not None. Got {pool}")

            self.sock = pool.socket(pool.AF_INET, pool.SOCK_DGRAM) # , pool.IPPROTO_UDP)
            if my_debug:
                print(TAG+'type(self.sock)= {}'.format(type(self.sock)), file=sys.stderr)
            #self.sock.setsockopt(pool.SOL_SOCKET, pool.SO_REUSEADDR, 1)

            if my_debug:
                print(TAG+'self.use_udp_host= {}'.format(self.use_udp_host), file=sys.stderr)
                print(TAG+'type(wifi)= {}'.format(type(wifi)), file=sys.stderr)
            if self.use_udp_host:
                udp_host = self.udp_host
            else:
                #udp_host = str(wifi.radio.ipv4_address)
                if my_debug:
                    print(TAG+'type(self.MCAST_GRP)= {}'.format(type(self.MCAST_GRP)), file=sys.stderr)
                udp_host = self.MCAST_GRP
            self.sock.bind((udp_host, self.MCAST_PORT))
            if start and not my_debug:
                print(TAG+'waiting for packets on host {}, port {}'.format(udp_host, self.MCAST_PORT), file=sys.stderr)

        except ValueError as e:
            print(TAG+'Error: {}'.format(e), file=sys.stderr)
            raise
        except Exception as e:
            print(TAG+'Error: {}'.format(e), file=sys.stderr)
            raise

        if my_debug:
            print(TAG+'type of object to return: self.sock= {}'.format(type(self.sock)), file=sys.stderr)

        return self.sock

    # Function created by Paulsk
    def CloseUDPSocket(self):
        TAG = tag_adjust("dg.CloseUDPSocket(): ")
        lResult = False
        if self.sock is not None:
            lResult = self.sock.close()
            if my_debug:
                print(TAG+'result self.sock.close() = {}'.format(lResult), file=sys.stderr)
            if lResult is None:  # result of sock.close() is None
                self.sock = None

    def GetUDPSocket(self):
        return self.sock

    def packet_has_data(self, packet):
        TAG = tag_adjust("dg.packet_has_data(): ")
        b_cnt = 0
        le = len(packet)
        # print(TAG+'packet contents= {}'.format(packet), file=sys.stderr)
        if le >= 0:
            for _ in range(le):
                # print(TAG+'value byte nr {} is {}'.format(_, packet[_]), file=sys.stderr)
                if packet[_] > 0:
                    break
                else:
                    b_cnt += 1
            if b_cnt == le or b_cnt == le -1:
                if not my_debug:
                    print(TAG+'{} nr of 0x00 bytes found. Packet doesn\'t contain data.'.format(b_cnt), file=sys.stderr)
                return False
        return True

    # Added 2023-03-27
    def datagram_test(self):
        TAG = tag_adjust("dg.datatagram_test(): ")
        lResult = self.GetUDPDatagram()
        self.CloseUDPSocket()
        if my_debug:
            print(TAG+'return value= {}'.format(lResult), file=sys.stderr)
        return lResult

    # Function created by Paulsk
    def GetUDPDatagram(self):
        TAG = tag_adjust("dg.GetUDPDatagram(): ")
        mcast_pack_str = "=4sl"
        '''
        Find the IP of XPlane Host in Network.
        It takes the first one it can find.
        '''
        headerlen = 5
        self.retval = []
        lretval = False
        self.packet = []
        #self.packet_length = 149  # Update 2023-02-02: Also with X-Plane 12 the Multicast to group 239.255.1.1 destination port 49707 had a length of 149 bytes
        self.sender = None
        self.size = 0
        self.timeout_cnt = 0
        t = None

        if my_debug:
            print(TAG+'type(self.sock)= {}'.format(type(self.sock)), file=sys.stderr)

        # open the UDP socket
        if self.sock is None:
            self.sock = self.OpenUDPSocket(True)

        self.packet = bytearray(self.packet_length)

        """
        le_p = len(self.packet)

        if le_p > 0:
            if not self.packet_has_data(self.packet):
                if not my_debug:
                    print(TAG+'len(self.packet)= {}, however it does not contain data'.format(le_p))
                return 0
        """
        if my_debug:
            print(TAG+'type(self.retval)= {}. nr of items= {}'.format(type(self.retval), len(self.retval)), file=sys.stderr)

        while len(self.retval) == 0:
            # receive data
            try:
                # C-Examples see: https://github.com/dotsha747/libXPlane-UDP-Client/blob/master/src/libsrc/XPlaneUDPClient.cpp
                # Next 'Remembrance' lines copied from the 'dotsha' GitHub page.
                #
                # Check for other messages here. Be sure to check recv_len first as
                # we can also receive -1 if socket timeouts.
                #
                # Check for unsubscribed RREFs. These are where we have datarefs that we think
                # are subscribed, but have not received any data. If nothing has been received
                # in more than 5 seconds, we should resend the subscribe message.
                #
                # IMPORTANT NOTE: in the next line: when I changed the value of "self.packet_length" from 114 to 149,
                # I began to receive again the "dme" packets with ID 102 !
                # self.packet, self.sender = self.sock.recvfrom(self.packet_length) # was originally: sock.recvfrom(15000).
                self.size, self.sender = self.sock.recvfrom_into(self.packet)
                if my_debug:
                    print(TAG+'contents received packet= {}'.format(self.packet), file=sys.stderr)
                """The X-Plane 11 log.txt reports a message length 113 (= 0..112) but I discovered
                that it is 0..113, thus 114 bytes"""
                if not self.packet:
                    print(TAG+'Received packet is empty. Exiting.', file=sys.stderr)
                    break
                else:
                    header = self.packet[0:headerlen-1]   # note the modified "headerlen-1" We take just the first 4 characters
                    if my_debug:
                        print(TAG+'packet header= {}'.format(header), file=sys.stderr)

                    #if my_debug:
                    #    print('GetUDPDatagram(): header contents is: {}'.format(header), file=sys.stderr)
                    #============================================================================================================
                    # Addition by Paulsk:
                    # see file: F:\X-Plane 11\Instructions\X-Plane SPECS from Austin\Exchanging Data with X-Plane.rftd    XT.rtf,
                    # page 23.
                    # This starts with:
                    # Once you are receiving the BEACON messages from X-Plane, the struct must be interpreted as follows:
                    #     5-character MESSAGE PROLOGUE which indicates the type of the following struct as BECN\0
                    #===========================================================================================================
                    # X-Plane 12 see: F:\X-Plane 12\Instructions\Broadcast To All Mapping Apps format.rtfd
                    #============================================================================================================
                    # * Data
                    #data = packet[headerlen:21]
                    if my_debug:
                        print(TAG+'udp_packet_types.keys()= {}'.format(udp_packet_types.keys()), file=sys.stderr)
                        print(TAG+'udp_packet_types_rev.keys()= {}'.format(udp_packet_types_rev.keys()), file=sys.stderr)

                    if header == b'BECN':
                        pass  # We don't handle BECN packets here.
                                # We also don't want that BECN packets are reported as "unknown packets", handled by 'else:' below.

                    if header in [b'DATA', b'XATT', b'XGPS', b'XTRA']: # was: header == b'DATA':
                        """Arrived an UDP Datagram packet
                        Decode the packet. Result is a python dict (like a map in C) with values from X-Plane.
                        Example:
                        {'latitude': 47.72798156738281, 'longitude': 12.434000015258789,
                        'altitude MSL': 1822.67, 'altitude AGL': 0.17, 'speed': 4.11,
                        'roll': 1.05, 'pitch': -4.38, 'heading': 275.43, 'heading2': 271.84}
                        values = packet[headerlen:]"""
                        self.retval = self.DecodePacket()
                        if my_debug:
                            print(TAG+'self.retval= {}\n'.format(self.retval), file=sys.stderr) # print the UDP Datagram
                    else:
                        """ We have no BECN message neither we have an UDP Datagram"""
                        print(TAG+'Unknown packet from {}'.format(self.sender[0]), file=sys.stderr)
                        print(TAG+'{} bytes'.format(str(len(self.retval)+1)), file=sys.stderr)
                        print(TAG+'decoded packet: {}'.format(self.retval), file=sys.stderr)
                        print(binascii.hexlify(self.retval), file=sys.stderr)
                        # t = raw_input('Press enter to continue: ')
            except pool.timeout:
                print(TAG+'go-around nr: {:2d}, Socket timed out error'.format(self.timeout_cnt), file=sys.stderr)
                self.timeout_cnt = self.timeout_cnt + 1
                if self.timeout_cnt >= 11:
                    break
            except AttributeError as e: # for example: ... has no attribute lcd
                print(TAG+'Error: {}'.format(e), file=sys.stderr)
                break
            except Exception as e:
                print(TAG+'Error: {}'.format(e), file=sys.stderr)
            except KeyboardInterrupt:
                myVars.write("kbd_intr", True)
                break

        if len(self.retval) > 0:
            lretval = True
        if my_debug:
            print(TAG+'return value= {}'.format(lretval), file=sys.stderr)
        return lretval

    def LCDFill(self):
        global Hasseb_lcd, Loose_lcd, my_have_tft

        if self.dme3_or_gs:
            t= "DME3:        frq MHz "
        else:
            t= " GS:       kts      "

        if Hasseb_lcd:
            lcd._set_cursor_pos((1, 0))
            lcd.write_string(t)
            lcd._set_cursor_pos((2, 0))
            lcd.write_string("HDG:        degs     ")
            lcd._set_cursor_pos((3, 0))
            lcd.write_string("ALT:       ft MSL   ")
            lcd._set_cursor_pos((3,19))
            #t= raw_input('Press enter to continue: ')
        elif Loose_lcd:
            lcd.lcd_display_string_pos(t,2,0)
            lcd.lcd_display_string_pos("HDG:       degs   ",3,0)
            lcd.lcd_display_string_pos("ALT:       ft MSL ",4,0)
            lcd.lcd_display_string_pos('', 4, 20)

    def disp_hdg_alt(self):
        global xp, xp_grp, my_page_layout, main_group
        TAG= tag_adjust("disp_hdg_alt(): ")
        # Update this to change the text displayed.
        disp_hdg_alt = False
        x = myVars.read("xp")
        x_lst = myVars.read("xp_lst")
        if my_debug:
            print(TAG+'myVars.read("xp")= {}, ...("xp_lst")= {}'.format(x, x_lst), file=sys.stderr)
        if x is None:
            if not my_debug:
                print(TAG+'error: xp is None', file=sys.stderr)
            return
        if my_have_tft:
            if isinstance(self.hdg_alt_lst, list):
                le = len(self.hdg_alt_lst)
                if le == 0:
                    self.hdg_alt_lst.append("no data")
                    le = len(self.hdg_alt_lst)
                if le > 0:
                    if not my_debug:
                        print(TAG+"self.hdg_alt_lst= {}".format(self.hdg_alt_lst), file=sys.stderr)
                    # Update this to change the size of the text displayed. Must be a whole number.
                    # print(TAG, file=sys.stderr,end='')
                    
                    hdg_old = myVars.read("hdg_old")
                    alt_old = myVars.read("alt_old")
                    
                    try:
                        for _ in range(le):
                            x[_].scale = 2
                            if _ == 0:
                                hdg = round(int(self.hdg_alt_lst[_]))
                                if hdg != hdg_old:
                                    myVars.write("hdg_old", hdg)
                                    disp_hdg_alt = True
                                    x[_].text = "Hdg: " +str(hdg) + " mag"
                            if _ == 1:
                                alt = round(int(self.hdg_alt_lst[_]))
                                if alt != alt_old:
                                    myVars.write("alt_old", alt)
                                    disp_hdg_alt = True
                                    x[_].text = "Alt: " +str(alt) + " ftMSL"

                            # print('{} '.format(author_lst[_]), file=sys.stderr, end='')
                        # print('', file=sys.stderr) end='\n')
                        if disp_hdg_alt:
                            my_page_layout.show_page(page_name="XPlane")
                            # tile_grid1.hidden=False
                            print(TAG+"showing page: XPlane")
                    except Exception as e:
                        print(TAG+'Error: {}'.format(e), file=sys.stderr)
                time.sleep(2) # myVars.read("TFT_show_duration")) # in seconds
                self.my_lcd_cleanup() # empty also self.hdg_alt_lst
                print(TAG+"showing page: main")
                
    def msgs_unpack(self, packet):
        TAG= tag_adjust("dg.msgs_unpack(): ")
        msg = (0,)  # create an empty tuple
        p_bytes = [36, 36, 36, 36]
        p_unpack_strs = ['self.udp_unpack_str_3', 'self.udp_unpack_str_17', 'self.udp_unpack_str_20', 'self.udp_unpack_str_102']
        messages = []
        if packet is not None:
            if my_debug:
                print(TAG+'packet length= {} bytes'.format(len(packet)), file=sys.stderr)
                print(TAG+'unpacking packet {}\n'.format(packet), file=sys.stderr)
            for _ in range(4):
                if _ == 0:
                    #s = values_struct_3
                    s = self.udp_unpack_str_3
                elif _ == 1:
                    #s = values_struct_17
                    s = self.udp_unpack_str_17
                elif _ == 2:
                    #s = values_struct_20
                    s = self.udp_unpack_str_20 
                elif _ == 3:
                    #s = values_struct_102
                    s = self.udp_unpack_str_102
                    
                s_size = struct.calcsize(s)
                
                if my_debug:
                    print(TAG+'using unpack string: \'{}\', size= {} bytes, value= \'{}\''.format(p_unpack_strs[_], s_size, s), file=sys.stderr)

                if _ == 0:
                    i1 = 0
                    #i2 = s_size-1      # bytes   0 -  35
                elif _ == 1:
                    i1 = p_bytes[0]
                    #i2 = (2*s_size)-1  # bytes  35 -  71
                elif _ == 2:
                    i1 = p_bytes[0] + p_bytes[1] 
                    #i2 = (3*s_size)-1  # bytes  72 - 107
                elif _ == 3:
                    i1 = p_bytes[0] + p_bytes[1] + p_bytes[2] 
                    #i2 = (4*s_size)-1  # bytes 108 - 143
                
                #p0 = packet[i1:i2] 
                if my_debug:
                    print(TAG +'unpacking from offset (i1) = {}, sub-packet= {}'.format(i1, packet[i1:]), file=sys.stderr)

                try:
                    us = struct.unpack_from(s, packet, i1)
                    if my_debug:
                        print(TAG+'us= {}\n'.format(us), file=sys.stderr)
                    messages.append(us)
                except Exception as e:
                    print(TAG+'Error: {}'.format(e), file=sys.stderr)
                    raise RuntimeError
                i = 0
                
                if _ == 0:
                    """
                    self.values_struct_3 = { # udp_unpack_str01 = "iffffifff"
                    'ID':          DUMMY_STR_INT,     # DATA and a NULL
                    'vind_kias':   DUMMY_STR_FLOAT,   # FLOAT vind_kias   airspeed in knots indicated air speed
                    'vind_keas':   DUMMY_STR_FLOAT,   # FLOAT vind_keas   airspeed in knots e... air speed
                    'vtrue_ktas':  DUMMY_STR_FLOAT,   # FLOAT vtrue_ktas  true airspeed in knots
                    'vtrue_ktgs':  DUMMY_STR_FLOAT,   # FLOAT vtrue_ktgs  true ground speed in knots
                    'nothing':     DUMMY_STR_INT,     # INT filling
                    'vind_mph':    DUMMY_STR_FLOAT,   # FLOAT vind_mph    indicated airspeed in miles-per-hour
                    'vtrue_mphas': DUMMY_STR_FLOAT,   # FLOAT vtrue_mphas  true airspeed in miles-per-hour
                    'vtrue_mphgs': DUMMY_STR_FLOAT    # FLOAT vtrue_mphgs  true groundspeed in miles-per-hour
                    }
                    """
                    self.values_struct_3['ID']          = us[i]
                    self.values_struct_3['vind_kias']   = us[i+1]
                    self.values_struct_3['vind_keas']   = us[i+2]
                    self.values_struct_3['vtrue_ktas']  = us[i+3]
                    self.values_struct_3['vtrue_ktgs']  = us[i+4]
                    self.values_struct_3['nothing']     = us[i+5]
                    self.values_struct_3['vind_mph']    = us[i+6]
                    self.values_struct_3['vtrue_mphas'] = us[i+7]
                    self.values_struct_3['vtrue_mphgs'] = us[i+8]
                    
                    if my_debug:
                        #print(TAG+'self.values_struct_3.keys() = {}\n'.format(self.values_struct_3.keys()), file=sys.stderr)
                        print(TAG+'self.values_struct_3.items() = {}\n'.format(self.values_struct_3.items()), file=sys.stderr)
                    
                elif _ == 1:
                    """
                    self.values_struct_17 = { # udp_unpack_str02 = "ifffiffif"
                    'ID':         DUMMY_STR_INT,
                    'pitch_deg':  DUMMY_STR_FLOAT,
                    'roll_deg':   DUMMY_STR_FLOAT,
                    'hding_true': DUMMY_STR_FLOAT,
                    'nothing1':   DUMMY_STR_INT,                   
                    'hding_mag':  DUMMY_STR_FLOAT,
                    'mavar_deg':  DUMMY_STR_FLOAT,
                    'nothing2':   DUMMY_STR_INT,
                    'mag_comp':   DUMMY_STR_FLOAT
                    }
                    """
                    self.values_struct_17['ID']         = us[i]
                    self.values_struct_17['pitch_deg']  = us[i+1]  
                    self.values_struct_17['roll_deg']   = us[i+2]
                    self.values_struct_17['hding_true'] = us[i+3]
                    self.values_struct_17['nothing1']   = us[i+4]                
                    self.values_struct_17['hding_mag']  = us[i+5]
                    self.values_struct_17['mavar_deg']  = us[i+6]
                    self.values_struct_17['nothing2']   = us[i+7]
                    self.values_struct_17['mag_comp']   = us[i+8]

                    if my_debug:
                        #print(TAG+'self.values_struct_17.keys() = {}\n'.format(self.values_struct_17.keys()), file=sys.stderr)
                        print(TAG+'self.values_struct_17.items() = {}\n'.format(self.values_struct_17.items()), file=sys.stderr)
                    
                elif _ == 2:
                    """
                    self.values_struct_20 = { # udp_unpack_str03 = "iffffffff"
                    'ID':          DUMMY_STR_INT,
                    'lat_deg':     DUMMY_STR_FLOAT,
                    'lon_deg':     DUMMY_STR_FLOAT,
                    'CG_ftmsl':    DUMMY_STR_FLOAT,
                    'gear_ftagl':  DUMMY_STR_FLOAT,
                    'terrn_ftmsl': DUMMY_STR_FLOAT,
                    'p-alt_ftmsl': DUMMY_STR_FLOAT,
                    'lat_orign':   DUMMY_STR_FLOAT,
                    'lon_orign':   DUMMY_STR_FLOAT
                    }
                    """
                    self.values_struct_20['ID']          = us[i]
                    self.values_struct_20['lat_deg']     = us[i+1]
                    self.values_struct_20['lon_deg']     = us[i+2]
                    self.values_struct_20['CG_ftmsl']    = us[i+3]
                    self.values_struct_20['gear_ftagl']  = us[i+4]
                    self.values_struct_20['terrn_ftmsl'] = us[i+5]
                    self.values_struct_20['p-alt_ftmsl'] = us[i+6]
                    self.values_struct_20['lat_orign']   = us[i+7]
                    self.values_struct_20['lon_orign']   = us[i+8]
                    
                    if my_debug:
                        #print(TAG+'self.values_struct_20.keys() = {}\n'.format(self.values_struct_20.keys()), file=sys.stderr)
                        print(TAG+'self.values_struct_20.items() = {}\n'.format(self.values_struct_20.items()), file=sys.stderr)
                    
                elif _ == 3:
                    """
                    self.values_struct_102 = { #  "iffffffii"  on: 2019-05-01 18h23PT udp_unpack_str04 = iiiiiiiif  --> old: "<ifffiiiff"  --> old unpack string: "ifiifffif"
                    'ID':         DUMMY_STR_INT,
                    'dme_nav01':  DUMMY_STR_FLOAT, # dme of nav1
                    'dme_mode':   DUMMY_STR_FLOAT, # dme mode (1 = dme1, 2= dme2)
                    'dme_found':  DUMMY_STR_FLOAT, # dme found  1.0000
                    'dme_dist':   DUMMY_STR_FLOAT, # dme distance (nm)
                    'dme_speed':  DUMMY_STR_FLOAT, # dme speed    (kts)
                    'dme_time':   DUMMY_STR_FLOAT, # dme_time (time-to-station)
                    'dme_n-typ':  DUMMY_STR_INT,   # dme n-typ (3.0000)
                    'dme-3_freq': DUMMY_STR_INT,   # dme3 freq (this is the 3rd, dme receiver (usually not reacheable)
                    }            
                    """
                    self.values_struct_102['ID']         = us[i]
                    self.values_struct_102['dme_nav01']  = us[i+1]
                    self.values_struct_102['dme_mode']   = us[i+2]
                    self.values_struct_102['dme_found']  = us[i+3]
                    self.values_struct_102['dme_dist']   = us[i+4]
                    self.values_struct_102['dme_speed']  = us[i+5]
                    self.values_struct_102['dme_time']   = us[i+6]
                    self.values_struct_102['dme_n-typ']  = us[i+7]
                    self.values_struct_102['dme-3_freq'] = us[i+8]    
                    
                    if my_debug:
                        #print(TAG+'self.values_struct_102.keys() = {}\n'.format(self.values_struct_102.keys()), file=sys.stderr)
                        print(TAG+'self.values_struct_102.items() = {}\n'.format(self.values_struct_102.items()), file=sys.stderr)                
 
                  
            le = len(messages)
            if le > 0:
                #print(TAG+'messages = {}'.format(messages), file=sys.stderr)
                if my_debug: 
                    for _ in range(le):
                        print(TAG+'unpacked messege nr {} = \'{}\''.format(_+1, messages[_]), file=sys.stderr)
                self.hdg_alt_lst.append(self.values_struct_17['hding_mag']) # mag compass heading
                self.hdg_alt_lst.append(self.values_struct_20['CG_ftmsl']) # altitude
                if my_debug:
                    print(TAG+'self.hdg_alt_lst= {}'.format(self.hdg_alt_lst), file=sys.stderr)
        else:
            print(TAG+'unpacked messages empty')
        return messages
    # ==============================================================
    # Two functions copied from: XPlane10UdpDataOutputReceiver.py  =
    # ==============================================================

    # Function copied from Charlylima's example file: XPlane10UdpDataOutputReceiver.py
    # Modifications, additions and documentary by Paulsk
    def DecodePacket(self):
        global my_debug
        TAG= tag_adjust("dg.DecodePacket(): ")
        self.message = None
        self.messages = None
        #  self.retval = []  # Do not empty the list here. It's done in dg.__init()
        headerlen = 5
        messagelen = 36

        # Convert packet header (bytearray) to string
        header0 = self.packet[:headerlen-1]
        header = ''
        if my_debug:
            print(TAG+'packet tail0 = \'{}\''.format(tail0), file=sys.stderr)
            
        for _ in range(len(header0)):
            header += chr(header0[_])

        if my_debug:
            print(TAG+'Going to decode packet with header \'{}\''.format(header), file=sys.stderr)

        # Packet consists of 4 byte ASCII string header, 1 byte pad character and 9 items of each 4 bytes (=36 bytes) messages.
        # copy message part of the parameter variable to self.packet (skip the first comma delimiter)
        tail0 = self.packet[headerlen:]
        if my_debug:
            print(TAG+'going to unpack packet {}'.format(tail0), file=sys.stderr)
        self.messages = self.msgs_unpack(tail0)
        if my_debug:
            print(TAG+'unpacked messages= {}'.format(self.messages), file=sys.stderr)

        # We have an udp datagram!
        myVars.write("xp_lst", self.messages) # save it

        self.DispMessage(header, self.messages)
        gc.collect()
        return self.messages


    def DispMessage(self, header, msg_lst):
        # global xp, xp_grp, my_page_layout
        TAG= tag_adjust("dg.DispMessage(): ")
        ln = '-'*40
        s = ''
        xp = myVars.read("xp")
        ptu = myVars.read("packet_types_used")
        loop_nr = myVars.read("main_loop_nr")

        if 'XGPS' in ptu:
            xgps_lst = ['LON', 'LAT', 'ALT', 'HDG',  'GS']
            xgps_lst_2 = ['',  '',    'm',   'true', 'm/s']

        if 'XATT' in ptu:
            xatt_lst =   ['HDG', 'PITCH', 'ROLL', 'Roll-rate','Pitch-rate', 'Yaw-rate', 'SPD_TRUE_EAST', 'SPD_TRUE_UP', 'SPD_TRUE_SOUTH', 'G-Load side', 'G-Load normal', 'G-Load axial']
            xatt_lst_2 = ['true', 'degs', 'degs', 'rad/s',    'rad/s',      'rad/s',    'm/s',           'm/s',          'm/s',           'G',           'G',             'G',]

        if 'XTRA' in ptu:
            xtra_lst   = ['LAT', 'LON', 'ALT', 'V/S',    'ON_GND',     'HDG',  'GS',  'TAIL NR']
            xtra_lst_2 = ['',    '',    'ft',  'ft/min', 'True/False', 'true', 'kts', '']

        le = len(msg_lst)

        # print(TAG+'header= {}'.format(header), file=sys.stderr)

        if le == 0:
            print(TAG+'param msg_lst is empty. Exiting...', file=sys.stderr)
        else:
            if my_debug:
                print(TAG+'header= \'{}\'. Contents msg_lst= {}'.format(header, msg_lst), file=sys.stderr)
            #print(TAG+'hasattr(xp[0],"text")= {}'.format(hasattr(xp[0],"text")), file=sys.stderr)
            if my_debug:
                print(TAG+'Packet types used= {}'.format(ptu), file=sys.stderr)

            if header in ptu:
                #print(TAG, file=sys.stderr)
                if not my_debug:
                    print(TAG+'Loop nr: {:03d}'.format(loop_nr), file=sys.stderr)
                print(ln, file=sys.stderr)
                print('\tPACKET TYPE: {}'.format(header), file=sys.stderr)
                print(ln, file=sys.stderr)
                try:
                    for _ in range(le):
                            if my_debug:
                                print(TAG+'first loop: index= {}'.format(_), file=sys.stderr)
                            if header == 'XGPS':
                                s = '\t{:14s} {:8.4f} {:s}'.format(xgps_lst[_], float(msg_lst[_]), xgps_lst_2[_])
                            elif header == 'XATT':
                                s = '\t{:14s} {:8.4f} {:s}'.format(xatt_lst[_], float(msg_lst[_]), xatt_lst_2[_])
                            elif header == 'XTRA':
                                s = '\t{:14s} {:8.4f} {:s}'.format(xtra_lst[_], float(msg_lst[_]), xtra_lst_2[_])
                            if len(s) > 0:
                                print(s, file=sys.stderr)
                    #if header == 'XGPS':
                    #    print(ln, file=sys.stderr)
                    print(ln, file=sys.stderr)
                except Exception as e:
                    print(TAG+'Error {}'.format(e), file=sys.stderr)
                    raise RuntimeError
                except KeyboardInterrupt:
                    myVars.write("kbd_intr", True)
                    raise
            elif header == 'DATA':
                if my_have_tft:
                    self.disp_hdg_alt()
                    return

            #print('\n', file=sys.stderr)
            #time.sleep(0.5)

            # print(TAG+'type(myVars)= {}'.format(type(myVars)), file=sys.stderr)

            # Example XATT packet received and converted to a list:
            #  msg_lst= ['-123.8', '0.6', '0.4', '0.0000', '-0.0000', '0.0000', '-64.9', '-0.6', '41.9', '-0.01', '1.00', '-0.0']

            if my_debug:
                print(TAG+'Adding {} packet elements to display:'.format(header), file=sys.stderr)
            # print(TAG+'type(xp)= {}. len(xp)= {}'.format(type(xp), len(xp)), file=sys.stderr)
            # print(TAG+'xp[0]= {}'.format(xp[0]), file=sys.stderr)

            if header in ptu:
                try:
                    for _ in range(le):
                            if my_debug:
                                print(TAG+'second loop: index= {}'.format(_), file=sys.stderr)
                            #xp[_].scale = 2
                            if header == 'XGPS':
                                s = '{} {} {}'.format(xgps_lst[_], msg_lst[_], xgps_lst_2[_])
                            elif header == 'XATT':
                                s = '{} {} {}'.format(xatt_lst[_], msg_lst[_], xatt_lst_2[_])
                            elif header == 'XTRA':
                                s = '{} {} {}'.format(xtra_lst[_], msg_lst[_], xtra_lst_2[_])

                    if header == 'XGPS':
                        hdg = round(float(msg_lst[3])) # round the heading value
                        if my_debug:
                            print(TAG+'hdg= {}'.format(hdg), file=sys.stderr)
                        s = '{} {} {}'.format(xgps_lst[3], hdg, xgps_lst_2[3])
                        if my_debug:
                            print(TAG+'Adding {} element {}'.format(header, s), file=sys.stderr)
                        xp[0].scale=2
                        xp[0].text = 'X-Plane ' + myVars.read('xplane_version')
                        xp[1].scale=3
                        xp[1].text = header
                        xp[2].scale=3
                        xp[2].text = s
                        #print(TAG+'type(my_page_layout)= {}'.format(type(my_page_layout)), file=sys.stderr)
                        myVars.write("xp", xp)

                        my_page_layout.show_page(page_name="XPlane")
                        blink_NEO_color(neo_led_green) # blink the Neopixel led in green (see: common.py)
                        time.sleep(myVars.read("TFT_show_duration")) # in seconds

                except KeyboardInterrupt:
                    myVars.write("kbd_intr", True)
                except Exception as e:
                    print(TAG+'Error {}'.format(e), file=sys.stderr)
                    raise RuntimeError

    # Function by Paulsk
    def my_lcd_cleanup(self):
        global my_have_lcd, my_have_tft, my_debug, lcd, Hasseb_lcd, Loose_lcd, LCD_DISPLAYCONTROL

        if my_debug:
            print('We entered function my_lcd_cleanup()', file=sys.stderr)

        if my_have_lcd:
            if Hasseb_lcd:
                #global LCD_DISPLAYOFF
                lcd.cursor_mode = LCD_CURSOROFF | LCD_BLINKOFF  # was: curm.hide
                lcd.display_enabled = LCD_DISPLAYOFF
                lcd.home()
                lcd.clear()
                lcd.close()
            elif Loose_lcd:
                #lcd.lcd_write(LCD_DISPLAYCONTROL | LCD_DISPLAYOFF)
                lcd.lcd_write(LCD_DISPLAYCONTROL | LCD_CURSOROFF)
                lcd.lcd_clear()
                if my_debug:
                    print >>sys.stderr,'This is my_lcd_cleanup() - going to switch off the LCD backlight\n'
                lcd.lcd_goblack() # switch off the backlight
        if my_have_tft:
            my_page_layout.show_page(page_name="XPlane")
            self.hdg_alt_lst = [] 
        return

    def usage(self):
        print('\nUsage : "python XPlaneUdpDatagramLCD.py [<IP Multicast Group>] [,<Multicast Port>]', file=sys.stderr)
        print('\t--group or -g <IP Multicast Group>       e.g. {}'.format("235.255.1.1"), file=sys.stderr)
        print('\t--port  or -p <Multicast Port>           e.g. {}'.format("49707"), file=sys.stderr)
        print('\t--dme   or -d Display DME3 frequency         ', file=sys.stderr)
        print('\t--groundspeed or -gs display the groundspeed ', file=sys.stderr)
        print('\t--help  or -h this help text\n', file=sys.stderr)

