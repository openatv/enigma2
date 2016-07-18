from enigma import iServiceInformation
from Components.Converter.Converter import Converter
from Components.Element import cached
from xml.etree.cElementTree import parse
from Poll import Poll

class SmartInfo(Poll, Converter, object):
    EXPERTINFO = 0

    def __init__(self, type):
        Converter.__init__(self, type)
        Poll.__init__(self)
        self.type = self.EXPERTINFO
        self.poll_interval = 30000
        self.poll_enabled = True
        self.ar_fec = ['Auto',
         '1/2',
         '2/3',
         '3/4',
         '5/6',
         '7/8',
         '3/5',
         '4/5',
         '8/9',
         '9/10',
         'None',
         'None',
         'None',
         'None',
         'None']
        self.ar_pol = ['H',
         'V',
         'CL',
         'CR',
         'na',
         'na',
         'na',
         'na',
         'na',
         'na',
         'na',
         'na']
        self.satNames = {}
        self.readSatXml()

    @cached
    def getText(self):
        service = self.source.service
        info = service and service.info()
        if not info:
            return ''
        Ret_Text = ''
        orbital = self.getOrbitalPosition(info)
        satName = self.satNames.get(orbital, orbital)
        if self.type == self.EXPERTINFO:
            feinfo = service and service.frontendInfo()
            if feinfo is not None:
                frontendData = feinfo and feinfo.getAll(True)
                if frontendData is not None:
                    if frontendData.get('tuner_type') == 'DVB-S' or frontendData.get('tuner_type') == 'DVB-C':
                        frequency = str(frontendData.get('frequency') / 1000) + ' MHz'
                        symbolrate = str(frontendData.get('symbol_rate') / 1000)
                        try:
                            if frontendData.get('tuner_type') == 'DVB-S':
                                polarisation_i = frontendData.get('polarization')
                            else:
                                polarisation_i = 0
                            fec_i = frontendData.get('fec_inner')
                            Ret_Text = Ret_Text + frequency + ' ' + self.ar_pol[polarisation_i] + ' ' + self.ar_fec[fec_i] + ' ' + symbolrate + ' '
                        except:
                            Ret_Text = Ret_Text + frequency + ' ' + symbolrate + ' '

                        orb_pos = ''
                    elif frontendData.get('tuner_type') == 'DVB-T':
                        frequency = str(frontendData.get('frequency') / 1000) + ' MHz'
                        Ret_Text = Ret_Text + 'Frequency: ' + frequency
                Ret_Text = Ret_Text + ' ' + satName
            return Ret_Text
        return 'n/a'

    text = property(getText)

    def changed(self, what):
        Converter.changed(self, what)

    def readSatXml(self):
        satXml = parse('/etc/tuxbox/satellites.xml').getroot()
        if satXml is not None:
            for sat in satXml.findall('sat'):
                name = sat.get('name') or None
                position = sat.get('position') or None
                if name is not None and position is not None:
                    position = '%s.%s' % (position[:-1], position[-1:])
                    if position.startswith('-'):
                        position = '%sW' % position[1:]
                    else:
                        position = '%sE' % position
                    if position.startswith('.'):
                        position = '0%s' % position
                    self.satNames[position] = name.encode('utf-8')

    def getOrbitalPosition(self, info):
        transponderData = info.getInfoObject(iServiceInformation.sTransponderData)
        orbital = 0
        if transponderData is not None:
            if isinstance(transponderData, float):
                return ''
            if transponderData.has_key('tuner_type'):
                if transponderData['tuner_type'] == 'DVB-S' or transponderData['tuner_type'] == 'DVB-S2':
                    orbital = transponderData['orbital_position']
                    orbital = int(orbital)
                    if orbital > 1800:
                        orbital = str(float(3600 - orbital) / 10.0) + 'W'
                    else:
                        orbital = str(float(orbital) / 10.0) + 'E'
                    return orbital
        return ''