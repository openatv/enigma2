from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox

from Components.ActionMap import ActionMap, NumberActionMap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.config import config, configfile, getConfigListEntry
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.MenuList import MenuList

from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import SCOPE_ACTIVE_SKIN, resolveFilename, fileExists

from enigma import eTimer, RT_HALIGN_LEFT, eListboxPythonMultiContent, gFont, getDesktop, eSize, ePoint
from xml.etree import ElementTree

from operator import itemgetter
import os, time
import urllib2
import skin

###global
f = 1
sizeH = 700
HDSKIN = False
screenwidth = getDesktop(0).size().width()
if screenwidth and screenwidth == 1920:
	f = 1.5
	sizeH = screenwidth - 150
	HDSKIN = True
elif screenwidth and screenwidth > 1920:
	f = 3
	HDSKIN = True
	sizeH = screenwidth - 300
elif screenwidth and screenwidth > 1024:
	sizeH = screenwidth - 100
	HDSKIN = True
###global

class OscamInfo:
	def __init__(self):
		pass

	TYPE = 0
	NAME = 1
	PROT = 2
	CAID_SRVID = 3
	SRVNAME = 4
	ECMTIME = 5
	IP_PORT = 6
	HEAD = { NAME: _("Label"), PROT: _("Protocol"),
		CAID_SRVID: _("CAID:SrvID"), SRVNAME: _("Serv.Name"),
		ECMTIME: _("ECM-Time"), IP_PORT: _("IP address") }
	version = ""

	def confPath(self):
		owebif = False
		oport = None
		opath = None
		ipcompiled = False

		# Find and parse running oscam
		if fileExists("/tmp/.oscam/oscam.version"):
			with open('/tmp/.oscam/oscam.version', 'r') as data:
				for i in data:
					if "web interface support:" in i.lower():
						owebif = i.split(":")[1].strip()
						if owebif == "no":
							owebif = False
						elif owebif == "yes":
							owebif = True
					elif "webifport:" in i.lower():
						oport = i.split(":")[1].strip()
						if oport == "0":
							oport = None
					elif "configdir:" in i.lower():
						opath = i.split(":")[1].strip()
					elif "ipv6 support:" in i.lower():
						ipcompiled = i.split(":")[1].strip()
						if ipcompiled == "no":
							ipcompiled = False
						elif ipcompiled == "yes":
							ipcompiled = True
					else:
						continue
		return owebif, oport, opath, ipcompiled

	def getUserData(self):
		[webif, port, conf, ipcompiled] = self.confPath()
		if conf == None:
			conf = ""
		conf += "/oscam.conf"

		# Assume that oscam webif is NOT blocking localhost, IPv6 is also configured if it is compiled in,
		# and no user and password are required
		blocked = False
		ipconfigured = ipcompiled
		user = pwd = None

		ret = _("oscam webif disabled")

		if webif and port is not None:
		# oscam reports it got webif support and webif is running (Port != 0)
			if conf is not None and os.path.exists(conf):
				# If we have a config file, we need to investigate it further
				with open(conf, 'r') as data:
					for i in data:
						if "httpuser" in i.lower():
							user = i.split("=")[1].strip()
						elif "httppwd" in i.lower():
							pwd = i.split("=")[1].strip()
						elif "httpport" in i.lower():
							port = i.split("=")[1].strip()
						elif "httpallowed" in i.lower():
							# Once we encounter a httpallowed statement, we have to assume oscam webif is blocking us ...
							blocked = True
							allowed = i.split("=")[1].strip()
							if "::1" in allowed or "127.0.0.1" in allowed or "0.0.0.0-255.255.255.255" in allowed:
								# ... until we find either 127.0.0.1 or ::1 in allowed list
								blocked = False
							if "::1" not in allowed:
								ipconfigured = False

			if not blocked:
				ret = [user, pwd, port, ipconfigured]

		return ret

	def openWebIF(self, part = None, reader = None):
		self.proto = "http"
		if config.oscaminfo.userdatafromconf.value:
			udata = self.getUserData()
			if isinstance(udata, str):
				return False, udata
			else:
				self.port = udata[2]
				self.username = udata[0]
				self.password = udata[1]
				self.ipaccess = udata[3]

			if self.ipaccess == "yes":
				self.ip = "::1"
			else:
				self.ip = "127.0.0.1"
		else:
			self.ip = ".".join("%d" % d for d in config.oscaminfo.ip.value)
			self.port = str(config.oscaminfo.port.value)
			self.username = str(config.oscaminfo.username.value)
			self.password = str(config.oscaminfo.password.value)

		if self.port.startswith( '+' ):
			self.proto = "https"
			self.port.replace("+","")

		if part is None:
			self.url = "%s://%s:%s/oscamapi.html?part=status" % ( self.proto, self.ip, self.port )
		else:
			self.url = "%s://%s:%s/oscamapi.html?part=%s" % ( self.proto, self.ip, self.port, part )
		if part is not None and reader is not None:
			self.url = "%s://%s:%s/oscamapi.html?part=%s&label=%s" % ( self.proto, self.ip, self.port, part, reader )

		opener = urllib2.build_opener( urllib2.HTTPHandler )
		if not self.username == "":
			pwman = urllib2.HTTPPasswordMgrWithDefaultRealm()
			pwman.add_password( None, self.url, self.username, self.password )
			handlers = urllib2.HTTPDigestAuthHandler( pwman )
			opener = urllib2.build_opener( urllib2.HTTPHandler, handlers )
			urllib2.install_opener( opener )
		request = urllib2.Request( self.url )
		err = False
		try:
			data = urllib2.urlopen( request ).read()
			# print data
		except urllib2.URLError, e:
			if hasattr(e, "reason"):
				err = str(e.reason)
			elif hasattr(e, "code"):
				err = str(e.code)
		if err is not False:
			print "[openWebIF] error: %s" % err
			return False, err
		else:
			return True, data

	def readXML(self, typ):
		if typ == "l":
			self.showLog = True
			part = "status&appendlog=1"
		else:
			self.showLog = False
			part = None
		result = self.openWebIF(part)
		retval = []
		tmp = {}
		if result[0]:
			if not self.showLog:
				data = ElementTree.XML(result[1])
