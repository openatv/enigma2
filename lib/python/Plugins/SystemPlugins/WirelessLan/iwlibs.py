# -*- coding: ISO-8859-1 -*-
# python-wifi -- a wireless library to access wireless cards via python
# Copyright (C) 2004, 2005, 2006 Róman Joost
# 
# Contributions from:
#   Mike Auty <m.auty@softhome.net> (Iwscanresult, Iwscan)
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

from struct import pack as struct_pack, \
	unpack as struct_unpack, \
	calcsize as struct_calcsize

from array import array
from math import ceil, log10
from fcntl import ioctl
from socket import AF_INET, SOCK_DGRAM, socket
from time import sleep
from re import compile

from flags import *    

def getNICnames():
    """ extract wireless device names of /proc/net/wireless 
        
        returns empty list if no devices are present

        >>> getNICnames()
        ['eth1', 'wifi0']
    """
    device = compile('[a-z]+[0-9]+')
    ifnames = []
    
    f = open('/proc/net/wireless', 'r')
    data = f.readlines()
    for line in data:
        try:
            ifnames.append(device.search(line).group())
        except AttributeError:
            pass 
    # if we couldn't lookup the devices, try to ask the kernel
    if ifnames == []:
        ifnames = getConfiguredNICnames()
    
    return ifnames

def getConfiguredNICnames():
    """get the *configured* ifnames by a systemcall
       
       >>> getConfiguredNICnames()
       []
    """
    iwstruct = Iwstruct()
    ifnames = []
    buff = array('c', '\0'*1024)
    caddr_t, length = buff.buffer_info()
    s = iwstruct.pack('iP', length, caddr_t)
    try:
        result = iwstruct._fcntl(SIOCGIFCONF, s)
    except IOError, (i, e):
        return i, e
   
    # get the interface names out of the buffer
    for i in range(0, 1024, 32):
        ifname = buff.tostring()[i:i+32]
        ifname = struct_unpack('32s', ifname)[0]
        ifname = ifname.split('\0', 1)[0]
        if ifname:
            # verify if ifnames are really wifi devices
            wifi = Wireless(ifname)
            result = wifi.getAPaddr()
            if result[0] == 0:
                ifnames.append(ifname)

    return ifnames  

def makedict(**kwargs):
    return kwargs


