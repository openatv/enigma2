#
# CpuUsage Converter for Enigma2 (CpuUsage.py)
# Coded by vlamo (c) 2012
#
# Version: 0.4 (11.04.2012 14:05)
# Support: http://dream.altmaster.net/
#
                                          
from Converter import Converter
from Poll import Poll
from Components.Element import cached


class CpuUsage(Converter, object):
    CPU_ALL   = -2
    CPU_TOTAL = -1

    def __init__(self, type):
        Converter.__init__(self, type)
        
        self.percentlist = [ ]
        self.pfmt = "%3d%%"
        if not type or type == "Total":
            self.type = self.CPU_TOTAL
            self.sfmt = "$0"
        elif len(type) == 1 and type[0].isdigit():
            self.type = int(type)
            self.sfmt = "$" + type
            self.pfmt = "%d"
        else:
            self.type = self.CPU_ALL
            self.sfmt = str(type)
            cpus = cpuUsageMonitor.getCpusCount()
            if cpus > -1:
                pos = 0
                while True:
                    pos = self.sfmt.find("$", pos)
                    if pos == -1: break
                    if pos < len(self.sfmt)-1 and \
                       self.sfmt[pos+1].isdigit() and \
                       int(self.sfmt[pos+1]) > cpus:
                        self.sfmt = self.sfmt.replace("$" + self.sfmt[pos+1], "n/a")
                    pos += 1

    def doSuspend(self, suspended):
        if suspended:
            cpuUsageMonitor.disconnectCallback(self.gotPercentage)
        else:
            cpuUsageMonitor.connectCallback(self.gotPercentage)

    def gotPercentage(self, list):
        self.percentlist = list
        self.changed((self.CHANGED_POLL,))

    @cached
    def getText(self):
        res = self.sfmt[:]
        if not self.percentlist:
            self.percentlist = [0] * 3
        for i in range(len(self.percentlist)):
            res = res.replace("$" + str(i), self.pfmt%(self.percentlist[i]))
        res = res.replace("$?", "%d" % (len(self.percentlist)-1))
        return res

    @cached
    def getValue(self):
        if self.type in range(len(self.percentlist)):
            i = self.type
        else:
            i = 0
        try:
            value = self.percentlist[i]
        except IndexError:
            value = 0
        return value

    text = property(getText)
    value = property(getValue)
    range = 100


class CpuUsageMonitor(Poll, object):

    def __init__(self):
        Poll.__init__(self)
        self.__callbacks = [ ]
        self.__curr_info = self.getCpusInfo()
        self.poll_interval = 1400

    def getCpusCount(self):
        return len(self.__curr_info) - 1

    def getCpusInfo(self):
        res = []
        try:
            fd = open("/proc/stat", "r")
            for l in fd:
                if l.find("cpu") == 0:
                    total = busy = 0
                    # tmp = [cpu, usr, nic, sys, idle, iowait, irq, softirq, steal]
                    tmp = l.split()
                    for i in range(1, len(tmp)):
                        tmp[i] = int(tmp[i])
                        total += tmp[i]
                    # busy = total - idle - iowait
                    busy = total - tmp[4] - tmp[5]
                    # append [cpu, total, busy]
                    res.append([tmp[0], total, busy])
            fd.close()
        except:
            pass
        return res

    def poll(self):
        prev_info, self.__curr_info = self.__curr_info, self.getCpusInfo()
        if len(self.__callbacks):
            info = [ ]
            for i in range(len(self.__curr_info)):
                # xxx% = (cur_xxx - prev_xxx) / (cur_total - prev_total) * 100
                try:
                    p = 100 * ( self.__curr_info[i][2] - prev_info[i][2] ) / ( self.__curr_info[i][1] - prev_info[i][1] )
                except ZeroDivisionError:
                    p = 0
                info.append(p)
            for f in self.__callbacks:
                f(info)

    def connectCallback(self, func):
        if not func in self.__callbacks:
            self.__callbacks.append(func)
        if not self.poll_enabled:
            self.poll()
            self.poll_enabled = True

    def disconnectCallback(self, func):
        if func in self.__callbacks:
            self.__callbacks.remove(func)
        if not len(self.__callbacks) and self.poll_enabled:
            self.poll_enabled = False


cpuUsageMonitor = CpuUsageMonitor()


