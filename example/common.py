# _*_ coding: utf-8 _*_
# SPDX-FileCopyrightText: 2023 Paulus Schulinck
#
# SPDX-License-Identifier: MIT
##############################
# This file contains common global variables for:
# Files:
# - code.py
# - XPlaneUdpDatagram.py
# - XPlaneDatarefRx.py
#
# Original see: I:\Raspberry_Pi\XPlane_datarefs\xp_data_outp_rx\XPlaneUdpDatagramLCDv11.py
# For the LCD 4x20 (e.g. used in the Hasseb.fi CMIO device) see file:
# I:\Raspberry_Pi\08th Raspberry pi - CM IO Hasseb FI\Files downloaded fm website Hassab\Sample_programs\RPLCD-master\RPLCD\lcd.py
#type:ignore
import os, sys
import time
import board
# import busio
from adafruit_displayio_layout.layouts.page_layout import PageLayout
import neopixel

id = board.board_id # 'adafruit_feather_esp32s2_tft'

print("\nThis script is running on an \'{}\'".format(id), file=sys.stderr)

TX = board.TX
RX = board.RX
uart = None
#uart = busio.UART(TX, RX, baudrate=4800, timeout=0, receiver_buffer_size=151)  # board.RX, board.TX)

# built-in display
display = board.DISPLAY

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)

# Define which type of LCD is connected:
# a) the Hitachi LCD 4x20 in the enclosure with the custom made Raspberry Pi CMIO and the CM3 connected;
Hasseb_lcd = False
# b) the loose Hitachi LCD 4x20 with only 4 lines connected to the Raspberry Pi: Vcc, GND, SDA to GPIO Pin 3 and SCL to GPIO Pin 5.
# The value of the flag Loose_lcd is alway the contrary of the value of Hasseb_lcd
Loose_lcd = False

# Important flag definitions:

my_have_tft = True
my_have_lcd = False # no, we're using an Adafruit Feather ESP32 S2 TFT display  (and not a raspberry pi (cmio + cm3) that has an 4x20 LCD builtin)
my_debug = False #  Debug / Printing flag
my_DoCheckCPUTemp = False # Flag to determine if we have to monitor the CPU temperature

use_getopt = True
my_debug = False
use_wifi = True
use_ping = True
use_tmp_sensor = False
use_logo = True
use_avatar = True

if use_wifi:
    #from secrets import secrets
    #ssid = secrets["ssid"]
    #password = secrets["password"]

    # Next 2 lines. See file 'settings.toml'
    ssid = os.getenv('CIRCUITPY_WIFI_SSID')
    password = os.getenv('CIRCUITPY_WIFI_PASSWORD')
else:
    ssid = None
    password = None

tag_width = 25

page_dict = {
    0: 'Logo1',
    1: 'Logo2',
    2: 'Battery',
    3: 'ID',
    4: 'Datetime',
    5: 'Author',
    6: 'XPlane',
}

if my_have_lcd:
    #  Flags for display on/off control (COPIED FROM Hasseb.fi, file: lcd.py)
    LCD_DISPLAYON = 0x04
    LCD_DISPLAYOFF = 0x00
    LCD_CURSORON = 0x02
    LCD_CURSOROFF = 0x00
    LCD_BLINKON = 0x01
    LCD_BLINKOFF = 0x00
    LCD_DISPLAYCONTROL = 0x08
    LCD_ENTRYSHIFTDECREMENT = 0x00 # = cursor shift
    LCD_ENTRYSHIFTINCREMENT = 0x01 # = display shift

# create the page layout
my_page_layout = PageLayout(x=0, y=0)

def tag_adjust(s):
    global tag_width
    le = len(s)
    if my_debug:
        print("tag_adjust(): param s= \'{}\', len(s)= {}, global tag_width= {}".format(s, le, tag_width), file=sys.stderr)
    if le >= tag_width:
        s2 = s[:tag_width]
    else:
        s2 = (s + ' '*(tag_width-le))
    # print("tag_adjust: returning \'{}\'".format(s2), file=sys.stderr)
    return s2

TAG= tag_adjust("common.global: ")