class Wireless(object):
    """Access to wireless interfaces"""
    
    def __init__(self, ifname):
        self.sockfd = socket(AF_INET, SOCK_DGRAM)
        self.ifname = ifname
        self.iwstruct = Iwstruct()
    
    def getAPaddr(self):
        """ returns accesspoint mac address 
        
            >>> from iwlibs import Wireless, getNICnames
            >>> ifnames = getNICnames()
            >>> ifnames
            ['eth1', 'wifi0']
            >>> wifi = Wireless(ifnames[0])
            >>> wifi.getAPaddr()
            '00:0D:88:8E:4E:93'

            Test with non-wifi card:
            >>> wifi = Wireless('eth0')
            >>> wifi.getAPaddr()
            (95, 'Operation not supported')

            Test with non-existant card:
            >>> wifi = Wireless('eth2')
            >>> wifi.getAPaddr()
            (19, 'No such device')
        """
        buff, s = self.iwstruct.pack_wrq(32)
        i, result = self.iwstruct.iw_get_ext(self.ifname, 
                                             SIOCGIWAP,
                                             data=s)
        if i > 0:
            return result

        return self.iwstruct.getMAC(result)
   
    def getBitrate(self):
        """returns device currently set bit rate 
        
            >>> from iwlibs import Wireless
            >>> wifi = Wireless('eth1')
            >>> wifi.getBitrate()
            '11 Mb/s'
        """
        i, result = self.iwstruct.iw_get_ext(self.ifname, 
                                            SIOCGIWRATE)
        if i > 0:
            return result
        iwfreq = Iwfreq(result)
        return iwfreq.getBitrate()
    
    def getBitrates(self):
        """returns the number of available bitrates for the device
           
            >>> from iwlibs import Wireless
            >>> wifi = Wireless('eth1')
            >>> num, rates = wifi.getBitrates()
            >>> num == len(rates)
            True
        """
        range = Iwrange(self.ifname)
        if range.errorflag:
            return (range.errorflag, range.error)
        return (range.num_bitrates, range.bitrates)

    def getChannelInfo(self):
        """returns the number of channels and available frequency for
           the device

            >>> from iwlibs import Wireless
            >>> wifi = Wireless('eth1')
            >>> num, rates = wifi.getChannelInfo()
            >>> num == len(rates)
            True
            """
        range = Iwrange(self.ifname)
        if range.errorflag:
            return (range.errorflag, range.error)
        return (range.num_channels, range.frequencies)

    def getEssid(self):
        """get essid information
            
            >>> from iwlibs import Wireless
            >>> wifi = Wireless('eth1')
            >>> wifi.getEssid()
            'romanofski'
        """
        essid = ""
        buff, s = self.iwstruct.pack_wrq(32)
        i, result = self.iwstruct.iw_get_ext(self.ifname, 
                                             SIOCGIWESSID, 
                                             data=s)
        if i > 0:
            return result
        str = buff.tostring()
        return str.strip('\x00')

    def setEssid(self, essid):
        """set essid """
        raise NotImplementedError
        if len(essid) > IW_ESSID_MAX_SIZE:
            return "essid to big"
        buff, s = self.iwstruct.pack_test(essid, 32)
        i, result = self.iwstruct.iw_get_ext(self.ifname, 
                                             SIOCSIWESSID, 
                                             data=s)
        if i > 0:
            return result

    def getEncryption(self):
        """get encryption information which is probably a string of '*',
        'open', 'private'
            
            as a normal user, you will get a 'Operation not permitted'
            error:
        
            >>> from iwlibs import Wireless
            >>> wifi = Wireless('eth1')
            >>> wifi.getEncryption()
            (1, 'Operation not permitted')
        """
        iwpoint = Iwpoint(self.ifname)
        if iwpoint.errorflag:
            return (iwpoint.errorflag, iwpoint.error)
        return iwpoint.getEncryptionKey()

    def getFragmentation(self):
        """returns fragmentation threshold 
           
           It depends on what the driver says. If you have fragmentation
           threshold turned on, you'll get an int. If it's turned of
           you'll get a string: 'off'.
            >>> from iwlibs import Wireless
            >>> wifi = Wireless('eth1')
            >>> wifi.getFragmentation()
            'off'
        """
        iwparam = Iwparam(self.ifname, SIOCGIWFRAG)
        if iwparam.errorflag:
            return (iwparam.errorflag, iwparam.error)
        return iwparam.getValue()
        
    def getFrequency(self):
        """returns currently set frequency of the card 
            
            >>> from iwlibs import Wireless
            >>> wifi = Wireless('eth1')
            >>> wifi.getFrequency()
            '2.417GHz' 
        """
        i, r = self.iwstruct.iw_get_ext(self.ifname, 
                                        SIOCGIWFREQ)
        if i > 0:
            return (i, r)
        iwfreq = Iwfreq(r)
        return iwfreq.getFrequency()
    
        
    def getMode(self):
        """returns currently set operation mode 
            
            >>> from iwlibs import Wireless
            >>> wifi = Wireless('eth1')
            >>> wifi.getMode()
            'Managed' 
        """
        i, result = self.iwstruct.iw_get_ext(self.ifname, 
                                             SIOCGIWMODE)
        if i > 0:
            return result
        mode = self.iwstruct.unpack('i', result[:4])[0]
        return modes[mode]

    def setMode(self, mode):
        """sets the operation mode """
        try:
            this_modes = [x.lower() for x in modes]
            mode = mode.lower()
            wifimode = this_modes.index(mode)
        except ValueError:
            return "Invalid operation mode!"
        
        s = self.iwstruct.pack('I', wifimode)
        i, result = self.iwstruct.iw_get_ext(self.ifname, 
                                             SIOCSIWMODE, 
                                             data=s)
        if i > 0:
            return result
    
    def getWirelessName(self):
        """ returns wireless name 
            
            >>> from iwlibs import Wireless
            >>> wifi = Wireless('eth1')
            >>> wifi.getWirelessName()
            'IEEE 802.11-DS'
        """
        i, result = self.iwstruct.iw_get_ext(self.ifname, 
                                             SIOCGIWNAME)
        if i > 0:
            return result
        return result.split('\0')[0]
    
    def getPowermanagement(self):
        """returns power management settings 
            
            >>> from iwlibs import Wireless
            >>> wifi = Wireless('eth1')
            >>> wifi.getPowermanagement()
            'off'
        """
        iwparam = Iwparam(self.ifname, SIOCGIWPOWER)
        if iwparam.errorflag:
            return (iwparam.errorflag, iwparam.error)
        return iwparam.getValue()

    
    def getRetrylimit(self):
        """returns limit retry/lifetime

            man iwconfig:
            Most cards have MAC retransmissions, and some  allow  to set
            the behaviour of the retry mechanism.
                     
            >>> from iwlibs import Wireless
            >>> wifi = Wireless('eth1')
            >>> wifi.getRetrylimit()
            16
        """
        iwparam = Iwparam(self.ifname, SIOCGIWRETRY)
        if iwparam.errorflag:
            return (iwparam.errorflag, iwparam.error)
        return iwparam.getValue()
    
    def getRTS(self):
        """returns rts threshold 
            
            returns int, 'auto', 'fixed', 'off'
        
            man iwconfig:
            RTS/CTS adds a handshake before each packet transmission to
            make sure that the channel is clear. This adds overhead, but
            increases performance in case of hidden  nodes or  a large
            number of active nodes. This parameter sets the size of the
            smallest packet for which the node sends RTS;  a value equal
            to the maximum packet size disable the mechanism. 
            
            >>> from iwlibs import Wireless
            >>> wifi = Wireless('eth1')
            >>> wifi.getRTS()
            'off'
        """
        iwparam = Iwparam(self.ifname, SIOCGIWRTS)
        if iwparam.errorflag:
            return (iwparam.errorflag, iwparam.error)
        return iwparam.getValue()
    
    def getSensitivity(self):
        """returns sensitivity information 
        
            man iwconfig:
            This is the lowest signal level for which the hardware
            attempt  packet  reception, signals  weaker  than  this are
            ignored. This is used to avoid receiving background noise,
            so you should  set  it according  to  the  average noise
            level. Positive values are assumed to be the raw value used
            by the hardware  or a percentage, negative values are
            assumed to be dBm.
        
            >>> from iwlibs import Wireless
            >>> wifi = Wireless('eth1')
            >>> wifi.getSensitivity()
            'off'
            
        """
        iwparam = Iwparam(self.ifname, SIOCGIWSENS)
        if iwparam.errorflag:
            return (iwparam.errorflag, iwparam.error)
        return iwparam.getValue()
        
    def getTXPower(self):
        """returns transmit power in dBm 
        
            >>> from iwlibs import Wireless
            >>> wifi = Wireless('eth1')
            >>> wifi.getTXPower()
            '17 dBm'
        """
        i, r = self.iwstruct.iw_get_ext(self.ifname, 
                                        SIOCGIWTXPOW)
        if i > 0:
            return (i, r)
        iwfreq = Iwfreq(r)
        return iwfreq.getTransmitPower()
         
    def getStatistics(self):
        """returns statistics information which can also be found in
           /proc/net/wireless 
        """
        iwstats = Iwstats(self.ifname)
        if iwstats.errorflag > 0:
            return (iwstats.errorflag, iwstats.error)
        return [iwstats.status, iwstats.qual, iwstats.discard,
            iwstats.missed_beacon]

    def scan(self):
        """returns Iwscanresult objects, after a successful scan"""
        iwscan = Iwscan(self.ifname)
        return iwscan.scan()


