# converter STBInfo - renamed from pliLayoutInfo.py to not conflict on modifications
#
# <convert type="STBInfo">{FlashInfo,HddInfo,HddTemp,LoadAvg,MemFree,MemTotal,SwapFree,SwapTotal,UsbInfo,SystemTemp},{Short,Full}</convert>
# 
#     <widget source="session.CurrentService" render="Label" ...
#       <convert type="STBInfo">MemTotal,Short</convert>
#     </widget>
#     <widget source="session.CurrentService" render="Label" ...
#       <convert type="STBInfo">HddInfo,Short</convert>
#     </widget>
#     <widget source="session.CurrentService" render="Label" ...
#       <convert type="STBInfo">UsbInfo,Short</convert>
#     </widget>


from Components.Converter.Converter import Converter
from Components.Element import cached
from Poll import Poll
from os import popen, statvfs

SIZE_UNITS = ['B',
 'KB',
 'MB',
 'GB',
 'TB',
 'PB',
 'EB']

class STBInfo(Poll, Converter):
    HDDTEMP = 0
    LOADAVG = 1
    MEMTOTAL = 2
    MEMFREE = 3
    SWAPTOTAL = 4
    SWAPFREE = 5
    USBINFO = 6
    HDDINFO = 7
    FLASHINFO = 8
    DRIVERINFO = 9
    SYSTEMTEMP = 10

    def __init__(self, type):
        Converter.__init__(self, type)
        Poll.__init__(self)
        type = type.split(',')
        self.shortFormat = 'Short' in type
        self.fullFormat = 'Full' in type
        if 'HddTemp' in type:
            self.type = self.HDDTEMP
        elif 'LoadAvg' in type:
            self.type = self.LOADAVG
        elif 'MemTotal' in type:
            self.type = self.MEMTOTAL
        elif 'MemFree' in type:
            self.type = self.MEMFREE
        elif 'SwapTotal' in type:
            self.type = self.SWAPTOTAL
        elif 'SwapFree' in type:
            self.type = self.SWAPFREE
        elif 'UsbInfo' in type:
            self.type = self.USBINFO
        elif 'HddInfo' in type:
            self.type = self.HDDINFO
        elif 'DriverInfo' in type:
            self.type = self.DRIVERINFO
        elif 'SystemTemp' in type:
            self.type = self.SYSTEMTEMP
        else:
            self.type = self.FLASHINFO
        if self.type in (self.FLASHINFO, self.HDDINFO, self.USBINFO):
            self.poll_interval = 5000
        else:
            self.poll_interval = 1000
        self.poll_enabled = True

    def doSuspend(self, suspended):
        if suspended:
            self.poll_enabled = False
        else:
            self.downstream_elements.changed((self.CHANGED_POLL,))
            self.poll_enabled = True

    @cached
    def getText(self):
        text = 'N/A'
        if self.type == self.HDDTEMP:
            text = self.getHddTemp()
        elif self.type == self.SYSTEMTEMP:
            text = self.getSystemTemp()
        elif self.type == self.LOADAVG:
            text = self.getLoadAvg()
        elif self.type == self.DRIVERINFO:
            text = self.getDriverInfo()
        else:
            entry = {self.MEMTOTAL: ('Mem', 'Ram'),
             self.MEMFREE: ('Mem', 'Ram'),
             self.SWAPTOTAL: ('Swap', 'Swap'),
             self.SWAPFREE: ('Swap', 'Swap'),
             self.USBINFO: ('/media/usb', 'USB'),
             self.HDDINFO: ('/media/hdd', 'HDD'),
             self.FLASHINFO: ('/', 'Flash')}[self.type]
            if self.type in (self.USBINFO, self.HDDINFO, self.FLASHINFO):
                list = self.getDiskInfo(entry[0])
            else:
                list = self.getMemInfo(entry[0])
            if list[0] == 0:
                text = '%s: Not Available' % entry[1]
            elif self.shortFormat:
                text = '%s:  Total %s, in use %s%%' % (entry[1], self.getSizeStr(list[0]), list[3])
            elif self.fullFormat:
                text = '%s:  Total %s  Free %s  Used %s (%s%%)' % (entry[1],
                 self.getSizeStr(list[0]),
                 self.getSizeStr(list[2]),
                 self.getSizeStr(list[1]),
                 list[3])
            else:
                text = '%s:  Total %s  Used %s  Free %s' % (entry[1],
                 self.getSizeStr(list[0]),
                 self.getSizeStr(list[1]),
                 self.getSizeStr(list[2]))
        return text

    @cached
    def getValue(self):
        result = 0
        if self.type in (self.MEMTOTAL,
         self.MEMFREE,
         self.SWAPTOTAL,
         self.SWAPFREE):
            entry = {self.MEMTOTAL: 'Mem',
             self.MEMFREE: 'Mem',
             self.SWAPTOTAL: 'Swap',
             self.SWAPFREE: 'Swap'}[self.type]
            result = self.getMemInfo(entry)[3]
        elif self.type in (self.USBINFO, self.HDDINFO, self.FLASHINFO):
            path = {self.USBINFO: '/media/usb',
             self.HDDINFO: '/media/hdd',
             self.FLASHINFO: '/'}[self.type]
            result = self.getDiskInfo(path)[3]
        return result
    text = property(getText)
    value = property(getValue)
    range = 100

    def getHddTemp(self):
        textvalue = 'No info'
        info = '0'
        try:
            out_line = popen('hddtemp -n -q /dev/sda').readline()
            info = 'Hdd C: ' + out_line[:4]
            textvalue = info
        except:
            pass
        return textvalue

    def getSystemTemp(self):
        textvalue = 'No info'
        info = '0'
        try:
            out_line = popen('cat /proc/stb/fp/temp_sensor').readline().strip()
            info = 'CPU temperature: ' + out_line[:4] + ' C'
            textvalue = info
        except:
            pass
        return textvalue

    def getLoadAvg(self):
        textvalue = 'No info'
        info = '0'
        try:
            out_line = popen('cat /proc/loadavg').readline()
            info = 'Loadavg: ' + out_line[:15]
            textvalue = info
        except:
            pass
        return textvalue

    def getDriverInfo(self):
        textvalue = 'No info'
        info = '0'
        try:
            popen('modinfo dvb |grep version: > /tmp/modinfo')
            out_line = popen('cat /tmp/modinfo').readline()
            info = 'Driver: ' + out_line[16:50]
            textvalue = info
        except:
            pass
        return textvalue

    def getMemInfo(self, value):
        result = [0,
         0,
         0,
         0]
        try:
            check = 0
            fd = open('/proc/meminfo')
            for line in fd:
                if value + 'Total' in line:
                    check += 1
                    result[0] = int(line.split()[1]) * 1024
                elif value + 'Available' in line:
                    check += 1
                    result[2] = int(line.split()[1]) * 1024
                if check > 1:
                    if result[0] > 0:
                        result[1] = result[0] - result[2]
                        result[3] = result[1] * 100 / result[0]
                    break
            fd.close()
        except:
            pass
        return result

    def getDiskInfo(self, path):

        def isMountPoint():
            try:
                fd = open('/proc/mounts', 'r')
                for line in fd:
                    l = line.split()
                    if len(l) > 1 and l[1] == path:
                        return True
                fd.close()
            except:
                return None
            return False
        result = [0,
         0,
         0,
         0]
        if isMountPoint():
            try:
                st = statvfs(path)
            except:
                st = None
            if st is not None and 0 not in (st.f_bsize, st.f_blocks):
                result[0] = st.f_bsize * st.f_blocks
                result[2] = st.f_bsize * st.f_bavail
                result[1] = result[0] - result[2]
                result[3] = result[1] * 100 / result[0]
        return result

    def getSizeStr(self, value, u = 0):
        fractal = 0
        if value >= 1024:
            fmt = '%(size)u.%(frac)d %(unit)s'
            while value >= 1024 and u < len(SIZE_UNITS):
                value, mod = divmod(value, 1024)
                fractal = mod * 10 / 1024
                u += 1
        else:
            fmt = '%(size)u %(unit)s'
        return fmt % {'size': value,
         'frac': fractal,
         'unit': SIZE_UNITS[u]}

    def doSuspend(self, suspended):
        if suspended:
            self.poll_enabled = False
        else:
            self.downstream_elements.changed((self.CHANGED_POLL,))
            self.poll_enabled = True