#				if typ=="version":
#					if data.attrib.has_key("version"):
#						self.version = data.attrib["version"]
#					else:
#						self.version = "n/a"
#					return self.version
				status = data.find("status")
				clients = status.findall("client")
				for cl in clients:
					name = cl.attrib["name"]
					proto = cl.attrib["protocol"]
					if cl.attrib.has_key("au"):
						au = cl.attrib["au"]
					else:
						au = ""
					caid = cl.find("request").attrib["caid"]
					srvid = cl.find("request").attrib["srvid"]
					if cl.find("request").attrib.has_key("ecmtime"):
						ecmtime = cl.find("request").attrib["ecmtime"]
						if ecmtime == "0" or ecmtime == "":
							ecmtime = _("n/a")
						else:
							ecmtime = str(float(ecmtime) / 1000)[:5]
					else:
						ecmtime = "not available"
					srvname = cl.find("request").text
					if srvname is not None:
						if ":" in srvname:
							srvname_short = srvname.split(":")[1].strip()
						else:
							srvname_short = srvname
					else:
						srvname_short = _("n/A")
					login = cl.find("times").attrib["login"]
					online = cl.find("times").attrib["online"]
					if proto.lower() == "dvbapi":
						ip = ""
					else:
						ip = cl.find("connection").attrib["ip"]
						if ip == "0.0.0.0":
							ip = ""
					port = cl.find("connection").attrib["port"]
					connstatus = cl.find("connection").text
					if name != "" and name != "anonymous" and proto != "":
						try:
							tmp[cl.attrib["type"]].append( (name, proto, "%s:%s" % (caid, srvid), srvname_short, ecmtime, ip, connstatus) )
						except KeyError:
							tmp[cl.attrib["type"]] = []
							tmp[cl.attrib["type"]].append( (name, proto, "%s:%s" % (caid, srvid), srvname_short, ecmtime, ip, connstatus) )
			else:
				if "<![CDATA" not in result[1]:
					tmp = result[1].replace("<log>", "<log><![CDATA[").replace("</log>", "]]></log>")
				else:
					tmp = result[1]
				data = ElementTree.XML(tmp)
				log = data.find("log")
				logtext = log.text
			if typ == "s":
				if tmp.has_key("r"):
					for i in tmp["r"]:
						retval.append(i)
				if tmp.has_key("p"):
					for i in tmp["p"]:
						retval.append(i)
			elif typ == "c":
				if tmp.has_key("c"):
					for i in tmp["c"]:
						retval.append(i)
			elif typ == "l":
				tmp = logtext.split("\n")
				retval = []
				for i in tmp:
					tmp2 = i.split(" ")
					if len(tmp2) > 2:
						del tmp2[2]
						txt = ""
						for j in tmp2:
							txt += "%s " % j.strip()
						retval.append( txt )

			return retval

		else:
			return result[1]
	def getVersion(self):
		xmldata = self.openWebIF()
		if xmldata[0]:
			data = ElementTree.XML(xmldata[1])
			if data.attrib.has_key("version"):
				self.version = data.attrib["version"]
			else:
				self.version = _("n/a")
			return self.version
		else:
			self.version = _("n/a")
		return self.version

	def getTotalCards(self, reader):
		xmldata = self.openWebIF(part = "entitlement", reader = reader)
		if xmldata[0]:
			xmld = ElementTree.XML(xmldata[1])
			cards = xmld.find("reader").find("cardlist")
			cardTotal = cards.attrib["totalcards"]
			return cardTotal
		else:
			return None
	def getReaders(self, spec = None):
		xmldata = self.openWebIF()
		readers = []
		if xmldata[0]:
			data = ElementTree.XML(xmldata[1])
			status = data.find("status")
			clients = status.findall("client")
			for cl in clients:
				if cl.attrib.has_key("type"):
					if cl.attrib["type"] == "p" or cl.attrib["type"] == "r":
						if spec is not None:
							proto = cl.attrib["protocol"]
							if spec in proto:
								name = cl.attrib["name"]
								cards = self.getTotalCards(name)
								readers.append( ( _("%s ( %s Cards )") % (name, cards), name) )
						else:
							if cl.attrib["name"] != "" and cl.attrib["name"] != "" and cl.attrib["protocol"] != "":
								readers.append( (cl.attrib["name"], cl.attrib["name"]) )  # return tuple for later use in Choicebox
			return readers
		else:
			return None

	def getClients(self):
		xmldata = self.openWebIF()
		clientnames = []
		if xmldata[0]:
			data = ElementTree.XML(xmldata[1])
			status = data.find("status")
			clients = status.findall("client")
			for cl in clients:
				if cl.attrib.has_key("type"):
					if cl.attrib["type"] == "c":
						readers.append( (cl.attrib["name"], cl.attrib["name"]) )  # return tuple for later use in Choicebox
			return clientnames
		else:
			return None

	def getECMInfo(self, ecminfo):
		result = []
		if os.path.exists(ecminfo):
			data = open(ecminfo, "r").readlines()
			for i in data:
				if "caid" in i:
					result.append( (_("CAID"), i.split(":")[1].strip()) )
				elif "pid" in i:
					result.append( (_("PID"), i.split(":")[1].strip()) )
				elif "prov" in i:
					result.append( (_("Provider"), i.split(":")[1].strip()) )
				elif "reader" in i:
					result.append( (_("Reader"), i.split(":")[1].strip()) )
				elif "from" in i:
					result.append( (_("Address"), i.split(":")[1].strip()) )
				elif "protocol" in i:
					result.append( (_("Protocol"), i.split(":")[1].strip()) )
				elif "hops" in i:
					result.append( (_("Hops"), i.split(":")[1].strip()) )
				elif "ecm time" in i:
					result.append( (_("ECM Time"), i.split(":")[1].strip()) )
			return result
		else:
			return "%s not found" % self.ecminfo