class Iwstruct(object):
    """basic class to handle iwstruct data """
    
    def __init__(self):
        self.idx = 0
        self.sockfd = socket(AF_INET, SOCK_DGRAM)

    def parse_data(self, fmt, data):
        """ unpacks raw C data """
        size = struct_calcsize(fmt)
        idx = self.idx

        str = data[idx:idx + size]
        self.idx = idx+size
        value = struct_unpack(fmt, str)

        # take care of a tuple like (int, )
        if len(value) == 1:
            return value[0]
        else:
            return value
    
    def pack(self, fmt, *args):
        """ calls struct_pack and returns the result """
        return struct_pack(fmt, *args)

    def pack_wrq(self, buffsize):
        """ packs wireless request data for sending it to the kernel """
        # Prepare a buffer
        # We need the address of our buffer and the size for it. The
        # ioctl itself looks for the pointer to the address in our
        # memory and the size of it.
        # Dont change the order how the structure is packed!!!
        buff = array('c', '\0'*buffsize)
        caddr_t, length = buff.buffer_info()
        s = struct_pack('Pi', caddr_t, length)
        return buff, s
    
    def pack_test(self, string, buffsize):
        """ packs wireless request data for sending it to the kernel """
        buffsize = buffsize - len(string)
        buff = array('c', string+'\0'*buffsize)
        caddr_t, length = buff.buffer_info()
        s = struct_pack('Pii', caddr_t, length, 1)
        return buff, s

    def unpack(self, fmt, packed_data):
        """ unpacks data with given format """
        return struct_unpack(fmt, packed_data)

    def _fcntl(self, request, args):
        return ioctl(self.sockfd.fileno(), request, args)
    
    def iw_get_ext(self, ifname, request, data=None):
        """ read information from ifname """
        # put some additional data behind the interface name
        if data is not None:
            buff = IFNAMSIZE-len(ifname)
            ifreq = ifname + '\0'*buff
            ifreq = ifreq + data
        else:
            ifreq = (ifname + '\0'*32)
            
        try:
            result = self._fcntl(request, ifreq)
        except IOError, (i, e):
            return i, e
        
        return (0, result[16:])

    def getMAC(self, packed_data):
        """ extracts mac addr from packed data and returns it as str """
        mac_addr = struct_unpack('xxBBBBBB', packed_data[:8])
        return "%02X:%02X:%02X:%02X:%02X:%02X" % mac_addr

