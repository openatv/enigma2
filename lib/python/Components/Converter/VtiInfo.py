from Components.config import config
from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService
from Components.Element import cached
from Components.Converter.Poll import Poll


class VtiInfo(Poll, Converter):
    ECMINFO = 1
    ONLINETEST = 21
    TEMPINFO = 22
    FANINFO = 23
    ALL = 24

    def __init__(self, type):
        Poll.__init__(self)
        Converter.__init__(self, type)
        self.type = type
        self.poll_interval = 2000
        self.poll_enabled = True
        if type == 'EcmInfo':
            self.type = self.ECMINFO
        elif type == 'OnlineTest':
            self.type = self.ONLINETEST
        elif type == 'TempInfo':
            self.type = self.TEMPINFO
        elif type == 'FanInfo':
            self.type = self.FANINFO
        else:
            self.type = self.ALL

    @cached
    def getText(self):
        textvalue = ''
        service = self.source.service
        if service:
            info = service and service.info()
            if self.type == self.TEMPINFO:
                textvalue = self.tempfile()
            elif self.type == self.FANINFO:
                textvalue = self.fanfile()
            elif self.type == self.ECMINFO:
                if config.misc.ecm_info.value and info and info.getInfoObject(iServiceInformation.sCAIDs):
                    ecm_info = self.ecmfile()
                    if ecm_info:
                        caid = ecm_info.get('caid', '')
                        caid = caid.lstrip('0x')
                        caid = caid.upper()
                        caid = caid.zfill(4)
                        caid = 'CAID: %s' % caid
                        hops = ecm_info.get('hops', None)
                        hops = 'HOPS: %s' % hops
                        ecm_time = ecm_info.get('ecm time', None)
                        if ecm_time:
                            if 'msec' in ecm_time:
                                ecm_time = 'TIME: %s ms' % ecm_time
                            else:
                                ecm_time = 'TIME: %s s' % ecm_time
                        address = ecm_info.get('address', '')
                        using = ecm_info.get('using', '')
                        if using:
                            if using == 'emu':
                                textvalue = '%s - %s' % (caid, ecm_time)
                            elif using == 'CCcam-s2s':
                                textvalue = '%s - %s - %s - %s' % (caid,
                                 address,
                                 hops,
                                 ecm_time)
                            else:
                                textvalue = '%s - %s - %s - %s' % (caid,
                                 address,
                                 hops,
                                 ecm_time)
                        else:
                            source = ecm_info.get('source', None)
                            if source:
                                if source == 'emu':
                                    textvalue = '%s' % caid
                                else:
                                    textvalue = '%s - %s - %s' % (caid, source, ecm_time)
                            oscsource = ecm_info.get('from', None)
                            if oscsource:
                                textvalue = '%s - %s - %s - %s' % (caid,
                                 oscsource,
                                 hops,
                                 ecm_time)
                            decode = ecm_info.get('decode', None)
                            response = ecm_info.get('response', None)
                            response = 'RESPONSE: %s ms' % response
                            provider = ecm_info.get('provider', None)
                            provider = 'PROVIDER: %s' % provider
                            if decode:
                                textvalue = '%s - %s - %s - %s' % (caid,
                                 decode,
                                 response,
                                 provider)
        return textvalue

    text = property(getText)

    @cached
    def getBoolean(self):
        if self.type == self.ONLINETEST:
            onlinecheck = self.pingtest()
            return onlinecheck
        return False

    boolean = property(getBoolean)

    def ecmfile(self):
        ecm = None
        info = {}
        service = self.source.service
        if service:
            frontendInfo = service.frontendInfo()
            if frontendInfo:
                try:
                    ecmpath = '/tmp/ecm%s.info' % frontendInfo.getAll(False).get('tuner_number')
                    with open(ecmpath, 'rb') as fd:
                        ecm = fd.readlines()
                except Exception:
                    try:
                        with open('/tmp/ecm.info', 'rb') as fd:
                            ecm = fd.readlines()
                    except OSError:
                        pass

            if ecm:
                for line in ecm:
                    x = line.lower().find('msec')
                    if x != -1:
                        info['ecm time'] = line[0:x + 4]
                    else:
                        item = line.split(':', 1)
                        if len(item) > 1:
                            info[item[0].strip().lower()] = item[1].strip()
                        elif 'caid' not in info:
                            x = line.lower().find('caid')
                            if x != -1:
                                y = line.find(',')
                                if y != -1:
                                    info['caid'] = line[x + 5:y]

                if info and info.get("from") and config.softcam.hideServerName.value:
                    info["from"] = "".join(["\u2022"] * len(info.get("from")))
        return info

    def tempfile(self):
        temp = ''
        unit = ''
        try:
            with open('/proc/stb/sensors/temp0/value', 'rb') as fd:
                temp = fd.readline().strip()
            with open('/proc/stb/sensors/temp0/unit', 'rb') as fd:
                unit = fd.readline().strip()
            tempinfo = 'TEMP: %s %s%s' % (str(temp), "\u00B0", str(unit))
            return tempinfo
        except Exception:
            pass

    def fanfile(self):
        fan = ''
        try:
            with open('/proc/stb/fp/fan_speed', 'rb') as fd:
                fan = fd.readline().strip()
            faninfo = f'FAN: {fan}'
            return faninfo
        except OSError:
            pass

    def pingtest(self):
        pingpath = '/tmp/.pingtest.info'
        try:
            with open(pingpath, 'rb') as fd:
                pingtestresult = fd.readlines()
        except OSError:
            pingtestresult = None

        if pingtestresult is not None:
            for line in pingtestresult:
                x = line.lower().find('0')
                print(x)
                if x == 0:
                    pingtestresult = 0
                else:
                    pingtestresult = 1

            if pingtestresult == 0:
                return True
        return False

    def changed(self, what):
        if what[0] == self.CHANGED_SPECIFIC and what[1] == iPlayableService.evUpdatedInfo or what[0] == self.CHANGED_POLL:
            Converter.changed(self, what)