class oscMenuList(MenuList):
	def __init__(self, list, itemH = 30):
		MenuList.__init__(self, list, False, eListboxPythonMultiContent)
		self.l.setItemHeight(int(itemH*f))
		self.l.setFont(0, gFont("Regular", int(20*f)))
		self.l.setFont(1, gFont("Regular", int(18*f)))
		self.clientFont = gFont("Regular", int(16*f))
		self.l.setFont(2, self.clientFont)
		self.l.setFont(3, gFont("Regular", int(12*f)))

class OscamInfoMenu(Screen):
	def __init__(self, session):
		self.session = session
		self.menu = [ _("Show /tmp/ecm.info"), _("Show Clients"), _("Show Readers/Proxies"), _("Show Log"), _("Card infos (CCcam-Reader)"), _("ECM Statistics"), _("Setup") ]
		Screen.__init__(self, session)
		self.osc = OscamInfo()
		self["mainmenu"] = oscMenuList([])
		self["actions"] = NumberActionMap(["OkCancelActions", "InputActions", "ColorActions"],
					{
						"ok": self.ok,
						"cancel": self.exit,
						"red": self.red,
						"green": self.green,
						"yellow": self.yellow,
						"blue": self.blue,
						"1": self.keyNumberGlobal,
						"2": self.keyNumberGlobal,
						"3": self.keyNumberGlobal,
						"4": self.keyNumberGlobal,
						"5": self.keyNumberGlobal,
						"6": self.keyNumberGlobal,
						"7": self.keyNumberGlobal,
						"8": self.keyNumberGlobal,
						"9": self.keyNumberGlobal,
						"0": self.keyNumberGlobal,
						"up": self.up,
						"down": self.down
						}, -1)
		self.onLayoutFinish.append(self.showMenu)

	def ok(self):
		selected = self["mainmenu"].getSelectedIndex()
		self.goEntry(selected)
	def cancel(self):
		self.close()
	def exit(self):
		self.close()
	def keyNumberGlobal(self, num):
		if num == 0:
			numkey = 10
		else:
			numkey = num
		if numkey < len(self.menu) - 3:
			self["mainmenu"].moveToIndex(numkey + 3)
			self.goEntry(numkey + 3)

	def red(self):
		self["mainmenu"].moveToIndex(0)
		self.goEntry(0)
	def green(self):
		self["mainmenu"].moveToIndex(1)
		self.goEntry(1)
	def yellow(self):
		self["mainmenu"].moveToIndex(2)
		self.goEntry(2)
	def blue(self):
		self["mainmenu"].moveToIndex(3)
		self.goEntry(3)
	def up(self):
		pass
	def down(self):
		pass
	def goEntry(self, entry):
		if entry in (1,2,3) and config.oscaminfo.userdatafromconf.value and self.osc.confPath()[0] is None:
			config.oscaminfo.userdatafromconf.setValue(False)
			config.oscaminfo.userdatafromconf.save()
			self.session.openWithCallback(self.ErrMsgCallback, MessageBox, _("File oscam.conf not found.\nPlease enter username/password manually."), MessageBox.TYPE_ERROR)
		elif entry == 0:
			if os.path.exists("/tmp/ecm.info"):
				self.session.open(oscECMInfo)
			else:
				pass
		elif entry == 1:
			self.session.open(oscInfo, "c")
		elif entry == 2:
			self.session.open(oscInfo, "s")
		elif entry == 3:
			self.session.open(oscInfo, "l")
		elif entry == 4:
			osc = OscamInfo()
			reader = osc.getReaders("cccam")  # get list of available CCcam-Readers
			if isinstance(reader, list):
				if len(reader) == 1:
					self.session.open(oscEntitlements, reader[0][1])
				else:
					self.callbackmode = "cccam"
					self.session.openWithCallback(self.chooseReaderCallback, ChoiceBox, title = _("Please choose CCcam-Reader"), list=reader)
		elif entry == 5:
			osc = OscamInfo()
			reader = osc.getReaders()
			if reader is not None:
				reader.append( (_("All"), "all") )
				if isinstance(reader, list):
					if len(reader) == 1:
						self.session.open(oscReaderStats, reader[0][1])
					else:
						self.callbackmode = "readers"
						self.session.openWithCallback(self.chooseReaderCallback, ChoiceBox, title = _("Please choose reader"), list=reader)
		elif entry == 6:
			self.session.open(OscamInfoConfigScreen)

	def chooseReaderCallback(self, retval):
		print retval
		if retval is not None:
			if self.callbackmode == "cccam":
				self.session.open(oscEntitlements, retval[1])
			else:
				self.session.open(oscReaderStats, retval[1])

	def ErrMsgCallback(self, retval):
		print retval
		self.session.open(OscamInfoConfigScreen)

	def buildMenu(self, mlist):
		keys = ["red", "green", "yellow", "blue", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", ""]
		menuentries = []
		k = 0
		for t in mlist:
			res = [ t ]
			if t.startswith("--"):
				png = resolveFilename(SCOPE_ACTIVE_SKIN, "div-h.png")
				if fileExists(png):
					png = LoadPixmap(png)
				if png is not None:
					x, y, w, h = skin.parameters.get("ChoicelistDash",(0, 2*f, 800*f, 2*f))
					res.append((eListboxPythonMultiContent.TYPE_PIXMAP, x, y, w, h, png))
					x, y, w, h = skin.parameters.get("ChoicelistName",(45*f, 2*f, 800*f, 25*f))
					res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, RT_HALIGN_LEFT, t[2:]))
					png2 = resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/key_" + keys[k] + ".png")
					if fileExists(png2):
						png2 = LoadPixmap(png2)
					if png2 is not None:
						x, y, w, h = skin.parameters.get("ChoicelistIcon",(5*f, 0, 35*f, 25*f))
						res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, x, y, w, h, png2))
			else:
				x, y, w, h = skin.parameters.get("ChoicelistName",(45*f, 2*f, 800*f, 25*f))
				res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, RT_HALIGN_LEFT, t))
				png2 = resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/key_" + keys[k] + ".png")
				if fileExists(png2):
					png2 = LoadPixmap(png2)
				if png2 is not None:
					x, y, w, h = skin.parameters.get("ChoicelistIcon",(5*f, 0, 35*f, 25*f))
					res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, x, y, w, h, png2))
			menuentries.append(res)
			if k < len(keys) - 1:
				k += 1
		return menuentries

	def showMenu(self):
		entr = self.buildMenu(self.menu)
		self.setTitle(_("Oscam Info - Main Menu"))
		self["mainmenu"].l.setList(entr)
		self["mainmenu"].moveToIndex(0)

