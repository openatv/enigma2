# -*- coding: ISO-8859-1 -*-
# python-wifi -- a wireless library to access wireless cards via python
# Copyright (C) 2004, 2005, 2006 Róman Joost
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public License
#    as published by the Free Software Foundation; either version 2.1 of
#    the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful, but
#    WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
#    USA 

modes = ['Auto', 
         'Ad-Hoc',
         'Managed',
         'Master', 
         'Repeat',
         'Second',
         'Monitor']

IFNAMSIZE = 16
IW_ESSID_MAX_SIZE = 16

KILO = 10**3
MEGA = 10**6
GIGA = 10**9

# ioctl calls for the Linux/i386 kernel
SIOCIWFIRST   = 0x8B00    # FIRST ioctl identifier
SIOCGIFCONF   = 0x8912    # ifconf struct
SIOCGIWNAME   = 0x8B01    # get name == wireless protocol
SIOCGIWFREQ   = 0x8B05    # get channel/frequency
SIOCSIWMODE   = 0x8B06    # set the operation mode
SIOCGIWMODE   = 0x8B07    # get operation mode
SIOCGIWSENS   = 0x8B09    # get sensitivity
SIOCGIWAP     = 0x8B15    # get AP MAC address
SIOCSIWSCAN   = 0x8B18    # set scanning off
SIOCGIWSCAN   = 0x8B19    # get scanning results
SIOCGIWRATE   = 0x8B21    # get default bit rate
SIOCGIWRTS    = 0x8B23    # get rts/cts threshold
SIOCGIWFRAG   = 0x8B25    # get fragmention thrh
SIOCGIWTXPOW  = 0x8B27    # get transmit power (dBm)
SIOCGIWRETRY  = 0x8B29    # get retry limit
SIOCGIWRANGE  = 0x8B0B    # range
SIOCGIWSTATS  = 0x8B0F    # get wireless statistics
SIOCSIWESSID  = 0x8B1A    # set essid
SIOCGIWESSID  = 0x8B1B    # get essid
SIOCGIWPOWER  = 0x8B2D    # get power managment settings
SIOCGIWENCODE = 0x8B2B    # get encryption information
SIOCIWLAST    = 0x8BFF    # LAST ioctl identifier

# Power management flags
IW_POWER_ON = 0x0000        # No details ...
IW_POWER_TYPE = 0xF000      # Type of parameter
IW_POWER_PERIOD = 0x1000    # Value is a period/duration of
IW_POWER_TIMEOUT = 0x2000   # Value is a timeout
IW_POWER_MODE = 0x0F00      # Power management mode
IW_POWER_MIN = 0x0001       # Value is a minimum
IW_POWER_MAX = 0x0002       # Value is a maximum
IW_POWER_RELATIVE = 0x0004  # Value is not in seconds/ms/us

# Retry limits 
IW_RETRY_TYPE = 0xF000      # Type of parameter

# encoding stuff
IW_ENCODE_DISABLED = 0x8000     # encoding is disabled
IW_ENCODE_NOKEY = 0x0800      # key is write only, not present

# constants responsible for scanning
IW_SCAN_MAX_DATA = 4096

IW_EV_LCP_LEN = 4
IW_EV_CHAR_LEN = IW_EV_LCP_LEN + IFNAMSIZE
IW_EV_UINT_LEN = IW_EV_LCP_LEN + 4
IW_EV_FREQ_LEN = IW_EV_LCP_LEN + 8
IW_EV_ADDR_LEN = IW_EV_LCP_LEN + 16
IW_EV_POINT_LEN = IW_EV_LCP_LEN + 4
IW_EV_PARAM_LEN = IW_EV_LCP_LEN + 8
IW_EV_QUAL_LEN = IW_EV_LCP_LEN + 4

EPERM = 1
E2BIG = 7
EAGAIN = 11

IWHT_NULL = 0
IWHT_CHAR = 2
IWHT_UINT = 4
IWHT_FREQ = 5
IWHT_ADDR = 6
IWHT_POINT = 8
IWHT_PARAM = 9
IWHT_QUAL = 10

IWEVFIRST     = 0x8C00    # FIRST event identifier
IWEVQUAL      = 0x8C01    # Quality statistics from scan
IWEVCUSTOM    = 0x8C02    # Custom Ascii string from Driver
IWEVLAST      = 0x8C0A    # LAST event identifier
