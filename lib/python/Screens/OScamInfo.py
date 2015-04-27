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

fb = getDesktop(0).size()
if fb.width() > 1024:
	sizeH = fb.width() - 100
	HDSKIN = True
else:
	# sizeH = fb.width() - 50
	sizeH = 700
	HDSKIN = False

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
		CAID_SRVID: "CAID:SrvID", SRVNAME: _("Serv.Name"),
		ECMTIME: _("ECM-Time"), IP_PORT: _("IP address") }
	version = ""

	def confPath(self):
		#search_dirs = [ "/usr", "/var", "/etc" ]
		#sdirs = " ".join(search_dirs)
		#cmd = 'find %s -name "oscam.conf"' % sdirs
		#res = os.popen(cmd).read()
		#if res == "":
		#	return None
		#else:
		#	return res.replace("\n", "")
		cmd = 'ps -eo command | sort -u | grep -v "grep" | grep -c "oscam"'
		res = os.popen(cmd).read()
		if res:
			data = res.replace("\n", "")
			if int(data) == 1:
				cmd = 'ps -eo command | sort -u | grep -v "grep" | grep "oscam"'
				res = os.popen(cmd).read()
				if res:
					data = res.replace("\n", "")
					data = res.replace("--config-dir ", "-c ")
					binary = res.split(" ")[0]
					try:
						data = data.split("-c ")[1]
						data = data.split("-")[0]
					except:
						try:
							print 'OScaminfo - oscam start-command is not as "/oscam-binary -parameter /config-folder" executed, using hard-coded config dir'
							cmd = binary + ' -V | grep ConfigDir'
							res = os.popen(cmd).read()
							data = res.split(":")[1]
						except:
							print 'OScaminfo - oscam binary appears to be broken'
							return None
					data = data.strip() + '/oscam.conf'
					if os.path.exists(data):
						print 'OScaminfo - config file "%s" ' % data
						return data
					print 'OScaminfo - config file "%s" not found' % data
					return None
			elif int(data) > 1:
				print 'OScaminfo - more than one(%s) oscam binarys is active'  % data
				return None
		print 'OScaminfo - no active oscam binarys found'
		return None

	def getUserData(self):
		err = ""
		self.oscamconf = self.confPath()
		self.username = ""
		self.password = ""
		if self.oscamconf is not None:
			data = open(self.oscamconf, "r").readlines()
			webif = False
			httpuser = httppwd = httpport = False
			for i in data:
				if "[webif]" in i.lower():
					webif = True
				elif "httpuser" in i.lower():
					httpuser = True
					user = i.split("=")[1].strip()
				elif "httppwd" in i.lower():
					httppwd = True
					pwd = i.split("=")[1].strip()
				elif "httpport" in i.lower():
					httpport = True
					port = i.split("=")[1].strip()
					self.port = port

			if not webif:
				err = _("There is no [webif] section in oscam.conf")
			elif not httpuser:
				err = _("No httpuser defined in oscam.conf")
			elif not httppwd:
				err = _("No httppwd defined in oscam.conf")
			elif not httpport:
				err = _("No httpport defined in oscam.conf. This value is required!")

			if err != "":
				return err
			else:
				return user, pwd, port
		else:
			return _("file oscam.conf could not be found")

	def openWebIF(self, part = None, reader = None):
		self.proto = "http"
		if config.oscaminfo.userdatafromconf.value:
			self.ip = "127.0.0.1"
			udata = self.getUserData()
			if isinstance(udata, str):
				if "httpuser" in udata:
					self.username=""
				elif "httppwd" in udata:
					self.password = ""
				else:
					return False, udata
			else:
				self.port = udata[2]
				self.username = udata[0]
				self.password = udata[1]
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
			print "[openWebIF] Fehler: %s" % err
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
							ecmtime = "n/a"
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
						srvname_short = "n/A"
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
				self.version = "n/a"
			return self.version
		else:
			self.version = "n/a"
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
								readers.append( ( "%s ( %s Cards )" % (name, cards), name) )
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
					result.append( ("CAID", i.split(":")[1].strip()) )
				elif "pid" in i:
					result.append( ("PID", i.split(":")[1].strip()) )
				elif "prov" in i:
					result.append( (_("Provider"), i.split(":")[1].strip()) )
				elif "reader" in i:
					result.append( ("Reader", i.split(":")[1].strip()) )
				elif "from" in i:
					result.append( (_("Address"), i.split(":")[1].strip()) )
				elif "protocol" in i:
					result.append( (_("Protocol"), i.split(":")[1].strip()) )
				elif "hops" in i:
					result.append( ("Hops", i.split(":")[1].strip()) )
				elif "ecm time" in i:
					result.append( (_("ECM Time"), i.split(":")[1].strip()) )
			return result
		else:
			return "%s not found" % self.ecminfo