class oscECMInfo(Screen, OscamInfo):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.ecminfo = "/tmp/ecm.info"
		self["output"] = oscMenuList([])
		if config.oscaminfo.autoupdate.value:
			self.loop = eTimer()
			self.loop.callback.append(self.showData)
			timeout = config.oscaminfo.intervall.value * 1000
			self.loop.start(timeout, False)
		self["actions"] = ActionMap(["OkCancelActions"],
					{
						"ok": self.exit,
						"cancel": self.exit
					}, -1)
		self.onLayoutFinish.append(self.showData)

	def exit(self):
		if config.oscaminfo.autoupdate.value:
			self.loop.stop()
		self.close()

	def buildListEntry(self, listentry):
		return [
			"",
			(eListboxPythonMultiContent.TYPE_TEXT, 10*f, 2*f, 300*f, 30*f, 0, RT_HALIGN_LEFT, listentry[0]),
			(eListboxPythonMultiContent.TYPE_TEXT, 300*f, 2*f, 300*f, 30*f, 0, RT_HALIGN_LEFT, listentry[1])
			]

	def showData(self):
		data = self.getECMInfo(self.ecminfo)
		out = []
		y = 0
		for i in data:
			out.append(self.buildListEntry(i))
		self["output"].l.setItemHeight(int(30*f))
		self["output"].l.setList(out)
		self["output"].selectionEnabled(False)

