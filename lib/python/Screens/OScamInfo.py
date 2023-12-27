# PYTHON IMPORTS
from datetime import datetime, timezone, timedelta
from json import loads
from dateutil.parser import isoparse
from os.path import exists
from re import search, S
from twisted.internet.reactor import callInThread
from urllib.error import URLError
from urllib.request import build_opener, install_opener, urlopen, HTTPDigestAuthHandler, HTTPHandler, HTTPPasswordMgrWithDefaultRealm, Request

# ENIGMA IMPORTS
from enigma import eTimer
from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.ScrollLabel import ScrollLabel
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Setup import Setup

# GLOBALS
MODULE_NAME = __name__.split(".")[-2]


class OScamGlobals():
	def __init__(self):
		pass

	def openWebIF(self, log=False):
		proto, api = "http", "oscamapi"
		if config.oscaminfo.userDataFromConf.value:
			udata = self.getUserData()
			if isinstance(udata, str):
				return False, udata.encode()
			username, password, port, ipaccess, api = udata
			ip = "::1" if ipaccess == "yes" else "127.0.0.1"
		else:
			ip = ".".join("%d" % d for d in config.oscaminfo.ip.value)
			port = str(config.oscaminfo.port.value)
			username = str(config.oscaminfo.username.value)
			password = str(config.oscaminfo.password.value)
		if port.startswith('+'):
			proto = "https"
			port.replace("+", "")
		style, appendix = ("html", "&appendlog=1") if log else ("json", "")
		url = "%s://%s:%s/%s.%s?part=status%s" % (proto, ip, port, api, style, appendix)
		opener = build_opener(HTTPHandler)
		if username and password:
			pwman = HTTPPasswordMgrWithDefaultRealm()
			pwman.add_password(None, url, username, password)
			handlers = HTTPDigestAuthHandler(pwman)
			opener = build_opener(HTTPHandler, handlers)
			install_opener(opener)
		request = Request(url)
		try:
			data = urlopen(request).read()
			return True, data
		except URLError as error:
			errmsg = str(error)
			if hasattr(error, "reason"):
				errmsg = str(error.reason)
			elif hasattr(error, "errno"):
				errmsg = str(error.errno)
			print("[%s] ERROR in module 'openWebIF': Unexpected error accessing WebIF: %s" % (MODULE_NAME, errmsg))
			return False, errmsg.encode()

	def confPath(self):
		owebif, oport, opath, ipcompiled, conffile = False, None, None, False, ""
		for file in ["/tmp/.ncam/ncam.version", "/tmp/.oscam/oscam.version"]:  # Find and parse running oscam
			if exists(file):
				with open(file) as data:
					conffile = file.split('/')[-1].replace("version", "conf")
					for i in data:
						if "web interface support:" in i.lower():
							owebif = {"no": False, "yes": True}.get(i.split(":")[1].strip(), False)
						elif "webifport:" in i.lower():
							oport = i.split(":")[1].strip()
							if oport == "0":
								oport = None
						elif "configdir:" in i.lower():
							opath = i.split(":")[1].strip()
						elif "ipv6 support:" in i.lower():
							ipcompiled = {"no": False, "yes": True}.get(i.split(":")[1].strip())
						else:
							continue
		return owebif, oport, opath, ipcompiled, conffile

	def getUserData(self):
		webif, port, conf, ipcompiled, conffile = self.confPath()  # (True, '8080', '/etc/tuxbox/config/oscam-trunk/', True, 'oscam.conf')
		conf = "%s%s" % ((conf or ""), (conffile or "oscam.conf"))
		api = conffile.replace(".conf", "api")
		blocked = False  # Assume that oscam webif is NOT blocking localhost, IPv6 is also configured if it is compiled in, and no user and password are required
		ipconfigured = ipcompiled
		user = pwd = None
		ret = _("OScam webif disabled")
		if webif and port is not None:  # oscam reports it got webif support and webif is running (Port != 0)
			if conf is not None and exists(conf):  # If we have a config file, we need to investigate it further
				with open(conf) as data:
					for i in data:
						if "httpuser" in i.lower():
							user = i.split("=")[1].strip()
						elif "httppwd" in i.lower():
							pwd = i.split("=")[1].strip()
						elif "httpport" in i.lower():
							port = i.split("=")[1].strip()
						elif "httpallowed" in i.lower():
							blocked = True  # Once we encounter a httpallowed statement, we have to assume oscam webif is blocking us ...
							allowed = i.split("=")[1].strip()
							if "::1" in allowed or "127.0.0.1" in allowed or "0.0.0.0-255.255.255.255" in allowed:
								blocked = False  # ... until we find either 127.0.0.1 or ::1 in allowed list
							if "::1" not in allowed:
								ipconfigured = False
			if not blocked:
				ret = user, pwd, port, ipconfigured, api
		return ret

	def updateLog(self):
		webifok, result = self.openWebIF(log=True)
		if webifok:
			log = search(r'<log>(.*?)</log>', result.decode().replace("<![CDATA[", "").replace("]]>", ""), S)
			return log.group(1).strip() if log else "<no log found>"