class Iwparam(object):
    """class to hold iwparam data """
    
    def __init__(self, ifname, ioctl):
        # (i) value, (b) fixed, (b) disabled, (b) flags
        self.fmt = "ibbH"
        self.value = 0
        self.fixed = 0
        self.disabled = 0
        self.flags = 0
        self.errorflag = 0
        self.error = ""
        self.ioctl = ioctl 
        self.ifname = ifname
        self.update()
    
    def getValue(self):
        """returns the value if not disabled """

        if self.disabled:
            return 'off'
        if self.flags & IW_RETRY_TYPE == 0:
            return self.getRLAttributes()
        else:
            return self.getPMAttributes()

    def getRLAttributes(self):
        """returns a string with attributes determined by self.flags
        """
        return self.value

    def getPMAttributes(self):
        """returns a string with attributes determined by self.flags
           and IW_POWER*
        """
        result = ""
        
        # Modifiers
        if self.flags & IW_POWER_MIN == 0:
            result = " min"
        if self.flags & IW_POWER_MAX == 0:
            result = " max"
            
        # Type
        if self.flags & IW_POWER_TIMEOUT == 0:
            result = " period:" 
        else:
            result = " timeout:"
        # Value with or without units
        # IW_POWER_RELATIVE - value is *not* in s/ms/us
        if self.flags & IW_POWER_RELATIVE:
            result += "%f" %(float(self.value)/MEGA)
        else:
            if self.value >= MEGA:
                result += "%fs" %(float(self.value)/MEGA)
            elif self.value >= KILO:
                result += "%fms" %(float(self.value)/KILO)
            else:
                result += "%dus" % self.value

        return result
        
    def update(self):
        iwstruct = Iwstruct()
        i, r = iwstruct.iw_get_ext(self.ifname, 
                                   self.ioctl)
        if i > 0:
            self.errorflag = i
            self.error = r
        self._parse(r)
    
    def _parse(self, data):
        """ unpacks iwparam data """
        iwstruct = Iwstruct()
        self.value, self.fixed, self.disabled, self.flags =\
            iwstruct.parse_data(self.fmt, data)
        