class oscInfo(Screen, OscamInfo):
	def __init__(self, session, what):
		global HDSKIN, sizeH
		self.session = session
		self.what = what
		self.firstrun = True
		self.listchange = True
		self.scrolling = False
		self.webif_data = self.readXML(typ = self.what)
		ypos = 10
		ysize = 350
		self.rows = 12
		self.itemheight = 25
		self.sizeLH = sizeH - 20
		self.skin = """<screen position="center,center" size="%d, %d" title="Client Info" >""" % (sizeH, ysize)
		button_width = int(sizeH / 4)
		for k, v in enumerate(["red", "green", "yellow", "blue"]):
			xpos = k * button_width
			self.skin += """<ePixmap name="%s" position="%d,%d" size="35,25" pixmap="/usr/share/enigma2/skin_default/buttons/key_%s.png" zPosition="1" transparent="1" alphatest="on" />""" % (v, xpos, ypos, v)
			self.skin += """<widget source="key_%s" render="Label" position="%d,%d" size="%d,%d" font="Regular;18" zPosition="1" valign="center" transparent="1" />""" % (v, xpos + 40, ypos, button_width, 22)
		self.skin +="""<ePixmap name="divh" position="0,37" size="%d,2" pixmap="/usr/share/enigma2/skin_default/div-h.png" transparent="1" alphatest="on" />""" % sizeH
		self.skin +="""<widget name="output" position="10,45" size="%d,%d" zPosition="1" scrollbarMode="showOnDemand" />""" % ( self.sizeLH, ysize - 50)
		self.skin += """</screen>"""
		Screen.__init__(self, session)
		self.mlist = oscMenuList([])
		self["output"] = self.mlist
		self.errmsg = ""
		self["key_red"] = StaticText(_("Close"))
		if self.what == "c":
			self["key_green"] = StaticText("")
			self["key_yellow"] = StaticText(_("Servers"))
			self["key_blue"] = StaticText(_("Log"))
		elif self.what == "s":
			self["key_green"] = StaticText(_("Clients"))
			self["key_yellow"] = StaticText("")
			self["key_blue"] = StaticText(_("Log"))
		elif self.what == "l":
			self["key_green"] = StaticText(_("Clients"))
			self["key_yellow"] = StaticText(_("Servers"))
			self["key_blue"] = StaticText("")
		else:
			self["key_green"] = StaticText(_("Clients"))
			self["key_yellow"] = StaticText(_("Servers"))
			self["key_blue"] = StaticText(_("Log"))
		if config.oscaminfo.autoupdate.value:
			self.loop = eTimer()
			self.loop.callback.append(self.showData)
			timeout = config.oscaminfo.intervall.value * 1000
			self.loop.start(timeout, False)
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"],
					{
						"ok": self.key_ok,
						"cancel": self.exit,
						"red": self.exit,
						"green": self.key_green,
						"yellow": self.key_yellow,
						"blue": self.key_blue,
						"up": self.key_up,
						"down": self.key_down,
						"right": self.key_right,
						"left": self.key_left,
						"moveUp": self.key_moveUp,
						"moveDown": self.key_moveDown
					}, -1)
		self.onLayoutFinish.append(self.showData)

	def key_ok(self):
		self.disableScrolling()
		self.showData()

	def key_up(self):
		self.enableScrolling()
		self["output"].up()
		if self.what != "l" and self["output"].getSelectedIndex() < 1:
			self["output"].moveToIndex(1)

	def key_down(self):
		self.enableScrolling()
		self["output"].down()

	def key_right(self):
		self.enableScrolling()
		self["output"].pageDown()

	def key_left(self):
		self.enableScrolling()
		self["output"].pageUp()
		if self.what != "l" and self["output"].getSelectedIndex() < 1:
			self["output"].moveToIndex(1)

	def key_moveUp(self):
		self.enableScrolling()
		if self.what != "l":
			self["output"].moveToIndex(1)
		else:
			self["output"].moveToIndex(0)

	def key_moveDown(self):
		self.enableScrolling()
		self["output"].moveToIndex(len(self.out)-1)

	def key_green(self):
		if self.what == "c":
			pass
		else:
			self.listchange = True
			self.what = "c"
			self.key_ok()

	def key_yellow(self):
		if self.what == "s":
			pass
		else:
			self.listchange = True
			self.what = "s"
			self.key_ok()

	def key_blue(self):
		if self.what == "l":
			pass
		else:
			self.listchange = True
			self.what = "l"
			self.key_ok()

	def exit(self):
		if config.oscaminfo.autoupdate.value:
			self.loop.stop()
		self.close()

	def buildListEntry(self, listentry, heading = False):
		res = [""]
		x = 0
		if not HDSKIN:
			self.fieldsize = [ 100, 130, 100, 150, 80, 130 ]
			self.startPos = [ 10, 110, 240, 340, 490, 570 ]
			useFont = 3
		else:
			self.fieldsize = [ 150*f, 150*f, 150*f, 300*f, 150*f, 200*f ]
			self.startPos = [ 50*f, 200*f, 350*f, 500*f, 800*f, 950*f ]
			useFont = 2

		ypos = 2
		if isinstance(self.errmsg, tuple):
			useFont = 0  # overrides previous font-size in case of an error message. (if self.errmsg is a tuple, an error occurred which will be displayed instead of regular results
		elif heading:
			useFont = 1
			ypos = -2
		if not heading:
			status = listentry[len(listentry)-1]
			colour = "0xffffff"
			if status == "OK" or "CONNECTED" or status == "CARDOK":
				colour = "0x389416"
			if status == "NEEDINIT" or status == "CARDOK":
				colour = "0xbab329"
			if status == "OFF" or status == "ERROR":
				colour = "0xf23d21"
		else:
			colour = "0xffffff"
		for i in listentry[:-1]:
			xsize = self.fieldsize[x]
			xpos = self.startPos[x]
			res.append( (eListboxPythonMultiContent.TYPE_TEXT, xpos, ypos*f, xsize, self.itemheight*f, useFont, RT_HALIGN_LEFT, i, int(colour, 16)) )
			x += 1
		if heading:
			png = resolveFilename(SCOPE_ACTIVE_SKIN, "div-h.png")
			if fileExists(png):
				png = LoadPixmap(png)
			if png is not None:
				res.append( (eListboxPythonMultiContent.TYPE_PIXMAP, 0, (self.itemheight-2)*f, self.sizeLH, 2*f, png))
		return res

	def buildLogListEntry(self, listentry):
		res = [""]
		for i in listentry:
			if i.strip() != "" or i is not None:
				res.append( (eListboxPythonMultiContent.TYPE_TEXT, 5*f, 0, self.sizeLH,self.itemheight*f, 2, RT_HALIGN_LEFT, i) )
		return res

	def showData(self):
		if self.firstrun:
			data = self.webif_data
			self.firstrun = False
		else:
			data = self.readXML(typ = self.what)
		self.out = []
		self.itemheight = 25
		if not isinstance(data,str):
			if self.what != "l":
				heading = ( self.HEAD[self.NAME], self.HEAD[self.PROT], self.HEAD[self.CAID_SRVID],
						self.HEAD[self.SRVNAME], self.HEAD[self.ECMTIME], self.HEAD[self.IP_PORT], "")
				self.out = [ self.buildListEntry(heading, heading=True)]
				for i in data:
					self.out.append(self.buildListEntry(i))
			else:
				for i in data:
					if i != "":
						self.out.append( self.buildLogListEntry( (i,) ))
			if self.what == "c":
				self.setTitle(_("Client Info ( Oscam-Version: %s )") % self.getVersion())
				self["key_green"].setText("")
				self["key_yellow"].setText(_("Servers"))
				self["key_blue"].setText(_("Log"))
			elif self.what == "s":
				self.setTitle(_("Server Info ( Oscam-Version: %s )") % self.getVersion())
				self["key_green"].setText(_("Clients"))
				self["key_yellow"].setText("")
				self["key_blue"].setText(_("Log"))
			elif self.what == "l":
				self.setTitle(_("Oscam Log ( Oscam-Version: %s )") % self.getVersion())
				self["key_green"].setText(_("Clients"))
				self["key_yellow"].setText(_("Servers"))
				self["key_blue"].setText("")
				self.itemheight = 20
		else:
			self.errmsg = (data,)
			if config.oscaminfo.autoupdate.value:
				self.loop.stop()
			for i in self.errmsg:
				self.out.append( self.buildListEntry( (i,) ))
			self.setTitle(_("Error") + ": " + data)
			self["key_green"].setText(_("Clients"))
			self["key_yellow"].setText(_("Servers"))
			self["key_blue"].setText(_("Log"))

		if self.listchange:
			self.listchange = False
			self["output"].l.setItemHeight(int(self.itemheight*f))
			self["output"].instance.setScrollbarMode(0) #"showOnDemand"
			self.rows = int(self["output"].instance.size().height() / (self.itemheight*f))
			if self.what != "l" and self.rows < len(self.out):
				self.enableScrolling(True)
				return
			self.disableScrolling(True)
		if self.scrolling:
			self["output"].l.setList(self.out)
		else:
			self["output"].l.setList(self.out[-self.rows:])

	def disableScrolling(self, force=False):
		if force or self.scrolling:
			self.scrolling = False
			self["output"].selectionEnabled(False)

	def enableScrolling(self, force=False):
		if force or (not self.scrolling and self.rows < len(self.out)):
			self.scrolling = True
			self["output"].selectionEnabled(True)
			self["output"].l.setList(self.out)
			if self.what != "l":
				self["output"].moveToIndex(1)
			else:
				self["output"].moveToIndex(len(self.out)-1)