class OScamOverview(Screen, OScamGlobals):
	skin = """
		<screen name="OScamInfoOverview" position="center,center" size="1950,1080" backgroundColor="#10101010" title="OScamInfo Overview" flags="wfNoBorder" resolution="1920,1080">
			<ePixmap pixmap="OscamLogo.png" position="15,15" size="80,80" scale="1" alphatest="blend" />
			<widget source="title" render="Label" position="15,15" size="1920,60" font="Regular;40" halign="center" valign="center" foregroundColor="white" backgroundColor="#10101010" />
			<widget source="global.CurrentTime" render="Label" position="1635,15" size="260,60" font="Regular;40" halign="right" valign="center" foregroundColor="#0092CBDF" backgroundColor="#10101010">
				<convert type="ClockToText">Format:%H:%M:%S</convert>
			</widget>
			<widget source="timerinfos" render="Label" position="15,72" size="1920,40" font="Regular;28" halign="center" valign="center" foregroundColor="white" backgroundColor="#10101010" />
			<widget source="buildinfos" render="Label" position="15,105" size="1920,40" font="Regular;28" halign="center" valign="center"  foregroundColor="#092CBDF" backgroundColor="#10101010" />
			<!-- Server / Reader / Clients -->
			<eLabel text="#" position="15,150" size="23,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#1B3C85" />
			<eLabel text="Reader/User" position="40,150" size="173,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#1B3C85" />
			<eLabel text="AU" position="215,150" size="88,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#1B3C85" />
			<eLabel text="Address" position="305,150" size="168,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#1B3C85" />
			<eLabel text="Port" position="475,150" size="88,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#1B3C85" />
			<eLabel text="Protocol" position="565,150" size="288,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#1B3C85" />
			<eLabel text="srvid:caid@provid" position="855,150" size="238,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#1B3C85" />
			<eLabel text="Last Channel" position="1095,150" size="278,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#1B3C85" />
			<eLabel text="LB Value/Reader" position="1375,150" size="218,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#1B3C85" />
			<eLabel text="Online\nIdle" position="1595,150" size="138,58" font="Regular;24" halign="center" valign="center" foregroundColor="white" backgroundColor="#1B3C85" />
			<eLabel text="Status" position="1735,150" size="170,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#1B3C85" />
			<widget source="outlist" render="Listbox" position="15,210" size="1890,600" backgroundColor="grey" backgroundColorSelected="grey" scrollbarMode="showOnDemand" >
				<convert type="TemplatedMultiContent">
					{"template": [ # index 11 is backcolor
					MultiContentEntryText(pos=(0,0), size=(23,60), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, color_sel=0x000000, backcolor=MultiContentTemplateColor(11), backcolor_sel=MultiContentTemplateColor(11), text=0),  # type
					MultiContentEntryText(pos=(25,0), size=(173,60), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, color_sel=0x000000, backcolor=MultiContentTemplateColor(11), backcolor_sel=MultiContentTemplateColor(11), text=1),  # Reader/User
					MultiContentEntryText(pos=(200,0), size=(88,60), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, color_sel=0x000000, backcolor=MultiContentTemplateColor(11), backcolor_sel=MultiContentTemplateColor(11), text=2),  # AU
					MultiContentEntryText(pos=(290,0), size=(168,60), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, color_sel=0x000000, backcolor=MultiContentTemplateColor(11), backcolor_sel=MultiContentTemplateColor(11), text=3),  # Adress
					MultiContentEntryText(pos=(460,0), size=(88,60), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, color_sel=0x000000, backcolor=MultiContentTemplateColor(11), backcolor_sel=MultiContentTemplateColor(11), text=4),  # Port
					MultiContentEntryText(pos=(550,0), size=(288,60), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER|RT_WRAP, color=0x000000, color_sel=0x000000, backcolor=MultiContentTemplateColor(11), backcolor_sel=MultiContentTemplateColor(11), text=5),  # Protocol
					MultiContentEntryText(pos=(840,0), size=(238,60), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, color_sel=0x000000, backcolor=MultiContentTemplateColor(11), backcolor_sel=MultiContentTemplateColor(11), text=6),  # srvid:caid@provid
					MultiContentEntryText(pos=(1080,0), size=(278,60), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER|RT_WRAP, color=0x000000, color_sel=0x000000, backcolor=MultiContentTemplateColor(11), backcolor_sel=MultiContentTemplateColor(11), text=7),  # Last Channel
					MultiContentEntryText(pos=(1360,0), size=(218,60), font=1, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, color_sel=0x000000, backcolor=MultiContentTemplateColor(11), backcolor_sel=MultiContentTemplateColor(11), text=8),  # LB Value/Reader
					MultiContentEntryText(pos=(1580,0), size=(138,60), font=1, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER|RT_WRAP, color=0x000000, color_sel=0x000000, backcolor=MultiContentTemplateColor(11), backcolor_sel=MultiContentTemplateColor(11), text=9),  # Online+Idle
					MultiContentEntryText(pos=(1720,0), size=(170,60), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, color_sel=0x000000, backcolor=MultiContentTemplateColor(11), backcolor_sel=MultiContentTemplateColor(11), text=10)  # Status
					], "fonts": [gFont("Regular",21),gFont("Regular",18)], "itemHeight":60
					}
				</convert>
			</widget>
			<widget name="logtext" position="15,812" size="1890,150" font="Regular;24" halign="left" valign="top" foregroundColor="black" backgroundColor="#ECEAF6" noWrap="0" scrollbarMode="showNever" />
			<eLabel text="System Ram" position="15,964" size="148,42" font="Regular;27" halign="center" valign="center" foregroundColor="#FFFF30" backgroundColor="#1B3C85" />
			<widget source="total" render="Label" position="165,964" size="228,42" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#1B3C85" />
			<widget source="used" render="Label" position="395,964" size="228,42" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#1B3C85" />
			<widget source="free" render="Label" position="625,964" size="228,42" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#1B3C85" />
			<widget source="buffer" render="Label" position="855,964" size="228,42" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#1B3C85" />
			<eLabel text="OScam" position="1085,964" size="148,42" font="Regular;27" valign="center" halign="center" foregroundColor="#FFFF30" backgroundColor="#1B3C85" />
			<widget source="virtuell" render="Label" position="1235,964" size="338,42" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#1B3C85" />
			<widget source="resident" render="Label" position="1575,964" size="330,42" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#1B3C85" />
			<eLabel name="blue" position="1260,1010" size="10,65" backgroundColor="blue" zPosition="1" />
			<widget source="key_blue" render="Label" position="1280,1020" size="380,42" font="Regular;30" halign="left" valign="center" foregroundColor="grey" />
			<widget source="key_menu" render="Label" position="1530,1020" size="150,42" font="Regular;30" halign="center" valign="center" foregroundColor="black" backgroundColor="grey" />
			<widget source="key_exit" render="Label" position="1730,1020" size="150,42" font="Regular;30" halign="center" valign="center" foregroundColor="black" backgroundColor="grey" />
		</screen>
		"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "OScamInfoOverview"
		self.setTitle(_("OScamInfo Overview"))
		self["title"] = StaticText(_("OScamInfo Overview"))
		self["timerinfos"] = StaticText()
		self["buildinfos"] = StaticText()
		self["outlist"] = List([])
		self["logtext"] = ScrollLabel(_("<no log found"))
		self["total"] = StaticText()
		self["used"] = StaticText()
		self["free"] = StaticText()
		self["buffer"] = StaticText()
		self["virtuell"] = StaticText()
		self["resident"] = StaticText()
		self["key_blue"] = StaticText(_("Show Log"))
		self["key_menu"] = StaticText(_("Menu"))
		self["key_exit"] = StaticText(_("Exit"))
		self["actions"] = HelpableActionMap(self, ["NavigationActions", "OkCancelActions", "ColorActions", "MenuActions"], {
			"ok": (self.exit, _("Close the screen")),
			"cancel": (self.exit, _("Close the screen")),
			"pageUp": (self.keyPageUp, _("Move up a page")),
			"up": (self.keyPageUp, _("Move up a page")),
			"down": (self.keyPageDown, _("Move down a page")),
			"pageDown": (self.keyPageDown, _("Move down a page")),
			"menu": (self.keyMenu, _("Open Settings")),
			"blue": (self.keyBlue, _("Open Log"))
		}, prio=1, description=_("OScamOverview Actions"))
		self.loop = eTimer()
		self.loop.callback.append(self.updateOScamData)
		self.onLayoutFinish.append(self.onLayoutFinished)

	def onLayoutFinished(self):
		if config.oscaminfo.userDataFromConf.value and self.confPath()[0] is None:
			config.oscaminfo.userDataFromConf.value = False
			config.oscaminfo.userDataFromConf.save()
			self.session.openWithCallback(self.ErrMsgCallback, MessageBox, _("File oscam.conf not found.\nPlease enter username/password manually."), MessageBox.TYPE_ERROR, timeout=5, close_on_any_key=True)
		else:
			callInThread(self.updateOScamData)
			if config.oscaminfo.autoUpdate.value:
				self.loop.start(config.oscaminfo.autoUpdate.value * 1000, False)

	def updateOScamData(self):
		webifok, jsonfull = self.openWebIF()
		if webifok and jsonfull:
			oscam = loads(jsonfull).get("oscam", {})
			sysinfo = oscam.get("sysinfo", {})
			totals = oscam.get("totals", {})
			ctime = isoparse(datetime.now(timezone.utc).astimezone().isoformat())
			currtime = "Current Time: %s - %s" % (ctime.strftime("%x"), ctime.strftime("%X"))
			# GENERAL INFOS (timing, memory usage)
			stime_iso = oscam.get("starttime", None)
			starttime = "Start Time: %s - %s" % (isoparse(stime_iso).strftime("%x"), isoparse(stime_iso).strftime("%X")) if stime_iso else (_("n/a"), _("n/a"))
			runtime = "OScam Run Time: %s" % oscam.get("runtime", _("n/a"))
			version = "OScam: %s" % (oscam.get("version", _("n/a")))
			srvidfile = "srvidfile: %s" % oscam.get("srvidfile", _("n/a"))
			# MAIN INFOS {'s': 'server', 'h': 'http', 'p': 'proxy', 'r': 'reader', 'c': 'cccam_ext', 'x': 'cache exchange', 'm': 'monitor')
			outlist = []
			for client in oscam.get("status", {}).get("client", []):
				connection = client.get("connection", {})
				request = client.get("request", {})
				times = client.get("times", {})
				currtype = client.get("type", "")
				readeruser = {"s": "root", "h": "root", "p": client.get("rname_enc", ""), "r": client.get("rname_enc", ""), "c": client.get("name_enc", "")}.get(currtype, _("n/a"))
				au = {"-1": "ON", "0": "OFF", "1": "ACTIVE"}.get(client.get("au", _("n/a")), _("n/a"))
				ip = connection.get("ip", "")
				if ip and config.softcam.hideServerName.value:
					ip = "".join(["\u2022"] * len(ip))
				ip = ip or _("n/a")
				port = connection.get("port", _("n/a"))
				protocol = client.get("protocol", "")
				srinfo = "%s:%s@%s" % (request.get("srvid", _("n/a")), request.get("caid", _("n/a")), request.get("provid", _("n/a")))
				chinfo = "%s %s" % (request.get("chname", _("n/a")), request.get("chprovider", _("n/a")))
				answered = request.get("answered", "")
				if answered and config.softcam.hideServerName.value:
					answered = "".join(["\u2022"] * len(answered))
				answered = answered or _("n/a")
				ecmtime = request.get("ecmtime", _("n/a"))
				lbvaluereader = "%s (%s ms)" % (answered, ecmtime) if answered and ecmtime else request.get("lbvalue", _("n/a"))
				login_iso = times.get("login")
				loginfmt = isoparse(login_iso).strftime("%X").replace(" days", "d").replace(" day", "d") if login_iso else _("n/a")
				idle_iso = times.get("idle")
				loginfmt += "\n%s" % (timedelta(seconds=float(idle_iso)) if idle_iso else _("n/a"))
				status = connection.get("status", _("n/a"))
				totentitlements = connection.get("totentitlements", _("n/a"))
				if currtype in ["p", "r"]:
					status += "\n(%s entitlements)" % totentitlements if totentitlements else "\n(%s of %s card)" % (totals.get("total_active_readers", "?"), totals.get("total_readers", "?"))
				bgcolor = {"s": 0xe1e0ee, "h": 0xe1e0ee, "p": 0xfef2e6, "r": 0xfff3e7, "c": 0xf0f4e5}.get(currtype, 0xcbcbc)
				outlist.append((currtype, readeruser, au, ip, port, protocol, srinfo, chinfo, lbvaluereader, loginfmt, status, bgcolor))
			outlist.sort(key=lambda val: {"s": 0, "h": 1, "p": 2, "r": 3, "c": 4, "a": 5}[val[0]])  # sort according column 'client type' by customized sort order
			self["timerinfos"].setText("%s | %s | %s" % (currtime, starttime, runtime))
			self["buildinfos"].setText("%s | %s" % (version, srvidfile))
			self["total"].setText("Total: %s" % sysinfo.get("mem_cur_total", _("n/a")))
			self["used"].setText("Used: %s" % sysinfo.get("mem_cur_used", _("n/a")))
			self["free"].setText("Free: %s" % sysinfo.get("mem_cur_free", _("n/a")))
			self["buffer"].setText("Buffer: %s" % sysinfo.get("mem_cur_buff", _("n/a")))
			self["virtuell"].setText("Virtuell memory: %s" % sysinfo.get("oscam_vmsize", _("n/a")))
			self["resident"].setText("Resident Set: %s" % sysinfo.get("oscam_rsssize", _("n/a")))
			self["outlist"].updateList(outlist)
			self.displayLog()

	def displayLog(self):
		logtext = self.updateLog()
		if logtext:
			self["logtext"].setText(logtext)
			self["logtext"].moveBottom()

	def keyPageDown(self):
		self["outlist"].pageDown()

	def keyPageUp(self):
		self["outlist"].pageUp()

	def keyMenu(self):
		def keyMenuCallback():
			self.loop.stop()
			if config.oscaminfo.autoUpdate.value:
				self.loop.start(config.oscaminfo.autoUpdate.value * 1000, False)
		self.session.openWithCallback(keyMenuCallback, OScamInfoSetup)

	def keyBlue(self):
		def keyBlueCallback():
			if config.oscaminfo.autoUpdate.value:
				self.loop.start(config.oscaminfo.autoUpdate.value * 1000, False)
		self.loop.stop()
		self.session.openWithCallback(keyBlueCallback, OScamShowLog)

	def exit(self):
		self.loop.stop()
		self.close()


class OScamShowLog(Screen, OScamGlobals):
	skin = """
		<screen name="OScamShowLog" position="center,center" size="1950,1080" backgroundColor="#10101010" title="OScamInfo ShowLog" flags="wfNoBorder" resolution="1920,1080">
			<widget source="title" render="Label" position="15,15" size="1920,60" font="Regular;40" halign="center" valign="center" foregroundColor="white" backgroundColor="#10101010" />
			<widget source="global.CurrentTime" render="Label" position="1635,15" size="260,60" font="Regular;40" halign="right" valign="center" foregroundColor="#0092CBDF" backgroundColor="#10101010">
				<convert type="ClockToText">Format:%H:%M:%S</convert>
			</widget>
			<widget name="logtext" position="15,70" size="1880,995" font="Regular;24" halign="left" valign="top" foregroundColor="black" backgroundColor="#ECEAF6" noWrap="0" scrollbarMode="showOnDemand" />
		</screen>
		"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "OScamInfoShowLog"
		self.setTitle(_("OScamInfo ShowLog"))
		self["title"] = StaticText(_("OScamInfo ShowLog"))
		self["logtext"] = ScrollLabel(_("<no log found"))
		self["actions"] = HelpableActionMap(self, ["NavigationActions", "OkCancelActions"], {
			"ok": (self.exit, _("Close the screen")),
			"cancel": (self.exit, _("Close the screen")),
			"pageUp": (self.keyPageUp, _("Move up a page")),
			"up": (self.keyPageUp, _("Move up a page")),
			"down": (self.keyPageDown, _("Move down a page")),
			"pageDown": (self.keyPageDown, _("Move down a page"))
		}, prio=1, description=_("OScamLog Actions"))
		self.loop = eTimer()
		self.loop.callback.append(self.displayLog)
		self.onLayoutFinish.append(self.onLayoutFinished)

	def onLayoutFinished(self):
		if config.oscaminfo.autoUpdateLog.value:
			self.loop.start(config.oscaminfo.autoUpdateLog.value * 1000, False)
		callInThread(self.displayLog)

	def displayLog(self):
		logtext = self.updateLog()
		if logtext:
			self["logtext"].setText(logtext)
			self["logtext"].moveBottom()

	def keyPageDown(self):
		self["logtext"].pageDown()

	def keyPageUp(self):
		self["logtext"].pageUp()

	def exit(self):
		self.loop.stop()
		self.close()


class OScamInfoSetup(Setup):
	def __init__(self, session, msg=None):   # TODO Was ist das msg?
		Setup.__init__(self, session, setup="OScamOverview")
		self.setTitle(_("OScamInfo Settings"))
		self.msg = msg
		if self.msg:
			self.msg = "Error:\n%s" % self.msg

	def layoutFinished(self):
		Setup.layoutFinished(self)
		if self.msg:
			self.setFootnote(self.msg)
			self.msg = None


class OscamInfoMenu(OScamOverview):  # ToDo: startup-classname for the moment, replace later by 'class OScamOverview'
	def __init__(self, session):
		OScamOverview.__init__(self, session)
