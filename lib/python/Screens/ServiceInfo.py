from os import path
from Screens.Screen import Screen
from Screens.About import AboutBase
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Sources.List import List
from Components.config import config
from Components.Sources.StaticText import StaticText
from ServiceReference import ServiceReference
from enigma import eListboxPythonMultiContent, eListbox, gFont, iServiceInformation, eServiceCenter, getDesktop, RT_HALIGN_LEFT, RT_VALIGN_CENTER
from Tools.Transponder import ConvertToHumanReadable, getChannelNumber, supportedChannels
import skin

RT_HALIGN_LEFT = 0

TYPE_TEXT = 0
TYPE_VALUE_HEX = 1
TYPE_VALUE_DEC = 2
TYPE_VALUE_HEX_DEC = 3
TYPE_SLIDER = 4
TYPE_VALUE_ORBIT_DEC = 5
TYPE_VALUE_FREQ = 6
TYPE_VALUE_FREQ_FLOAT = 7
TYPE_VALUE_BITRATE = 8

def to_unsigned(x):
	return x & 0xFFFFFFFF

def ServiceInfoListEntry(a, b="", valueType=TYPE_TEXT, param=4):
	if not isinstance(b, str):
		if valueType == TYPE_VALUE_HEX:
			b = ("0x%0" + str(param) + "x") % to_unsigned(b)
		elif valueType == TYPE_VALUE_FREQ:
			b = "%s MHz" % (b / 1000)
		elif valueType == TYPE_VALUE_FREQ_FLOAT:
			b = "%s.%s MHz" % (b / 1000, b % 1000)
		elif valueType == TYPE_VALUE_BITRATE:
			b = "%s" % (b / 1000)
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
		(_("Frequency"), "frequency", TYPE_VALUE_FREQ),
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
		(_("Input stream ID"), "is_id", TYPE_TEXT),
		(_("PLS mode"), "pls_mode", TYPE_TEXT),
		(_("PLS code"), "pls_code", TYPE_TEXT),
	)

	def __init__(self, session, menu_path="", serviceref=None):
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
			screentitle = _("Transponder Information")
			self.type = TYPE_TRANSPONDER_INFO
			self.skinName = "ServiceInfoSimple"
			info = eServiceCenter.getInstance().info(serviceref)
			self.transponder_info = info.getInfoObject(serviceref, iServiceInformation.sTransponderData)
			# info is a iStaticServiceInformation, not a iServiceInformation
			self.info = None
			self.feinfo = None
		else:
			screentitle = _("Service Information")
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
		if config.usage.show_menupath.value == 'large':
			menu_path += screentitle
			title = menu_path
			self["menu_path_compressed"] = StaticText("")
		elif config.usage.show_menupath.value == 'small':
			title = screentitle
			self["menu_path_compressed"] = StaticText(menu_path + " >" if not menu_path.endswith(' / ') else menu_path[:-3] + " >" or "")
		else:
			title = screentitle
			self["menu_path_compressed"] = StaticText("")
		Screen.setTitle(self, title)

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
				videocodec =  ("MPEG2", "AVC", "MPEG1", "MPEG4-VC", "VC1", "VC1-SM", "HEVC", "-")[self.info.getInfo(iServiceInformation.sVideoType)]
				video_height = 0
				video_width = 0
				video_pol = " "
				video_rate = 0
				if path.exists("/proc/stb/vmpeg/0/yres"):
					f = open("/proc/stb/vmpeg/0/yres", "r")
					try:
						video_height = int(f.read(),16)
					except:
						pass
					f.close()
				if path.exists("/proc/stb/vmpeg/0/xres"):
					f = open("/proc/stb/vmpeg/0/xres", "r")
					try:
						video_width = int(f.read(),16)
					except:
						pass
					f.close()
				if path.exists("/proc/stb/vmpeg/0/progressive"):
					f = open("/proc/stb/vmpeg/0/progressive", "r")
					try:
						video_pol = "p" if int(f.read(),16) else "i"
					except:
						pass
					f.close()
				if path.exists("/proc/stb/vmpeg/0/framerate"):
					f = open("/proc/stb/vmpeg/0/framerate", "r")
					try:
						video_rate = int(f.read())
					except:
						pass
					f.close()

				fps  = str((video_rate + 500) / 1000)
				resolution = str(video_width) + "x" + str(video_height) + video_pol + fps

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

	def ShowECMInformation(self):
		from Components.Converter.PliExtraInfo import caid_data
		self["Title"].text = _("Service info - ECM Info")
		tlist = []
		provid = ""
		for caid in sorted(set(self.info.getInfoObject(iServiceInformation.sCAIDPIDs)), key=lambda x: (x[0], x[1])):
			CaIdDescription = _("Undefined")
			extra_info = ""
			for caid_entry in caid_data:
				if int(caid_entry[0], 16) <= caid[0] <= int(caid_entry[1], 16):
					CaIdDescription = caid_entry[2]
					break
			if caid[2]:
				if CaIdDescription == "Seca":
					provid = caid[2][:4]
				if CaIdDescription == "Nagra":
					provid = caid[2][-4:]
				if CaIdDescription == "Via":
					provid = caid[2][-6:]
				if provid:
					extra_info = "provid=%s" % provid
				else:
					extra_info = "extra data=%s" % caid[2]
			from Tools.GetEcmInfo import GetEcmInfo
			ecmdata = GetEcmInfo().getEcmData()
			color = "\c00??;?00" if caid[1] == int(ecmdata[3], 16) and caid[0] == int(ecmdata[1], 16) else ""
			tlist.append(ServiceInfoListEntry("%sECMPid %04X (%d) %04X-%s %s" % (color, caid[1], caid[1], caid[0], CaIdDescription, extra_info)))
		if not tlist:
			tlist.append(ServiceInfoListEntry(_("No ECMPids available (FTA Service)")))
		self["infolist"].l.setList(tlist)