class oscEntitlements(Screen, OscamInfo):
	global HDSKIN, sizeH
	sizeLH = sizeH - 20
	skin = """<screen position="center,center" size="%s, 400" title="Client Info" >
			<widget source="output" render="Listbox" position="10,10" size="%s,400" scrollbarMode="showOnDemand" >
				<convert type="TemplatedMultiContent">
				{"templates":
					{"default": (55,[
							MultiContentEntryText(pos = (0, 1), size = (80, 24), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is caid
							MultiContentEntryText(pos = (90, 1), size = (150, 24), font=0, flags = RT_HALIGN_LEFT, text = 1), # index 1 is csystem
							MultiContentEntryText(pos = (250, 1), size = (40, 24), font=0, flags = RT_HALIGN_LEFT, text = 2), # index 2 is hop 1
							MultiContentEntryText(pos = (290, 1), size = (40, 24), font=0, flags = RT_HALIGN_LEFT, text = 3), # index 3 is hop 2
							MultiContentEntryText(pos = (330, 1), size = (40, 24), font=0, flags = RT_HALIGN_LEFT, text = 4), # index 4 is hop 3
							MultiContentEntryText(pos = (370, 1), size = (40, 24), font=0, flags = RT_HALIGN_LEFT, text = 5), # index 5 is hop 4
							MultiContentEntryText(pos = (410, 1), size = (40, 24), font=0, flags = RT_HALIGN_LEFT, text = 6), # index 6 is hop 5
							MultiContentEntryText(pos = (480, 1), size = (70, 24), font=0, flags = RT_HALIGN_LEFT, text = 7), # index 7 is sum of cards for caid
							MultiContentEntryText(pos = (550, 1), size = (80, 24), font=0, flags = RT_HALIGN_LEFT, text = 8), # index 8 is reshare
							MultiContentEntryText(pos = (0, 25), size = (700, 24), font=1, flags = RT_HALIGN_LEFT, text = 9), # index 9 is providers
													]),
					"HD": (55,[
							MultiContentEntryText(pos = (0, 1), size = (80, 24), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is caid
							MultiContentEntryText(pos = (90, 1), size = (150, 24), font=0, flags = RT_HALIGN_LEFT, text = 1), # index 1 is csystem
							MultiContentEntryText(pos = (250, 1), size = (40, 24), font=0, flags = RT_HALIGN_LEFT, text = 2), # index 2 is hop 1
							MultiContentEntryText(pos = (290, 1), size = (40, 24), font=0, flags = RT_HALIGN_LEFT, text = 3), # index 3 is hop 2
							MultiContentEntryText(pos = (330, 1), size = (40, 24), font=0, flags = RT_HALIGN_LEFT, text = 4), # index 4 is hop 3
							MultiContentEntryText(pos = (370, 1), size = (40, 24), font=0, flags = RT_HALIGN_LEFT, text = 5), # index 5 is hop 4
							MultiContentEntryText(pos = (410, 1), size = (40, 24), font=0, flags = RT_HALIGN_LEFT, text = 6), # index 6 is hop 5
							MultiContentEntryText(pos = (480, 1), size = (70, 24), font=0, flags = RT_HALIGN_LEFT, text = 7), # index 7 is sum of cards for caid
							MultiContentEntryText(pos = (550, 1), size = (80, 24), font=0, flags = RT_HALIGN_LEFT, text = 8), # index 8 is reshare
							MultiContentEntryText(pos = (630, 1), size = (1024, 50), font=1, flags = RT_HALIGN_LEFT, text = 9), # index 9 is providers

												]),
					},
					"fonts": [gFont("Regular", 18),gFont("Regular", 14),gFont("Regular", 24),gFont("Regular", 20)],
					"itemHeight": 56
				}
				</convert>
			</widget>
		</screen>""" % ( sizeH, sizeLH)
	def __init__(self, session, reader):
		global HDSKIN, sizeH
		Screen.__init__(self, session)
		self.mlist = oscMenuList([])
		self.cccamreader = reader
		self["output"] = List([ ])
		self["actions"] = ActionMap(["OkCancelActions"],
					{
						"ok": self.showData,
						"cancel": self.exit
					}, -1)
		self.onLayoutFinish.append(self.showData)

	def exit(self):
		self.close()

	def buildList(self, data):
		caids = data.keys()
		caids.sort()
		outlist = []
		res = [ ("CAID", _("System"), "1", "2", "3", "4", "5", "Total", _("Reshare"), "") ]
		for i in caids:
			csum = 0
			ca_id = i
			csystem = data[i]["system"]
			hops = data[i]["hop"]
			csum += sum(hops)
			creshare = data[i]["reshare"]
			prov = data[i]["provider"]
			if not HDSKIN:
				providertxt = _("Providers: ")
				linefeed = ""
			else:
				providertxt = ""
				linefeed = "\n"
			for j in prov:
				providertxt += "%s - %s%s" % ( j[0], j[1], linefeed )
			res.append( ( 	ca_id,
					csystem,
					str(hops[1]),str(hops[2]), str(hops[3]), str(hops[4]), str(hops[5]), str(csum), str(creshare),
					providertxt[:-1]
					) )
			outlist.append(res)
		return res

	def showData(self):
		xmldata_for_reader = self.openWebIF(part = "entitlement", reader = self.cccamreader)
		xdata = ElementTree.XML(xmldata_for_reader[1])
		reader = xdata.find("reader")
		if reader.attrib.has_key("hostaddress"):
			hostadr = reader.attrib["hostaddress"]
			host_ok = True
		else:
			host_ok = False
		cardlist = reader.find("cardlist")
		cardTotal = cardlist.attrib["totalcards"]
		cards = cardlist.findall("card")
		caid = {}
		for i in cards:
			ccaid = i.attrib["caid"]
			csystem = i.attrib["system"]
			creshare = i.attrib["reshare"]
			if not host_ok:
				hostadr = i.find("hostaddress").text
			chop = int(i.attrib["hop"])
			if chop > 5:
				chop = 5
			if caid.has_key(ccaid):
				if caid[ccaid].has_key("hop"):
					caid[ccaid]["hop"][chop] += 1
				else:
					caid[ccaid]["hop"] = [ 0, 0, 0, 0, 0, 0 ]
					caid[ccaid]["hop"][chop] += 1
				caid[ccaid]["reshare"] = creshare
				caid[ccaid]["provider"] = [ ]
				provs = i.find("providers")
				for prov in provs.findall("provider"):
					caid[ccaid]["provider"].append( (prov.attrib["provid"], prov.text) )
				caid[ccaid]["system"] = csystem
			else:
				caid[ccaid] = {}
				if caid[ccaid].has_key("hop"):
					caid[ccaid]["hop"][chop] += 1
				else:
					caid[ccaid]["hop"] = [ 0, 0, 0, 0, 0, 0]
					caid[ccaid]["hop"][chop] += 1
				caid[ccaid]["reshare"] = creshare
				caid[ccaid]["provider"] = [ ]
				provs = i.find("providers")
				for prov in provs.findall("provider"):
					caid[ccaid]["provider"].append( (prov.attrib["provid"], prov.text) )
				caid[ccaid]["system"] = csystem
		result = self.buildList(caid)
		if HDSKIN:
			self["output"].setStyle("HD")
		else:
			self["output"].setStyle("default")
		self["output"].setList(result)
		title = [ _("Reader"), self.cccamreader, _("Cards:"), cardTotal, _("Server:"), hostadr ]
		self.setTitle( " ".join(title))