class Iwfreq(object):
    """ class to hold iwfreq data
        delegates to Iwstruct class
    """
    
    def __init__(self, data=None):
        self.fmt = "ihbb"
        if data is not None:
            self.frequency = self.parse(data)
        else:
            self.frequency = 0
        self.iwstruct = Iwstruct()
        
    def __getattr__(self, attr):
        return getattr(self.iwstruct, attr)

    def parse(self, data):
        """ unpacks iwparam"""
        
        size = struct_calcsize(self.fmt)
        m, e, i, pad = struct_unpack(self.fmt, data[:size])
        # XXX well, its not *the* frequency - we need a better name
        if e == 0:
            return m
        else:
            return float(m)*10**e
    
    def getFrequency(self):
        """returns Frequency (str) 
            
           data - binary data returned by systemcall (iw_get_ext())
        """
        freq = self.frequency
        
        if freq >= GIGA:
            return "%0.3fGHz" %(freq/GIGA)

        if freq >= MEGA:
            return "%0.3fMHZ" %(freq/MEGA)

        if freq >= KILO:
            return "%0.3fKHz" %(freq/KILO)
    
    def getBitrate(self):
        """ returns Bitrate in Mbit 
        
           data - binary data returned by systemcall (iw_get_ext())
        """
        bitrate = self.frequency

        if bitrate >= GIGA:
            return "%i Gb/s" %(bitrate/GIGA)

        if bitrate >= MEGA:
            return "%i Mb/s" %(bitrate/MEGA)
        
        if bitrate >= KILO:
            return "%i Kb/s" %(bitrate/KILO)

    def getTransmitPower(self):
        """ returns transmit power in dbm """
        # XXX something flaky is going on with m and e
        # eg. m = 50 and e should than be 0, because the number is stored in
        # m and don't needs to be recalculated
        return "%i dBm" %self.mw2dbm(self.frequency/10)
    
    def getChannel(self, freq):
        """returns channel information given by frequency
           
           returns None if frequency can't be converted
           freq = frequency to convert (int)
           iwrange = Iwrange object
        """
        
        try:
            freq = float(freq)
        except:
            return None
        
        lut = {}
        #13 Channels beginning at 2.412GHz and inreasing by 0,005 GHz steps
        for i in range(0,12):
            cur = float( 2.412 + ( i * 0.005 ) )
            lut[str(cur)] = i+1
        # Channel 14 need special actions ;)
        lut['2.484'] = 14
        
        
        if str(freq) in lut.keys():
                return lut[str(freq)]
        
        return None
    
          
    def mw2dbm(self, mwatt):
        """ converts mw to dbm(float) """
        return ceil(10.0 * log10(mwatt))
        
    def _setFrequency(self, list):
        """sets self.frequency by given list 
           
           currently only used by Iwrange
        """
        assert len(list) == 4
        m, e, i, pad = list
        if e == 0:
            self.frequency = m
        else:
            self.frequency = m #float(m)*10**e

class Iwstats(object):
    """ class to hold iwstat data """

    def __init__(self, ifname):
        # (2B) status, 4B iw_quality, 6i iw_discarded
        self.fmt = "2B4B6i"
        self.status = 0
        self.qual = Iwquality()
        self.discard = {}
        self.missed_beacon = 0
        self.ifname = ifname
        self.errorflag = 0
        self.error = ""
        self.update()

    def update(self):
        iwstruct = Iwstruct()
        buff, s = iwstruct.pack_wrq(32)
        i, result = iwstruct.iw_get_ext(self.ifname, 
                                        SIOCGIWSTATS, 
                                        data=s)
        if i > 0:
            self.error = result
            self.errorflag = i
        self._parse(buff.tostring())
    
    def _parse(self, data):
        """ unpacks iwstruct data """
        struct = Iwstruct()
        iwqual = Iwquality()
        iwstats_data = struct.parse_data(self.fmt, data)
        
        self.status = iwstats_data[0:2]
        self.qual.quality, self.qual.sl, self.qual.nl,\
            self.qual.flags = iwstats_data[2:6]
        nwid, code, frag, retries, flags = iwstats_data[6:11]
        self.missed_beacon = iwstats_data[11:12][0]
        self.discard = makedict(nwid=nwid, code=code,
            fragment=frag, retries=retries, misc=flags)