if use_wifi:
    try:
        if wifi is None:
            import wifi
    except NameError: # this error occurrs when 'wifi' is not defined
        import wifi # so we going to try to import wifi
        if my_debug:
            print(TAG+'type(wifi)= {}'.format(type(wifi)), file=sys.stderr)

    try:
        if pool is None:
            import socketpool
    except NameError:
        import socketpool

    pool = socketpool.SocketPool(wifi.radio)
    if my_debug:
        print(TAG+'type(pool)= {}'.format(type(pool)), file=sys.stderr)


dg = None

dr = None

udp_packet_types = {
    0: b"BECN",
    1: b"DATA",
    2: b"XATT",
    3: b"XGPS",
    4: b'XTRA'}

udp_packet_types_rev = {
    b"BECN" : 0,
    b"DATA": 1,
    b"XATT": 2,
    b"XGPS": 3,
    b'XTRA': 4}

SCRIPT_NAME = ''
XPlane_version = "X-Plane 12"
ADAFRUIT_IO_USERNAME = None
ADAFRUIT_IO_KEY = None
pool = None
requests = None
tt = None
ip = None
s_ip = None
location = None
tz_offset = None
TIME_URL = None
rtc = None
tmp117 = None
blink_cycles = 2
temp_update_cnt = 0
old_temp = 0.00
temp_sensor_present = None
degs_sign = '' # chr(186)  # I preferred the real degrees sign which is: chr(176)
main_group = None
logo1_grp = None
logo2_grp = None
ba_grp = None
dt_grp = None
ta1_grp = None
ta2_grp = None
te_grp = None
xp_grp = None
tmp117 = None
author_lst = None
# hdg_alt_lst = None
t0 = None
t1 = None
t2 = None
dt = None
ba = None
ta1 = None
ta2 = None
te = None
xp = None

neo_brill = 50
neo_led_red = 1
neo_led_green = 2
neo_led_blue = 3
neo_black = (0, 0, 0)
neo_red = (neo_brill, 0, 0)
neo_green = (0, neo_brill, 0)
neo_blue = (0, 0, neo_brill)

tile_grid0 = None
tile_grid1 = None
tile_grid2 = None

weekdays = {0:"Monday", 1:"Tuesday",2:"Wednesday",3:"Thursday",4:"Friday",5:"Saturday",6:"Sunday"}

# release any currently configured displays
#displayio.release_displays()
start_t= time.monotonic()
start_0 = start_t # remember (and don't change this value!!!)
time_received = False

lcd = None

# unichr used to print a degrees sign from the Hitachi LCD ROM A00. See: class RaspiCheckCPUTemp()
try:
    unichr = unichr
except NameError:  # Python 3
    unichr = chr

def get_page_name(page_index):
    le = len(page_dict)
    # print("get_page_number(): param page_index = {}".format(page_index), file=sys.stderr)
    if page_index >= 0 and page_index < le:
        if page_index in page_dict.keys():
            return page_dict[page_index]
    return ''

def make_pool():
    global pool
    TAG= tag_adjust("common.make_pool(): ")
    try:
        if pool is None:
            import socketpool
    except NameError:
        import socketpool

    pool = socketpool.SocketPool(wifi.radio)
    if not my_debug:
        print(TAG+'type(pool)= {}'.format(type(pool)), file=sys.stderr)

    return pool

def blink_NEO_color(color):

    pixel.brightness = 0.3

    if color is None:
        for _ in range(blink_cycles):
            pixel.fill(neo_red)
            time.sleep(0.5)
            pixel.fill(neo_green)
            time.sleep(0.5)
            pixel.fill(neo_blue)
            time.sleep(0.5)
        pixel.fill((0, 0, 0))
    else:
        if color == neo_led_red:
            c = neo_led_red # red
        elif color == neo_led_green:
            c = neo_green  # green
        elif color == neo_led_blue:
            c = neo_blue  # blue
        else:
            print('blink_NEO_color(): color undefine. Got {}'.format(color), file=sys.stderr)
            return

        if color > 0:
            # blink in the chosen color
            for _ in range(blink_cycles):
                pixel.fill(c)
                time.sleep(0.5)
                pixel.fill(neo_black)
                time.sleep(0.5)