class oscReaderStats(Screen, OscamInfo):
	global HDSKIN, sizeH
	sizeLH = sizeH - 20
	skin = """<screen position="center,center" size="%s, 400" title="Client Info" >
			<widget source="output" render="Listbox" position="10,10" size="%s,400" scrollbarMode="showOnDemand" >
				<convert type="TemplatedMultiContent">
				{"templates":
					{"default": (25,[
							MultiContentEntryText(pos = (0, 1), size = (100, 24), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is caid
							MultiContentEntryText(pos = (100, 1), size = (50, 24), font=0, flags = RT_HALIGN_LEFT, text = 1), # index 1 is csystem
							MultiContentEntryText(pos = (150, 1), size = (150, 24), font=0, flags = RT_HALIGN_LEFT, text = 2), # index 2 is hop 1
							MultiContentEntryText(pos = (300, 1), size = (60, 24), font=0, flags = RT_HALIGN_LEFT, text = 3), # index 3 is hop 2
							MultiContentEntryText(pos = (360, 1), size = (60, 24), font=0, flags = RT_HALIGN_LEFT, text = 4), # index 4 is hop 3
							MultiContentEntryText(pos = (420, 1), size = (80, 24), font=0, flags = RT_HALIGN_LEFT, text = 5), # index 5 is hop 4
							MultiContentEntryText(pos = (510, 1), size = (80, 24), font=0, flags = RT_HALIGN_LEFT, text = 6), # index 6 is hop 5
							MultiContentEntryText(pos = (590, 1), size = (80, 24), font=0, flags = RT_HALIGN_LEFT, text = 7), # index 7 is sum of cards for caid
							]),
					"HD": (25,[
							MultiContentEntryText(pos = (0, 1), size = (200, 24), font=1, flags = RT_HALIGN_LEFT, text = 0), # index 0 is caid
							MultiContentEntryText(pos = (200, 1), size = (70, 24), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 1 is csystem
							MultiContentEntryText(pos = (300, 1), size = (220, 24), font=1, flags = RT_HALIGN_LEFT, text = 2), # index 2 is hop 1
							MultiContentEntryText(pos = (540, 1), size = (80, 24), font=1, flags = RT_HALIGN_LEFT, text = 3), # index 3 is hop 2
							MultiContentEntryText(pos = (630, 1), size = (80, 24), font=1, flags = RT_HALIGN_LEFT, text = 4), # index 4 is hop 3
							MultiContentEntryText(pos = (720, 1), size = (130, 24), font=1, flags = RT_HALIGN_LEFT, text = 5), # index 5 is hop 4
							MultiContentEntryText(pos = (840, 1), size = (130, 24), font=1, flags = RT_HALIGN_LEFT, text = 6), # index 6 is hop 5
							MultiContentEntryText(pos = (970, 1), size = (100, 24), font=1, flags = RT_HALIGN_LEFT, text = 7), # index 7 is sum of cards for caid
							]),
					},
					"fonts": [gFont("Regular", 14),gFont("Regular", 18),gFont("Regular", 24),gFont("Regular", 20)],
					"itemHeight": 26
				}
				</convert>
			</widget>
		</screen>""" % ( sizeH, sizeLH)
	def __init__(self, session, reader):
		global HDSKIN, sizeH
		Screen.__init__(self, session)
		if reader == "all":
			self.allreaders = True
		else:
			self.allreaders = False
		self.reader = reader
		self.mlist = oscMenuList([])
		self["output"] = List([ ])
		self["actions"] = ActionMap(["OkCancelActions"],
					{
						"ok": self.showData,
						"cancel": self.exit
					}, -1)
		self.onLayoutFinish.append(self.showData)

	def exit(self):
		self.close()

	def buildList(self, data):
		caids = data.keys()
		caids.sort()
		outlist = []
		res = [ ("CAID", "System", "1", "2", "3", "4", "5", "Total", "Reshare", "") ]
		for i in caids:
			csum = 0
			ca_id = i
			csystem = data[i]["system"]
			hops = data[i]["hop"]
			csum += sum(hops)
			creshare = data[i]["reshare"]
			prov = data[i]["provider"]
			if not HDSKIN:
				providertxt = _("Providers: ")
				linefeed = ""
			else:
				providertxt = ""
				linefeed = "\n"
			for j in prov:
				providertxt += "%s - %s%s" % ( j[0], j[1], linefeed )
			res.append( ( 	ca_id,
					csystem,
					str(hops[1]),str(hops[2]), str(hops[3]), str(hops[4]), str(hops[5]), str(csum), str(creshare),
					providertxt[:-1]
					) )
			outlist.append(res)
		return res

	def sortData(self, datalist, sort_col, reverse = False):
		return sorted(datalist, key=itemgetter(sort_col), reverse = reverse)

	def showData(self):
		readers = self.getReaders()
		result = []
		title2 = ""
		for i in readers:
			xmldata = self.openWebIF(part = "readerstats", reader = i[1])
			emm_wri = emm_ski = emm_blk = emm_err = ""
			if xmldata[0]:
				xdata = ElementTree.XML(xmldata[1])
				rdr = xdata.find("reader")