class Iwquality(object):
    """ class to hold iwquality data """

    def __init__(self):
        self.quality = 0
        self.sl = 0
        self.nl = 0
        self.updated = 0
        self.fmt = "4B"

    def parse(self, data):
        """ unpacks iwquality data """
        struct = Iwstruct()
        qual, sl, nl, flags = struct.parse_data(self.fmt, data)

        # compute signal and noise level
        self.signal_level = sl
        self.noise_level = nl

        # asign the other values
        self.quality = qual
        self.updated = flags

    def setValues(self, list):
        """ assigns values given by a list to our attributes """
        attributes = ["quality", "signallevel", "noise_level",
            "updated"]
        assert len(list) == 4
        
        for i in range(len(list)):
            setattr(self, attributes[i], list[i])
    
    def getSignallevel(self):
        """ returns signal level """
        return self.sl-0x100

    def setSignallevel(self, sl):
        """ sets signal level """
        self.sl = sl
    signallevel = property(getSignallevel, setSignallevel)
    
    def getNoiselevel(self):
        """ returns noise level """
        return self.nl - 0x100

    def setNoiselevel(self):
        raise NotImplementedError
        self.nl = nl
    noiselevel = property(getNoiselevel, setNoiselevel)

class Iwpoint(object):
    """ class to hold iwpoint data """

    def __init__(self, ifname):
        self.key = [0,0,0,0]
        self.fields = 0
        self.flags = 0
        # (4B) pointer to data, H length, H flags
        self.fmt = "4BHH"
        self.errorflag = 0
        self.error = ""
        self.ifname = ifname
        self.update()

    def __getattr__(self, attr):
        return getattr(self.iwstruct, attr)
    
    def update(self):
        iwstruct = Iwstruct()
        buff, s = iwstruct.pack_wrq(32)
        i, result = iwstruct.iw_get_ext(self.ifname, 
                                        SIOCGIWENCODE, 
                                        data=s)
        if i > 0:
            self.errorflag = i
            self.error = result
        self._parse(result)
        
    def getEncryptionKey(self):
        """ returns encryption key as '**' or 'off' as str """
        if self.flags & IW_ENCODE_DISABLED != 0:
            return 'off'
        elif self.flags & IW_ENCODE_NOKEY != 0:
            # a key is set, so print it
            return '**' * self.fields
    
    def _parse(self, data):
        """ unpacks iwpoint data
        """
        iwstruct = Iwstruct()
        ptr, ptr, ptr, ptr, self.fields, self.flags =\
            iwstruct.parse_data(self.fmt, data)
        self.key = [ptr, ptr, ptr, ptr]