class oscMenuList(MenuList):
	def __init__(self, list, itemH = 35):
		MenuList.__init__(self, list, False, eListboxPythonMultiContent)
		self.l.setItemHeight(itemH)
		screenwidth = getDesktop(0).size().width()
		self.l.setFont(0, gFont("Regular", 20))
		self.l.setFont(1, gFont("Regular", 18))
		self.clientFont = gFont("Regular", 16)
		self.l.setFont(2, self.clientFont)
		self.l.setFont(3, gFont("Regular", 12))
		self.l.setFont(4, gFont("Regular", 30))
		self.l.setFont(5, gFont("Regular", 27))
		self.clientFont1080 = gFont("Regular", 24)
		self.l.setFont(6, self.clientFont1080)
		self.l.setFont(7, gFont("Regular", 24))

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
		if entry == 0:
			if os.path.exists("/tmp/ecm.info"):
				self.session.open(oscECMInfo)
			else:
				pass
		elif entry == 1:
			if config.oscaminfo.userdatafromconf.value:
				if self.osc.confPath() is None:
					config.oscaminfo.userdatafromconf.setValue(False)
					config.oscaminfo.userdatafromconf.save()
					self.session.openWithCallback(self.ErrMsgCallback, MessageBox, _("File oscam.conf not found.\nPlease enter username/password manually."), MessageBox.TYPE_ERROR)
				else:
					self.session.open(oscInfo, "c")
			else:
				self.session.open(oscInfo, "c")
		elif entry == 2:
			if config.oscaminfo.userdatafromconf.value:
				if self.osc.confPath() is None:
					config.oscaminfo.userdatafromconf.setValue(False)
					config.oscaminfo.userdatafromconf.save()
					self.session.openWithCallback(self.ErrMsgCallback, MessageBox, _("File oscam.conf not found.\nPlease enter username/password manually."), MessageBox.TYPE_ERROR)
				else:
					self.session.open(oscInfo, "s")
			else:
				self.session.open(oscInfo, "s")
		elif entry == 3:
			if config.oscaminfo.userdatafromconf.value:
				if self.osc.confPath() is None:
					config.oscaminfo.userdatafromconf.setValue(False)
					config.oscaminfo.userdatafromconf.save()
					self.session.openWithCallback(self.ErrMsgCallback, MessageBox, _("File oscam.conf not found.\nPlease enter username/password manually."), MessageBox.TYPE_ERROR)
				else:
					self.session.open(oscInfo, "l")
			else:
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
				reader.append( ("All", "all") )
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
		screenwidth = getDesktop(0).size().width()
		keys = ["red", "green", "yellow", "blue", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", ""]
		menuentries = []
		y = 0
		for x in mlist:
			res = [ x ]
			if x.startswith("--"):
				#png = LoadPixmap("/usr/share/enigma2/skin_default/div-h.png")
				png = resolveFilename(SCOPE_ACTIVE_SKIN, "div-h.png")
				if fileExists(png):
					png = LoadPixmap(png)
				if png is not None:
					if screenwidth and screenwidth == 1920:
						res.append((eListboxPythonMultiContent.TYPE_PIXMAP, 15,2,540, 2, png))
						res.append((eListboxPythonMultiContent.TYPE_TEXT, 68, 5, 1600, 45, 4, RT_HALIGN_LEFT, x[2:]))
					else:
						res.append((eListboxPythonMultiContent.TYPE_PIXMAP, 10,0,360, 2, png))
						res.append((eListboxPythonMultiContent.TYPE_TEXT, 45, 3, 800, 30, 0, RT_HALIGN_LEFT, x[2:]))
					#png2 = LoadPixmap("/usr/share/enigma2/skin_default/buttons/key_" + keys[y] + ".png")
					png2 = resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/key_" + keys[y] + ".png")
					if fileExists(png2):
						png2 = LoadPixmap(png2)
					if png2 is not None:
						if screenwidth and screenwidth == 1920:
							res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, 8, 2, 45, 45, png2))
						else:
							res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 5, 0, 30, 30, png2))
			else:
				if screenwidth and screenwidth == 1920:
					res.append((eListboxPythonMultiContent.TYPE_TEXT, 68, 2, 1600, 45, 4, RT_HALIGN_LEFT, x))
				else:
					res.append((eListboxPythonMultiContent.TYPE_TEXT, 45, 0, 800, 30, 0, RT_HALIGN_LEFT, x))
				#png2 = LoadPixmap("/usr/share/enigma2/skin_default/buttons/key_" + keys[y] + ".png")
				png2 = resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/key_" + keys[y] + ".png")
				if fileExists(png2):
					png2 = LoadPixmap(png2)
				if png2 is not None:
					if screenwidth and screenwidth == 1920:
						res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, 8, 2, 45, 45, png2))
					else:
						res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 5, 0, 30, 30, png2))
			menuentries.append(res)
			if y < len(keys) - 1:
				y += 1
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
		screenwidth = getDesktop(0).size().width()
		if screenwidth and screenwidth == 1920:
			return [
				None,
				(eListboxPythonMultiContent.TYPE_TEXT, 15, 3, 450, 45, 4, RT_HALIGN_LEFT, listentry[0]),
				(eListboxPythonMultiContent.TYPE_TEXT, 450, 3, 450, 45, 4, RT_HALIGN_LEFT, listentry[1])
				]
		else:
			return [
				None,
				(eListboxPythonMultiContent.TYPE_TEXT, 10, 2, 300, 30, 0, RT_HALIGN_LEFT, listentry[0]),
				(eListboxPythonMultiContent.TYPE_TEXT, 300, 2, 300, 30, 0, RT_HALIGN_LEFT, listentry[1])
				]

	def showData(self):
		screenwidth = getDesktop(0).size().width()
		data = self.getECMInfo(self.ecminfo)
		#print data
		out = []
		y = 0
		for i in data:
			out.append(self.buildListEntry(i))
		if screenwidth and screenwidth == 1920:
			self["output"].l.setItemHeight(45)
		else:
			self["output"].l.setItemHeight(30)
		self["output"].l.setList(out)
		self["output"].selectionEnabled(True)