# +-------------------------------------------------------+
# | Definition for variables in the past defined as global|
# +-------------------------------------------------------+
# The gVars class is created
# to elminate the need for global variables.


class gVars:
    def __init__(self):

        self.gVarsDict = {
            0: "my_debug",
            1: "rtc",
            2: "disp_width",
            3: "disp_height",
            4: "xp",
            5: "xp_lst",
            6: "TFT_show_duration",
            7: "kbd_intr",
            8: "use_udp_host",
            9: "multicast_group1",
            10:"multicast_group2",
            11:"multicast_port1",
            12:"multicast_port2",
            13:"packet_types_used",
            14: "xplane_version",
            15: "main_loop_nr",
            16: "hdg_old",
            17: "alt_old"
        }

        self.gVars_rDict = {
            "my_debug": 0,
            "rtc": 1,
            "disp_width": 2,
            "disp_height":3,
            "xp": 4,
            "xp_lst": 5,
            "TFT_show_duration": 6,
            "kbd_intr": 7,
            "use_udp_host": 8,
            "multicast_group1": 9,
            "multicast_group2": 10,
            "multicast_port1": 11,
            "multicast_port2": 12,
            "packet_types_used": 13,
            "xplane_version": 14,
            "main_loop_nr": 15,
            "hdg_old": 16,
            "alt_old": 17
        }

        self.g_vars = {}

        # self.clean()

    def write(self, s, value):
        if isinstance(s, str):
            if s in self.gVars_rDict:
                n = self.gVars_rDict[s]
                if my_debug:
                    print("myVars.write() \'{:" ">20s}\' found in self.gVars_rDict, key: {}".format(s, n), file=sys.stderr)
                self.g_vars[n] = value
            else:
                raise KeyError(
                    "variable '{:" ">20s}' not found in self.gVars_rDict".format(s)
                )
        else:
            raise TypeError(
                "myVars.write(): param s expected str, {} received".format(type(s))
            )

    def read(self, s):
        RetVal = None
        if isinstance(s, str):
            if s in self.gVars_rDict:
                n = self.gVars_rDict[s]
                if n in self.g_vars:
                    RetVal = self.g_vars[n]
        return RetVal

    def clean(self):
        self.g_vars = {
            0: None,
            1: None,
            2: None,
            3: None,
            4: None,
            5: None,
            6: None,
            7: None,
            8: None,
            9: None,
            10: None,
            11: None,
            12: None,
            13: None,
            14: None,
            15: None,
            16: None,
            17: None
    }

    def list(self):
        for i in range(0, len(self.g_vars) - 1):
            print(
                "self.g_vars['{:"
                ">20s}'] = {}".format(
                    self.gVarsDict[i], self.g_vars[i] if i in self.g_vars else "None"
                )
            )


# ---------- End of class gVars ------------------------

myVars = gVars()  # create an instance of the gVars class


# -------------- Setting myVars elements ----------------------------------
myVars.write("my_debug", False)
myVars.write("rtc", None)
myVars.write("disp_width", display.width)
myVars.write("disp_height", display.height)
myVars.write("xp", None)
myVars.write("xp_lst", None)
myVars.write("TFT_show_duration", 5)
myVars.write("kbd_intr", False)
myVars.write("use_udp_host", os.getenv("USE_UDP_HOST"))
myVars.write("multicast_group1", os.getenv("MULTICAST_GROUP1"))
myVars.write("multicast_group2", os.getenv("MULTICAST_GROUP2"))
myVars.write("multicast_port1", int(os.getenv("MULTICAST_PORT1")))
myVars.write("multicast_port2", int(os.getenv("MULTICAST_PORT2")))
# myVars.write("packet_types_used", ['XGPS']) # or ['XGPS', 'XATT', 'XTRA']
myVars.write("packet_types_used", os.getenv("PACKET_TYPES_USED"))
myVars.write("xplane_version", os.getenv("XPLANE_VERSION"))
myVars.write("main_loop_nr", 0)
myVars.write("hdg_old",0)
myVars.write("alt_old",0)
