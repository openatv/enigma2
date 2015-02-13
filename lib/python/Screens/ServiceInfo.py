from Screens.About import AboutBase
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Sources.List import List
from ServiceReference import ServiceReference
from enigma import eListboxPythonMultiContent, eListbox, gFont, iServiceInformation, eServiceCenter, getDesktop, RT_HALIGN_LEFT, RT_VALIGN_CENTER
from Tools.Transponder import ConvertToHumanReadable
from Components.Converter.ChannelNumbers import channelnumbers
import skin

RT_HALIGN_LEFT = 0

TYPE_TEXT = 0
TYPE_VALUE_HEX = 1
TYPE_VALUE_DEC = 2
TYPE_VALUE_HEX_DEC = 3
TYPE_SLIDER = 4
TYPE_VALUE_ORBIT_DEC = 5

def to_unsigned(x):
	return x & 0xFFFFFFFF

def ServiceInfoListEntry(a, b, valueType=TYPE_TEXT, param=4):
	if not isinstance(b, str):
		if valueType == TYPE_VALUE_HEX:
			b = ("0x%0" + str(param) + "x") % to_unsigned(b)
		elif valueType == TYPE_VALUE_DEC:
			b = str(b)
		elif valueType == TYPE_VALUE_HEX_DEC:
			b = ("0x%0" + str(param) + "x (%dd)") % (to_unsigned(b), b)
		elif valueType == TYPE_VALUE_ORBIT_DEC:
			direction = 'E'
			if b > 1800:
				b = 3600 - b
				direction = 'W'
			b = "%d.%d%s" % (b // 10, b % 10, direction)
		else:
			b = str(b)

	return (a, b)

TYPE_SERVICE_INFO = 1
TYPE_TRANSPONDER_INFO = 2

class ServiceInfo(AboutBase):
	infoLabels = (
		(_("NIM"), "tuner_name", TYPE_TEXT),
		(_("Type"), "tuner_type", TYPE_TEXT),
		(_("System"), "system", TYPE_TEXT),
		(_("Modulation"), "modulation", TYPE_TEXT),
		(_("Orbital position"), "orbital_position", TYPE_VALUE_DEC),
		(_("Frequency"), "frequency", TYPE_VALUE_DEC),
		(_("Channel"), "channel", TYPE_TEXT),
		(_("Symbol rate"), "symbol_rate", TYPE_VALUE_DEC),
		(_("Polarization"), "polarization", TYPE_TEXT),
		(_("Inversion"), "inversion", TYPE_TEXT),
		(_("FEC"), "fec_inner", TYPE_TEXT),
		(_("Pilot"), "pilot", TYPE_TEXT),
		(_("Roll-off"), "rolloff", TYPE_TEXT),
		(_("Bandwidth"), "bandwidth", TYPE_VALUE_DEC),
		(_("Code rate LP"), "code_rate_lp", TYPE_TEXT),
		(_("Code rate HP"), "code_rate_hp", TYPE_TEXT),
		(_("Constellation"), "constellation", TYPE_TEXT),
		(_("Transmission mode"), "transmission_mode", TYPE_TEXT),
		(_("Guard interval"), "guard_interval", TYPE_TEXT),
		(_("Hierarchy info"), "hierarchy_information", TYPE_TEXT),
	)

	def __init__(self, session, serviceref=None):
		AboutBase.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
			"ok": self.close,
			"cancel": self.close,
			"red": self.information,
			"green": self.pids,
			"yellow": self.transponder,
			"blue": self.tuner
		}, -1)

		if serviceref:
			self.type = TYPE_TRANSPONDER_INFO
			self.skinName = "ServiceInfoSimple"
			info = eServiceCenter.getInstance().info(serviceref)
			self.transponder_info = info.getInfoObject(serviceref, iServiceInformation.sTransponderData)
			# info is a iStaticServiceInformation, not a iServiceInformation
			self.info = None
			self.feinfo = None
		else:
			self.type = TYPE_SERVICE_INFO
			self["key_red"] = self["red"] = Label(_("Service"))
			self["key_green"] = self["green"] = Label(_("PIDs"))
			self["key_yellow"] = self["yellow"] = Label(_("Multiplex"))
			self["key_blue"] = self["blue"] = Label(_("Tuner status"))
			service = session.nav.getCurrentService()
			if service is not None:
				self.info = service.info()
				self.feinfo = service.frontendInfo()
			else:
				self.info = None
				self.feinfo = None

		self["list"] = List([])
		self.onShown.append(self.information)

	def information(self):
		if self.type == TYPE_SERVICE_INFO:
			if self.session.nav.getCurrentlyPlayingServiceOrGroup():
				name = ServiceReference(self.session.nav.getCurrentlyPlayingServiceReference()).getServiceName()
				refstr = self.session.nav.getCurrentlyPlayingServiceReference().toString()
			else:
				name = _("N/A")
				refstr = _("N/A")
			aspect = "-"
			videocodec = "-"
			videomode = "-"
			resolution = "-"
			if self.info:
				videocodec =  ("MPEG2", "MPEG4", "MPEG1", "MPEG4-II", "VC1", "VC1-SM", "-" )[self.info and self.info.getInfo(iServiceInformation.sVideoType)]
				width = self.info.getInfo(iServiceInformation.sVideoWidth)
				height = self.info.getInfo(iServiceInformation.sVideoHeight)
				if width > 0 and height > 0:
					resolution = "%dx%d" % (width, height)
					resolution += ("i", "p", "")[self.info.getInfo(iServiceInformation.sProgressive)]
					resolution += str((self.info.getInfo(iServiceInformation.sFrameRate) + 500) / 1000)
					aspect = self.getServiceInfoValue(iServiceInformation.sAspect)
					if aspect in (1, 2, 5, 6, 9, 0xA, 0xD, 0xE):
						aspect = "4:3"
					else:
						aspect = "16:9"
				f = open("/proc/stb/video/videomode")
				videomode = f.read()[:-1].replace('\n','')
				f.close()

			Labels = ((_("Name"), name, TYPE_TEXT),
					(_("Provider"), self.getServiceInfoValue(iServiceInformation.sProvider), TYPE_TEXT),
					(_("Videoformat"), aspect, TYPE_TEXT),
					(_("Videomode"), videomode, TYPE_TEXT),
					(_("Videosize"), resolution, TYPE_TEXT),
					(_("Videocodec"), videocodec, TYPE_TEXT),
					(_("Namespace"), self.getServiceInfoValue(iServiceInformation.sNamespace), TYPE_VALUE_HEX, 8),
					(_("Service reference"), refstr, TYPE_TEXT))

			self.fillList(Labels)
		else:
			if self.transponder_info:
				self.fillList(self.getFEData(self.transponder_info))

	def pids(self):
		if self.type == TYPE_SERVICE_INFO:
			Labels = ( (_("Video PID"), self.getServiceInfoValue(iServiceInformation.sVideoPID), TYPE_VALUE_HEX_DEC, 4),
					   (_("Audio PID"), self.getServiceInfoValue(iServiceInformation.sAudioPID), TYPE_VALUE_HEX_DEC, 4),
					   (_("PCR PID"), self.getServiceInfoValue(iServiceInformation.sPCRPID), TYPE_VALUE_HEX_DEC, 4),
					   (_("PMT PID"), self.getServiceInfoValue(iServiceInformation.sPMTPID), TYPE_VALUE_HEX_DEC, 4),
					   (_("TXT PID"), self.getServiceInfoValue(iServiceInformation.sTXTPID), TYPE_VALUE_HEX_DEC, 4),
					   (_("TSID"), self.getServiceInfoValue(iServiceInformation.sTSID), TYPE_VALUE_HEX_DEC, 4),
					   (_("ONID"), self.getServiceInfoValue(iServiceInformation.sONID), TYPE_VALUE_HEX_DEC, 4),
					   (_("SID"), self.getServiceInfoValue(iServiceInformation.sSID), TYPE_VALUE_HEX_DEC, 4))
			self.fillList(Labels)

	def showFrontendData(self, real):
		if self.type == TYPE_SERVICE_INFO:
			frontendData = self.feinfo and self.feinfo.getAll(real)

			self.fillList(self.getFEData(frontendData))

	def transponder(self):
		if self.type == TYPE_SERVICE_INFO:
			self.showFrontendData(True)

	def tuner(self):
		if self.type == TYPE_SERVICE_INFO:
			self.showFrontendData(False)

	def getFEData(self, frontendDataOrg):
		if frontendDataOrg and len(frontendDataOrg):
			frontendData = ConvertToHumanReadable(frontendDataOrg)
			return [(label, frontendData[data], format_type)
					for (label, data, format_type) in ServiceInfo.infoLabels
						if data in frontendData]
		return []

	def fillList(self, Labels):
		tlist = []

		for item in Labels:
			if item[1] is None:
				continue
			value = item[1]
			if len(item) < 4:
				tlist.append(ServiceInfoListEntry(item[0] + ":", value, item[2]))
			else:
				tlist.append(ServiceInfoListEntry(item[0] + ":", value, item[2], item[3]))

		self["list"].setList(tlist)

	def getServiceInfoValue(self, what):
		if self.info is None:
			return ""

		v = self.info.getInfo(what)
		if v == -2:
			v = self.info.getInfoString(what)
		elif v == -1:
			v = _("N/A")

		return v