class oscInfo(Screen, OscamInfo):
	def __init__(self, session, what):
		global HDSKIN, sizeH
		self.session = session
		self.what = what
		self.firstrun = True
		self.webif_data = self.readXML(typ = self.what)
		entry_count = len( self.webif_data )
#		entry_count = len(self.readXML(typ = self.what))
		ysize = (entry_count + 4) * 25
		ypos = 10
		self.sizeLH = sizeH - 20
		self.skin = """<screen position="center,center" size="%d, %d" title="Client Info" >""" % (sizeH, ysize / 2)
		button_width = int(sizeH / 4)
		for k, v in enumerate(["red", "green", "yellow", "blue"]):
			xpos = k * button_width
			self.skin += """<ePixmap name="%s" position="%d,%d" size="35,25" pixmap="/usr/share/enigma2/skin_default/buttons/key_%s.png" zPosition="1" transparent="1" alphatest="on" />""" % (v, xpos, ypos, v)
			self.skin += """<widget source="key_%s" render="Label" position="%d,%d" size="%d,%d" font="Regular;18" zPosition="1" valign="center" transparent="1" />""" % (v, xpos + 40, ypos, button_width, 22)
		self.skin +="""<ePixmap name="divh" position="0,37" size="%d,2" pixmap="/usr/share/enigma2/skin_default/div-h.png" transparent="1" alphatest="on" />""" % sizeH
		self.skin +="""<widget name="output" position="10,45" size="%d,%d" zPosition="1" scrollbarMode="showOnDemand" />""" % ( self.sizeLH, ysize / 2)
		self.skin += """</screen>"""
		Screen.__init__(self, session)
		self.mlist = oscMenuList([])
		self["output"] = self.mlist
		self.errmsg = ""
		self["key_red"] = StaticText(_("Close"))
		if self.what == "c":
			self["key_green"] = StaticText("")
			self["key_yellow"] = StaticText("Servers")
			self["key_blue"] = StaticText("Log")
		elif self.what == "s":
			self["key_green"] = StaticText("Clients")
			self["key_yellow"] = StaticText("")
			self["key_blue"] = StaticText("Log")
		elif self.what == "l":
			self["key_green"] = StaticText("Clients")
			self["key_yellow"] = StaticText("Servers")
			self["key_blue"] = StaticText("")
		else:
			self["key_green"] = StaticText("Clients")
			self["key_yellow"] = StaticText("Servers")
			self["key_blue"] = StaticText("Log")
		self.fieldSizes = []
		self.fs2 = {}
		if config.oscaminfo.autoupdate.value:
			self.loop = eTimer()
			self.loop.callback.append(self.showData)
			timeout = config.oscaminfo.intervall.value * 1000
			self.loop.start(timeout, False)
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
					{
						"ok": self.showData,
						"cancel": self.exit,
						"red": self.exit,
						"green": self.key_green,
						"yellow": self.key_yellow,
						"blue": self.key_blue
					}, -1)
		self.onLayoutFinish.append(self.showData)

	def key_green(self):
		if self.what == "c":
			pass
		else:
			self.what = "c"
			self.showData()

	def key_yellow(self):
		if self.what == "s":
			pass
		else:
			self.what = "s"
			self.showData()

	def key_blue(self):
		if self.what == "l":
			pass
		else:
			self.what = "l"
			self.showData()

	def exit(self):
		if config.oscaminfo.autoupdate.value:
			self.loop.stop()
		self.close()

	def buildListEntry(self, listentry, heading = False):
		screenwidth = getDesktop(0).size().width()
		res = [ None ]
		x = 0
		if not HDSKIN:
			self.fieldsize = [ 100, 130, 100, 150, 80, 130 ]
			self.startPos = [ 10, 110, 240, 340, 490, 570 ]
			useFont = 3
		else:
			if screenwidth and screenwidth == 1920:
				self.fieldsize = [ 300, 300, 225, 300, 225, 300 ]
				self.startPos = [ 75, 375, 675, 900, 1200, 1425 ]
				useFont = 6
			else:
				self.fieldsize = [ 200, 200, 150, 200, 150, 200 ]
				self.startPos = [ 50, 250, 450, 600, 800, 950 ]
				useFont = 2

		if isinstance(self.errmsg, tuple):
			if screenwidth and screenwidth == 1920:
				useFont = 4  # overrides previous font-size in case of an error message. (if self.errmsg is a tuple, an error occurred which will be displayed instead of regular results
			else:
				useFont = 0  # overrides previous font-size in case of an error message. (if self.errmsg is a tuple, an error occurred which will be displayed instead of regular results
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
			if screenwidth and screenwidth == 1920:
				res.append( (eListboxPythonMultiContent.TYPE_TEXT, xpos, 0, xsize, 33, useFont, RT_HALIGN_LEFT, i, int(colour, 16)) )
			else:
				res.append( (eListboxPythonMultiContent.TYPE_TEXT, xpos, 0, xsize, 22, useFont, RT_HALIGN_LEFT, i, int(colour, 16)) )
			x += 1
		if heading:
			png = resolveFilename(SCOPE_ACTIVE_SKIN, "div-h.png")
			if fileExists(png):
				png = LoadPixmap(png)
			if png is not None:
				if screenwidth and screenwidth == 1920:
					pos = 37
					res.append( (eListboxPythonMultiContent.TYPE_PIXMAP, 0, pos, self.sizeLH, useFont, png))
				else:
					pos = 24
					res.append( (eListboxPythonMultiContent.TYPE_PIXMAP, 0, pos, self.sizeLH, useFont, png))
		return res

	def buildLogListEntry(self, listentry):
		screenwidth = getDesktop(0).size().width()
		res = [ None ]
		for i in listentry:
			if i.strip() != "" or i is not None:
				if screenwidth and screenwidth == 1920:
					res.append( (eListboxPythonMultiContent.TYPE_TEXT, 8, 0, self.sizeLH,33, 6, RT_HALIGN_LEFT, i) )
				else:
					res.append( (eListboxPythonMultiContent.TYPE_TEXT, 5, 0, self.sizeLH,22, 2, RT_HALIGN_LEFT, i) )
		return res

	def calcSizes(self, entries):
		self.fs2 = {}
		colSize = [ 100, 200, 150, 200, 150, 100 ]
		for h in entries:
			for i, j in enumerate(h[:-1]):
				try:
					self.fs2[i].append(colSize[i])
				except KeyError:
					self.fs2[i] = []
					self.fs2[i].append(colSize[i])
		sizes = []
		for i in self.fs2.keys():
			sizes.append(self.fs2[i])
		return sizes

	def changeScreensize(self, new_height, new_width = None):
		screenwidth = getDesktop(0).size().width()
		if new_width is None:
			new_width = sizeH
		if self.instance.size().height() < new_height:
			self.instance.resize(eSize(new_width, new_height))
			fb = getDesktop(0).size()
			new_posY = int(( fb.height() / 2 ) - ( new_height / 2 ))
			x = int( ( fb.width() - sizeH ) / 2 )
			self.instance.move(ePoint(x, new_posY))
			self["output"].resize(eSize(self.sizeLH, new_height - 55))
		self["key_red"].setText(_("Close"))
		if self.what == "c":
			self["key_green"].setText("")
			self["key_yellow"].setText("Servers")
			self["key_blue"].setText("Log")
			if screenwidth and screenwidth == 1920:
				self["output"].l.setItemHeight(38)
			else:
				self["output"].l.setItemHeight(25)
		elif self.what == "s":
			self["key_green"].setText("Clients")
			self["key_yellow"].setText("")
			self["key_blue"].setText("Log")
			if screenwidth and screenwidth == 1920:
				self["output"].l.setItemHeight(38)
			else:
				self["output"].l.setItemHeight(25)
		elif self.what == "l":
			self["key_green"].setText("Clients")
			self["key_yellow"].setText("Servers")
			self["key_blue"].setText("")
			if screenwidth and screenwidth == 1920:
				self["output"].l.setItemHeight(30)
			else:
				self["output"].l.setItemHeight(20)
		else:
			self["key_green"].setText("Clients")
			self["key_yellow"].setText("Servers")
			self["key_blue"].setText("Log")

	def showData(self):
		if self.firstrun:
			data = self.webif_data
			self.firstrun = False
		else:
			data = self.readXML(typ = self.what)
		if not isinstance(data,str):
			out = []
			if self.what != "l":
				heading = ( self.HEAD[self.NAME], self.HEAD[self.PROT], self.HEAD[self.CAID_SRVID],
						self.HEAD[self.SRVNAME], self.HEAD[self.ECMTIME], self.HEAD[self.IP_PORT], "")
				outlist = [heading]
				for i in data:
					outlist.append( i )
				self.fieldsize = self.calcSizes(outlist)
				out = [ self.buildListEntry(heading, heading=True)]
				for i in data:
					out.append(self.buildListEntry(i))
			else:
				for i in data:
					if i != "":
						out.append( self.buildLogListEntry( (i,) ))
				#out.reverse()
			ysize = (len(out) + 4 ) * 25
			if self.what == "c":
				self.changeScreensize( ysize )
				self.setTitle("Client Info ( Oscam-Version: %s )" % self.getVersion())
			elif self.what == "s":
				self.changeScreensize( ysize )
				self.setTitle("Server Info( Oscam-Version: %s )" % self.getVersion())

			elif self.what == "l":
				self.changeScreensize( 500 )
				self.setTitle("Oscam Log ( Oscam-Version: %s )" % self.getVersion())
			self["output"].l.setList(out)
			self["output"].selectionEnabled(False)
		else:
			self.errmsg = (data,)
			if config.oscaminfo.autoupdate.value:
				self.loop.stop()
			out = []
			self.fieldsize = self.calcSizes( [(data,)] )
			for i in self.errmsg:
				out.append( self.buildListEntry( (i,) ))
			ysize = (len(out) + 4 ) * 25
			self.changeScreensize( ysize )
			self.setTitle(_("Error") + data)
			self["output"].l.setList(out)
			self["output"].selectionEnabled(False)



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
		title = [ _("Reader"), self.cccamreader, _("Cards:"), cardTotal, "Server:", hostadr ]
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
			self.oscamconfig.append(getConfigListEntry("Port", config.oscaminfo.port))
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