#					emms = rdr.find("emmstats")
#					if emms.attrib.has_key("totalwritten"):
#						emm_wri = emms.attrib["totalwritten"]
#					if emms.attrib.has_key("totalskipped"):
#						emm_ski = emms.attrib["totalskipped"]
#					if emms.attrib.has_key("totalblocked"):
#						emm_blk = emms.attrib["totalblocked"]
#					if emms.attrib.has_key("totalerror"):
#						emm_err = emms.attrib["totalerror"]

				ecmstat = rdr.find("ecmstats")
				totalecm = ecmstat.attrib["totalecm"]
				ecmcount = ecmstat.attrib["count"]
				lastacc = ecmstat.attrib["lastaccess"]
				ecm = ecmstat.findall("ecm")
				if ecmcount > 0:
					for j in ecm:
						caid = j.attrib["caid"]
						channel = j.attrib["channelname"]
						avgtime = j.attrib["avgtime"]
						lasttime = j.attrib["lasttime"]
						retcode = j.attrib["rc"]
						rcs = j.attrib["rcs"]
						num = j.text
						if rcs == "found":
							avg_time = str(float(avgtime) / 1000)[:5]
							last_time = str(float(lasttime) / 1000)[:5]
							if j.attrib.has_key("lastrequest"):
								lastreq = j.attrib["lastrequest"]
								try:
									last_req = lastreq.split("T")[1][:-5]
								except IndexError:
									last_req = time.strftime("%H:%M:%S",time.localtime(float(lastreq)))
							else:
								last_req = ""
						else:
							avg_time = last_time = last_req = ""
#						if lastreq != "":
#							last_req = lastreq.split("T")[1][:-5]
						if self.allreaders:
							result.append( (i[1], caid, channel, avg_time, last_time, rcs, last_req, int(num)) )
							title2 = _("( All readers)")
						else:
							if i[1] == self.reader:
								result.append( (i[1], caid, channel, avg_time, last_time, rcs, last_req, int(num)) )
							title2 =_("(Show only reader:") + "%s )" % self.reader

		outlist = self.sortData(result, 7, True)
		out = [ ( _("Label"), _("CAID"), _("Channel"), _("ECM avg"), _("ECM last"), _("Status"), _("Last Req."), _("Total") ) ]
		for i in outlist:
			out.append( (i[0], i[1], i[2], i[3], i[4], i[5], i[6], str(i[7])) )

		if HDSKIN:
			self["output"].setStyle("HD")
		else:
			self["output"].setStyle("default")
		self["output"].setList(out)
		title = [ _("Reader Statistics"), title2 ]
		self.setTitle( " ".join(title))

class OscamInfoConfigScreen(Screen, ConfigListScreen):
	def __init__(self, session, msg = None):
		Screen.__init__(self, session)
		self.session = session
		if msg is not None:
			self.msg = "Error:\n%s" % msg
		else:
			self.msg = ""
		self.oscamconfig = [ ]
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["status"] = StaticText(self.msg)
		self["config"] = ConfigList(self.oscamconfig)
		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"red": self.cancel,
			"green": self.save,
			"save": self.save,
			"cancel": self.cancel,
			"ok": self.save,
		}, -2)
		ConfigListScreen.__init__(self, self.oscamconfig, session = self.session)
		self.createSetup()
		config.oscaminfo.userdatafromconf.addNotifier(self.elementChanged, initial_call = False)
		config.oscaminfo.autoupdate.addNotifier(self.elementChanged, initial_call = False)
		self.onLayoutFinish.append(self.layoutFinished)

	def elementChanged(self, instance):
		self.createSetup()
		try:
			self["config"].l.setList(self.oscamconfig)
		except KeyError:
			pass

	def layoutFinished(self):
		self.setTitle(_("Oscam Info - Configuration"))
		self["config"].l.setList(self.oscamconfig)

	def createSetup(self):
		self.oscamconfig = []
		self.oscamconfig.append(getConfigListEntry(_("Read Userdata from oscam.conf"), config.oscaminfo.userdatafromconf))
		if not config.oscaminfo.userdatafromconf.value:
			self.oscamconfig.append(getConfigListEntry(_("Username (httpuser)"), config.oscaminfo.username))
			self.oscamconfig.append(getConfigListEntry(_("Password (httpwd)"), config.oscaminfo.password))
			self.oscamconfig.append(getConfigListEntry(_("IP address"), config.oscaminfo.ip))
			self.oscamconfig.append(getConfigListEntry(_("Port"), config.oscaminfo.port))
		self.oscamconfig.append(getConfigListEntry(_("Automatically update Client/Server View?"), config.oscaminfo.autoupdate))
		if config.oscaminfo.autoupdate.value:
			self.oscamconfig.append(getConfigListEntry(_("Update interval (in seconds)"), config.oscaminfo.intervall))

	def save(self):
		for x in self.oscamconfig:
			x[1].save()
		configfile.save()
		self.close()

	def cancel(self):
		for x in self.oscamconfig:
			x[1].cancel()
		self.close()