class Iwrange(object):
    """holds iwrange struct """
    IW_MAX_FREQUENCIES = 32

    def __init__(self, ifname):
        self.fmt = "iiihb6ii4B4Bi32i2i2i2i2i3h8h2b2bhi8i2b3h2i2ihB17x"\
            + self.IW_MAX_FREQUENCIES*"ihbb"
        
        self.ifname = ifname
        self.errorflag = 0
        self.error = ""
        
        # informative stuff
        self.throughput = 0
        
        # nwid (or domain id)
        self.min_nwid = self.max_nwid = 0
        
        # frequency for backward compatibility
        self.old_num_channels = self.old_num_frequency = self.old_freq = 0
        
        # signal level threshold
        self.sensitivity = 0
        
        # link quality
        self.max_qual = Iwquality()
        self.avg_qual = Iwquality()

        # rates
        self.num_bitrates = 0
        self.bitrates = []

        # rts threshold
        self.min_rts = self.max_rts = 0

        # fragmention threshold
        self.min_frag = self.max_frag = 0

        # power managment
        self.min_pmp = self.max_pmp = 0
        self.min_pmt = self.max_pmt = 0
        self.pmp_flags = self.pmt_flags = self.pm_capa = 0

        # encoder stuff
        self.encoding_size = 0
        self.num_encoding_sizes = self.max_encoding_tokens = 0
        self.encoding_login_index = 0

        # transmit power
        self.txpower_capa = self.num_txpower = self.txpower = 0

        # wireless extension version info
        self.we_vers_compiled = self.we_vers_src = 0

        # retry limits and lifetime
        self.retry_capa = self.retry_flags = self.r_time_flags = 0
        self.min_retry = self.max_retry = 0
        self.min_r_time = self.max_r_time = 0

        # frequency
        self.num_channels = self.num_frequency = 0
        self.frequencies = []
        self.update()
    
    def update(self):
        """updates Iwrange object by a system call to the kernel 
           and updates internal attributes
        """
        iwstruct = Iwstruct()
        buff, s = iwstruct.pack_wrq(640)
        i, result = iwstruct.iw_get_ext(self.ifname, 
                                        SIOCGIWRANGE, 
                                        data=s)
        if i > 0:
            self.errorflag = i
            self.error = result
        data = buff.tostring()
        self._parse(data)
        
    def _parse(self, data):
        struct = Iwstruct()
        result = struct.parse_data(self.fmt, data)
        
        # XXX there is maybe a much more elegant way to do this
        self.throughput, self.min_nwid, self.max_nwid = result[0:3]
        self.old_num_channels, self.old_num_frequency = result[3:5]
        self.old_freq = result[5:11]
        self.sensitivity = result[11]
        self.max_qual.setValues(result[12:16])
        self.avg_qual.setValues(result[16:20])
        self.num_bitrates = result[20] # <- XXX
        raw_bitrates = result[21:53]
        for rate in raw_bitrates:
            iwfreq = Iwfreq()
            iwfreq.frequency = rate
            br = iwfreq.getBitrate()
            if br is not None:
                self.bitrates.append(br)
            
        self.min_rts, self.max_rts = result[53:55]
        self.min_frag, self.max_frag = result[55:57]
        self.min_pmp, self.max_pmp = result[57:59]
        self.min_pmt, self.max_pmt = result[59:61]
        self.pmp_flags, self.pmt_flags, self.pm_capa = result[61:64]
        self.encoding_size = result[64:72]
        self.num_encoding_sizes, self.max_encoding_tokens = result[72:74]
        self.encoding_login_index = result[74:76]
        self.txpower_capa, self.num_txpower = result[76:78]
        self.txpower = result[78:86]
        self.we_vers_compiled, self.we_vers_src = result[86:88]
        self.retry_capa, self.retry_flags, self.r_time_flags = result[88:91]
        self.min_retry, self.max_retry = result[91:93]
        self.min_r_time, self.max_r_time = result[93:95]
        self.num_channels = result[95]
        self.num_frequency = result[96]
        freq = result[97:]
        
        i = self.num_frequency
        for x in range(0, len(freq), 4):
            iwfreq = Iwfreq()
            iwfreq._setFrequency(freq[x:x+4])
            fq = iwfreq.getFrequency()
            if fq is not None:
                self.frequencies.append(fq)
            i -= 1
            if i <= 0:
                break
        
