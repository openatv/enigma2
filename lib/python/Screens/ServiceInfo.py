from os import path
from Components.HTMLComponent import HTMLComponent
from Components.GUIComponent import GUIComponent
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
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

def ServiceInfoListEntry(a, b, valueType=TYPE_TEXT, param=4):
	screenwidth = getDesktop(0).size().width()
	if not isinstance(b, str):
		if valueType == TYPE_VALUE_HEX:
			b = ("%0" + str(param) + "X") % to_unsigned(b)
		elif valueType == TYPE_VALUE_FREQ:
			b = "%s MHz" % (b / 1000)
		elif valueType == TYPE_VALUE_FREQ_FLOAT:
			b = "%.3f MHz" % (b / 1000.0)
		elif valueType == TYPE_VALUE_BITRATE:
			b = "%s KSymbols/s" % (b / 1000)
		elif valueType == TYPE_VALUE_HEX_DEC:
			b = ("%0" + str(param) + "X (%d)") % (to_unsigned(b), b)
		elif valueType == TYPE_VALUE_ORBIT_DEC:
			direction = 'E'
			if b > 1800:
				b = 3600 - b
				direction = 'W'
			b = ("%d.%d%s") % (b // 10, b % 10, direction)
		else:
			b = str(b)
	x, y, w, h = skin.parameters.get("ServiceInfo",(0, 0, 300, 30))
	xa, ya, wa, ha = skin.parameters.get("ServiceInfoLeft",(0, 0, 300, 25))
	xb, yb, wb, hb = skin.parameters.get("ServiceInfoRight",(300, 0, 600, 25))
	return [
		#PyObject *type, *px, *py, *pwidth, *pheight, *pfnt, *pstring, *pflags;
		(eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, RT_HALIGN_LEFT, ""),
		(eListboxPythonMultiContent.TYPE_TEXT, xa, ya, wa, ha, 0, RT_HALIGN_LEFT, a),
		(eListboxPythonMultiContent.TYPE_TEXT, xb, yb, wb, hb, 0, RT_HALIGN_LEFT, b)
	]

class ServiceInfoList(HTMLComponent, GUIComponent):
	def __init__(self, source):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.list = source
		self.l.setList(self.list)
		self.fontName = "Regular"
		self.fontSize = 23
		self.ItemHeight = 25

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib == "font":
					font = skin.parseFont(value, ((1,1),(1,1)))
					self.fontName = font.family
					self.fontSize = font.pointSize
				elif attrib == "itemHeight":
					self.ItemHeight = int(value)
				else:
					attribs.append((attrib,value))
			self.skinAttributes = attribs
		rc = GUIComponent.applySkin(self, desktop, screen)
		self.setFontsize()
		self.l.setItemHeight(self.ItemHeight)
		return rc

	GUI_WIDGET = eListbox

	def setFontsize(self):
		self.l.setFont(0, gFont(self.fontName, self.fontSize))
		self.l.setFont(1, gFont(self.fontName, self.fontSize + 5))

	def postWidgetCreate(self, instance):
		self.instance.setContent(self.l)
		self.setFontsize()

TYPE_SERVICE_INFO = 1
TYPE_TRANSPONDER_INFO = 2

class ServiceInfo(Screen):
	def __init__(self, session, menu_path="", serviceref=None):
		Screen.__init__(self, session)
		self.menu_path = menu_path

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"ok": self.close,
			"cancel": self.close,
			"red": self.close,
		}, -1)

		self["infolist"] = ServiceInfoList([])
		self["key_red"] = self["red"] = Label(_("Exit"))

		self.transponder_info = self.info = self.feinfo = None
		play_service = session.nav.getCurrentlyPlayingServiceReference()
		if serviceref and not play_service and play_service != serviceref:
			screentitle = _("Transponder Information")
			self.type = TYPE_TRANSPONDER_INFO
			self.skinName="ServiceInfoSimple"
			self.transponder_info = eServiceCenter.getInstance().info(serviceref).getInfoObject(serviceref, iServiceInformation.sTransponderData)
			# info is a iStaticServiceInformation, not a iServiceInformation
		else:
			screentitle = _("Service")
			self.type = TYPE_SERVICE_INFO
			service = session.nav.getCurrentService()
			if service:
				self.transponder_info = None
				self.info = service.info()
				self.feinfo = service.frontendInfo()
				if self.feinfo and not self.feinfo.getAll(True):
					self.feinfo = None
					serviceref = play_service
					self.transponder_info = serviceref and eServiceCenter.getInstance().info(serviceref).getInfoObject(serviceref, iServiceInformation.sTransponderData)
			if self.feinfo or self.transponder_info:
				self["actions2"] = ActionMap(["ColorActions"],
				{
					"yellow": self.ShowServiceInformation,
					"blue": self.ShowTransponderInformation
				}, -1)
				self["key_yellow"] = self["yellow"] = Label(_("Service & PIDs"))
				self["key_blue"] = self["blue"] = Label(_("Tuner settings values"))
			else:
				self.skinName="ServiceInfoSimple"

		if config.usage.show_menupath.value == 'large':
			self.menu_path += screentitle
			title = self.menu_path
			self["menu_path_compressed"] = StaticText("")
			self.menu_path += ' / '
		elif config.usage.show_menupath.value == 'small':
			title = screentitle
			condtext = ""
			if self.menu_path and not self.menu_path.endswith(' / '):
				condtext = self.menu_path + " >"
			elif self.menu_path:
				condtext = self.menu_path[:-3] + " >"
			self["menu_path_compressed"] = StaticText(condtext)
			self.menu_path += screentitle + ' / '
		else:
			title = screentitle
			self["menu_path_compressed"] = StaticText("")
		Screen.setTitle(self, title)

		tlist = [ ]
		self.onShown.append(self.ShowServiceInformation)

	def ShowServiceInformation(self):
		menu_path = self.menu_path
		if self.type == TYPE_SERVICE_INFO:
			screentitle = _("Service & PIDs")
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

			if self.feinfo or self.transponder_info:
				self["key_blue"].text = self["blue"].text = _("Tuner settings values")
			if self.session.nav.getCurrentlyPlayingServiceOrGroup():
				name = ServiceReference(self.session.nav.getCurrentlyPlayingServiceReference()).getServiceName()
				refstr = self.session.nav.getCurrentlyPlayingServiceReference().toString()
				reftype = self.session.nav.getCurrentlyPlayingServiceReference().type
			else:
				name = _("N/A")
				refstr = _("N/A")
				reftype = 0
			aspect = "-"
			videocodec = "-"
			resolution = "-"
			if self.info:
				videocodec =  ("MPEG2", "AVC", "MPEG1", "MPEG4-VC", "VC1", "VC1-SM", "HEVC", "N/A")[self.info.getInfo(iServiceInformation.sVideoType)]
				width = self.info.getInfo(iServiceInformation.sVideoWidth)
				height = self.info.getInfo(iServiceInformation.sVideoHeight)
				if width > 0 and height > 0:
					resolution = videocodec + " - "
					resolution += "%dx%d - " % (width,height)
					resolution += str((self.info.getInfo(iServiceInformation.sFrameRate) + 500) / 1000)
					resolution += ("i", "p", "")[self.info.getInfo(iServiceInformation.sProgressive)]
					aspect = self.getServiceInfoValue(iServiceInformation.sAspect)
					aspect = aspect in ( 1, 2, 5, 6, 9, 0xA, 0xD, 0xE ) and "4:3" or "16:9"
					resolution += " - "+aspect+""
			if "%3a//" in refstr and reftype not in (1,257,4098,4114):
				fillList = [(_("Service name"), name, TYPE_TEXT),
					(_("Videocodec, size & format"), resolution, TYPE_TEXT),
					(_("Service reference"), ":".join(refstr.split(":")[:9]), TYPE_TEXT),
					(_("URL"), refstr.split(":")[10].replace("%3a", ":"), TYPE_TEXT)]
			else:
				if ":/" in refstr:
					fillList = [(_("Service name"), name, TYPE_TEXT),
						(_("Videocodec, size & format"), resolution, TYPE_TEXT),
						(_("Service reference"), ":".join(refstr.split(":")[:9]), TYPE_TEXT),
						(_("Filename"), refstr.split(":")[10], TYPE_TEXT)]
				else:
					fillList = [(_("Service name"), name, TYPE_TEXT),
						(_("Provider"), self.getServiceInfoValue(iServiceInformation.sProvider), TYPE_TEXT),
						(_("Videocodec, size & format"), resolution, TYPE_TEXT)]
					if "%3a//" in refstr:
						fillList = fillList + [(_("Service reference"), ":".join(refstr.split(":")[:9]), TYPE_TEXT),
							(_("URL"), refstr.split(":")[10].replace("%3a", ":"), TYPE_TEXT)]
					else:
						fillList = fillList + [(_("Service reference"), refstr, TYPE_TEXT)]
				fillList = fillList + [(_("Namespace"), self.getServiceInfoValue(iServiceInformation.sNamespace), TYPE_VALUE_HEX, 8),
					(_("Service ID"), self.getServiceInfoValue(iServiceInformation.sSID), TYPE_VALUE_HEX_DEC, 4),
					(_("Video PID"), self.getServiceInfoValue(iServiceInformation.sVideoPID), TYPE_VALUE_HEX_DEC, 4),
					(_("Audio PID"), self.getServiceInfoValue(iServiceInformation.sAudioPID), TYPE_VALUE_HEX_DEC, 4),
					(_("PCR PID"), self.getServiceInfoValue(iServiceInformation.sPCRPID), TYPE_VALUE_HEX_DEC, 4),
					(_("PMT PID"), self.getServiceInfoValue(iServiceInformation.sPMTPID), TYPE_VALUE_HEX_DEC, 4),
					(_("TXT PID"), self.getServiceInfoValue(iServiceInformation.sTXTPID), TYPE_VALUE_HEX_DEC, 4),
					(_("TSID"), self.getServiceInfoValue(iServiceInformation.sTSID), TYPE_VALUE_HEX_DEC, 4),
					(_("ONID"), self.getServiceInfoValue(iServiceInformation.sONID), TYPE_VALUE_HEX_DEC, 4)]
			self.fillList(fillList)
		elif self.transponder_info:
			self.fillList(self.getFEData(self.transponder_info))

	def ShowTransponderInformation(self):
		menu_path = self.menu_path
		screentitle = ""
		if self.type == TYPE_SERVICE_INFO:
			if self.feinfo and self.feinfo.getAll(True):
				if self["key_blue"].text == _("Tuner settings values"):
					screentitle = _("Tuning info: settings values")
					self["key_blue"].text = self["blue"].text = _("Tuner live values")
					frontendData = self.feinfo and self.feinfo.getAll(True)
				else:
					screentitle = _("Tuning info: live values")
					self["key_blue"].text = self["blue"].text = _("Tuner settings values")
					frontendData = self.feinfo and self.feinfo.getAll(False)
				self.fillList(self.getFEData(frontendData))
			elif self.transponder_info:
				screentitle = _("Tuning info: settings values")
				self["key_blue"].text = self["blue"].text = _("Tuner settings values")
				self.fillList(self.getFEData(self.transponder_info))
				

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

	def getFEData(self, frontendDataOrg):
		if frontendDataOrg and len(frontendDataOrg):
			frontendData = ConvertToHumanReadable(frontendDataOrg)
			if self.transponder_info:
				tuner = (_("Type"), frontendData["tuner_type"], TYPE_TEXT)
			else:
				tuner = (_("NIM & Type"), chr(ord('A') + frontendData["tuner_number"]) + " - " + frontendData["tuner_type"], TYPE_TEXT)
			if frontendDataOrg["tuner_type"] == "DVB-S":
				return (tuner,
					(_("System & Modulation"), "%s %s" % (frontendData["system"], frontendData["modulation"]), TYPE_TEXT),
					(_("Orbital position"), "%s" % frontendData["orbital_position"], TYPE_TEXT),
					(_("Frequency & Polarization"), "%s - %s" % (frontendData.get("frequency", 0), frontendData["polarization"]), TYPE_TEXT),
					(_("Symbol rate & FEC"), "%s - %s" % (frontendData.get("symbol_rate", 0), frontendData["fec_inner"]), TYPE_TEXT),
					(_("Input Stream ID"), "%s" % (frontendData.get("is_id", 0)), TYPE_TEXT),
					(_("PLS Mode & PLS Code"), "%s - %s" % (frontendData["pls_mode"], frontendData["pls_code"]), TYPE_TEXT),
					(_("Inversion, Pilot & Roll-off"), "%s - %s - %s" % (frontendData["inversion"], frontendData.get("pilot", None), str(frontendData.get("rolloff", None))), TYPE_TEXT))
			elif frontendDataOrg["tuner_type"] == "DVB-C":
				return (tuner,
					(_("Modulation"),"%s" % frontendData["modulation"], TYPE_TEXT),
					(_("Frequency"), "%s" % frontendData.get("frequency", 0), TYPE_TEXT),
					(_("Symbol rate & FEC"), "%s - %s" % (frontendData.get("symbol_rate", 0), frontendData["fec_inner"]), TYPE_TEXT),
					(_("Inversion"), "%s" % frontendData["inversion"], TYPE_TEXT))
			elif frontendDataOrg["tuner_type"] == "DVB-T":
				return (tuner,
					(_("Frequency & Channel"), "%s - Ch. %s" % (frontendData.get("frequency", 0), getChannelNumber(frontendData["frequency"], frontendData["tuner_number"])), TYPE_TEXT),
					(_("Inversion & Bandwidth"), "%s - %s" % (frontendData["inversion"], frontendData["bandwidth"]), TYPE_TEXT),
					(_("Code R. LP-HP & Guard Int"), "%s - %s - %s" % (frontendData["code_rate_lp"], frontendData["code_rate_hp"], frontendData["guard_interval"]), TYPE_TEXT),
					(_("Constellation & FFT mode"), "%s - %s" % (frontendData["constellation"], frontendData["transmission_mode"]), TYPE_TEXT),
					(_("Hierarchy info"), "%s" % frontendData["hierarchy_information"], TYPE_TEXT))
			elif frontendDataOrg["tuner_type"] == "ATSC":
				return (tuner,
					(_("System & Modulation"), "%s - %s" % (frontendData["system"], frontendData["modulation"]), TYPE_TEXT),
					(_("Frequency"), "%s" % frontendData.get("frequency", 0), TYPE_TEXT),
					(_("Inversion"), "%s" % frontendData["inversion"], TYPE_TEXT))
		return []

	def fillList(self, Labels):
		tlist = []
		for item in Labels:
			if item[1]:
				value = item[1]
				if len(item) < 4:
					tlist.append(ServiceInfoListEntry(item[0]+":", value, item[2]))
				else:
					tlist.append(ServiceInfoListEntry(item[0]+":", value, item[2], item[3]))
		self["infolist"].l.setList(tlist)

	def getServiceInfoValue(self, what):
		if self.info:
			v = self.info.getInfo(what)
			if v == -2:
				v = self.info.getInfoString(what)
			elif v == -1:
				v = _("N/A")
			return v
		return ""