class Iwscan(object):
    """class to handle AP scanning"""
    
    def __init__(self, ifname):
        self.ifname = ifname
        self.range = Iwrange(ifname)
        self.errorflag = 0
        self.error = ""
        self.stream = None
        self.aplist = None
                
    def scan(self, fullscan=True):
        """Completes a scan for available access points,
           and returns them in Iwscanresult format
           
           fullscan: If False, data is read from a cache of the last scan
                     If True, a scan is conducted, and then the data is read
        """
        # By default everything is fine, do not wait
        result = 1
        if fullscan:
            self.setScan()
            if self.errorflag > EPERM:
                raise RuntimeError, 'setScan failure ' + str(self.errorflag) + " " + str(self.error)
                return None
            elif self.errorflag < EPERM:
                # Permission was NOT denied, therefore we must WAIT to get results
                result = 250
        
        while (result > 0):
            sleep(result/1000)
            result = self.getScan()
        
        if result < 0 or self.errorflag != 0:
            raise RuntimeError, 'getScan failure ' + str(self.errorflag) + " " + str(self.error)
        
        return self.aplist
        
        
    def setScan(self):
        """Triggers the scan, if we have permission
        """
        iwstruct = Iwstruct()
        s = iwstruct.pack('Pii', 0, 0, 0)
        i, result = iwstruct.iw_get_ext(self.ifname, 
                                        SIOCSIWSCAN,s)
        if i > 0:
            self.errorflag = i
            self.error = result
        return result
        
    def getScan(self):
        """Retreives results, stored from the most recent scan
           Returns 0 if successful, a delay if the data isn't ready yet
           or -1 if something really nasty happened
        """
        iwstruct = Iwstruct()
        i = E2BIG
        bufflen = IW_SCAN_MAX_DATA
        
        # Keep resizing the buffer until it's large enough to hold the scan
        while (i == E2BIG):
            buff, s = iwstruct.pack_wrq(bufflen)
            i, result = iwstruct.iw_get_ext(self.ifname, 
                                            SIOCGIWSCAN,
                                            data=s)
            if i == E2BIG:
                pbuff, newlen = iwstruct.unpack('Pi', s)
                if bufflen < newlen:
                    bufflen = newlen
                else:
                    bufflen = bufflen * 2
        
        if i == EAGAIN:
            return 100
        if i > 0:
            self.errorflag = i
            self.error = result
            return -1
        
        pbuff, reslen = iwstruct.unpack('Pi', s)
        if reslen > 0:
            # Initialize the stream, and turn it into an enumerator
            self.aplist = self._parse(buff.tostring())
            return 0
        
    def _parse(self, data):
        """Parse the event stream, and return a list of Iwscanresult objects
        """
        iwstruct = Iwstruct()
        scanresult = None
        aplist = []

        # Run through the stream, until broken
        while 1:
            # If we're the stream doesn't have enough space left for a header, break
            if len(data) < IW_EV_LCP_LEN:
                break;
        
            # Unpack the header
            length, cmd = iwstruct.unpack('HH', data[:4])
            # If the header says the following data is shorter than the header, then break
            if length < IW_EV_LCP_LEN:
                break;

            # Put the events into their respective result data
            if cmd == SIOCGIWAP:
                if scanresult is not None:
                    aplist.append(scanresult)
                scanresult = Iwscanresult(data[IW_EV_LCP_LEN:length], self.range)
            elif scanresult is None:
                raise RuntimeError, 'Attempting to add an event without AP data'
            else:
                scanresult.addEvent(cmd, data[IW_EV_LCP_LEN:length])
            
            # We're finished with the preveious event
            data = data[length:]
        
        # Don't forgset the final result
        if scanresult.bssid != "00:00:00:00:00:00":
            aplist.append(scanresult)
        else:
            raise RuntimeError, 'Attempting to add an AP without a bssid'
        return aplist

class Iwscanresult(object):
    """An object to contain all the events associated with a single scanned AP
    """
    
    def __init__(self, data, range):
        """Initialize the scan result with the access point data"""
        self.iwstruct = Iwstruct()
        self.range = range
        self.bssid = "%02X:%02X:%02X:%02X:%02X:%02X" % struct_unpack('BBBBBB', data[2:8])
        self.essid = None
        self.mode = None
        self.rate = []
        self.quality = Iwquality() 
        self.frequency = None
        self.encode = None
        self.custom = []
        self.protocol = None

    def addEvent(self, cmd, data):
        """Attempts to add the data from an event to a scanresult
           Only certain data is accept, in which case the result is True
           If the event data is invalid, None is returned
           If the data is valid but unused, False is returned
        """
        if cmd <= SIOCIWLAST:
            if cmd < SIOCIWFIRST:
                return None
        elif cmd >= IWEVFIRST:
            if cmd > IWEVLAST:
                return None
        else:
            return None
            
        if cmd == SIOCGIWESSID:
            self.essid = data[4:]
        elif cmd == SIOCGIWMODE:
            self.mode = modes[self.iwstruct.unpack('i', data[:4])[0]]
        elif cmd == SIOCGIWRATE:
            # TODO, deal with multiple rates, or at least the highest rate
            freqsize = struct_calcsize("ihbb")
            while len(data) >= freqsize:
                iwfreq = Iwfreq(data)
                self.rate.append(iwfreq.getBitrate())
                data = data[freqsize:]
        elif cmd == IWEVQUAL:
            self.quality.parse(data)
        elif cmd == SIOCGIWFREQ:
            self.frequency = Iwfreq(data)
        elif cmd == SIOCGIWENCODE:
            self.encode = data
        elif cmd == IWEVCUSTOM:
            self.custom.append(data[1:])
        elif cmd == SIOCGIWNAME:
            self.protocol = data[:len(data)-2]
        else:
            #print "Cmd:", cmd
            return False
        return True