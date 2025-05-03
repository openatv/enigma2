# PYTHON IMPORTS
from datetime import datetime, timezone, timedelta
from json import loads
from os.path import exists
from re import compile
from twisted.internet.reactor import callInThread
from ssl import create_default_context, _create_unverified_context as SkipCertificateVerification
from urllib.parse import unquote
from urllib.request import build_opener, HTTPDigestAuthHandler, HTTPHandler, HTTPSHandler, HTTPPasswordMgrWithDefaultRealm
from pathlib import Path
from xml.etree.ElementTree import XML, ParseError
from ipaddress import ip_address
from socket import getaddrinfo, gaierror

# ENIGMA IMPORTS
from enigma import eTimer
from skin import parameters
from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.ScrollLabel import ScrollLabel
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import BoxInfo
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Setup import Setup
from Tools.BoundFunction import boundFunction

# GLOBALS
MODULE_NAME = __name__.split(".")[-1]


class OSCamGlobals():
	def __init__(self):
		pass

	def openWebIF(self, part="status", label="", fmt="json", log=False):
		udata = self.getUserData()
		if isinstance(udata, str):
			return False, None, None, None, udata.encode()
		proto, ip, port, user, pwd, api, signstatus = udata
		webifok, url, result = self.callApi(proto=proto, ip=ip, port=port,
						username=user, password=pwd, api=api,
						fmt=fmt, part=part, label=label, log=log)
		return webifok, api, url, signstatus, result

	def confPath(self):
		cam, api = "ncam", "api"
		webif = ipv6compiled = False
		port = signstatus = data = error = conffile = url = verfile = None
		cam = cam if cam in BoxInfo.getItem("CurrentSoftcam").split("/")[-1].lower() else "oscam"
		verfilename = "%s.version" % cam
		api = "%s%s" % (cam, api)
		if config.oscaminfo.userDataFromConf.value:  # Find and parse running oscam, ncam (auto)
			verfile = "/tmp/.%s/%s" % (verfilename.split('.')[0], verfilename)
			if exists(verfile):
				data = Path(verfile).read_text()
		else:  # Find and parse running oscam, ncam (api)
			webifok, url, result = self.callApi(proto="https" if config.oscaminfo.usessl.value else "http",
												ip=str(config.oscaminfo.ip.value),
												port=str(config.oscaminfo.port.value),
												username=str(config.oscaminfo.username.value),
												password=str(config.oscaminfo.password.value),
												api=api, fmt="html", part="files", label=verfilename)
			result = result.decode(encoding="latin-1", errors="ignore")
			if webifok:
				try:
					xml = XML(result).find("file")
					data = xml.text.strip() if xml is not None else None
				except ParseError:
					pass
			else:
				error = result

		if data:
			for i in data.splitlines():
				if "web interface support:" in i.lower():
					webif = {"no": False, "yes": True}.get(i.split(":")[1].strip(), False)
				elif "webifport:" in i.lower():
					port = i.split(":")[1].strip()
					if port == "0":
						port = None
				elif "configdir:" in i.lower():
					conffile = "%s%s" % (i.split(":")[1].strip(), verfilename.replace("version", "conf"))
				elif "ipv6 support:" in i.lower():
					ipv6compiled = {"no": False, "yes": True}.get(i.split(":")[1].strip())
				elif "signature:" in i.lower():
					signstatus = i.split(":")[1].strip()
				elif "subject:" in i.lower():
					signstatus = "%s (%s)" % (i.split(":")[1].strip(), signstatus)
				else:
					continue
		else:
			error = "unexpected result from %s%s" % ((verfile or ""), (url or "")) if not error else error
		return webif, port, api, ipv6compiled, signstatus, conffile, error

	def getUserData(self):
		ret = _("No system softcam configured!")
		if BoxInfo.getItem("ShowOscamInfo"):
			webif, port, api, ipv6compiled, signstatus, conffile, error = self.confPath()  # (True, 'http', '127.0.0.1', '8080', '/etc/tuxbox/config/oscam-trunk/', True, 'CN=...', 'oscam.conf', None)
			ip, proto, blocked = "127.0.0.1", "http", False  # Assume that oscam webif is NOT blocking localhost, IPv6 is also configured if it is compiled in, and no user and password are required
			user = pwd = None
			conffile = "%s" % (conffile or "oscam.conf")
			ret = _("OSCam webif disabled") if not error else error
			if webif and port is not None:  # oscam reports it got webif support and webif is running (Port != 0)
				if config.oscaminfo.userDataFromConf.value:  # Find and parse running oscam, ncam (auto)
					if conffile is not None and exists(conffile):  # If we have a config file, we need to investigate it further
						with open(conffile) as data:
							for i in data:
								if "httpuser" in i.lower():
									user = i.split("=")[1].strip()
								elif "httppwd" in i.lower():
									pwd = i.split("=")[1].strip()
								elif "httpport" in i.lower():
									port = i.split("=")[1].strip()
									if port.startswith('+'):
										proto = "https"
										port = port.replace("+", "")
								elif "httpallowed" in i.lower():
									blocked = True  # Once we encounter a httpallowed statement, we have to assume oscam webif is blocking us ...
									allowed = i.split("=")[1].strip()
									if "::1" in allowed or "127.0.0.1" in allowed or "0.0.0.0-255.255.255.255" in allowed:
										blocked = False  # ... until we find either 127.0.0.1 or ::1 in allowed list
										ip = "::1" if ipv6compiled else "127.0.0.1"
									if "::1" not in allowed:
										ip = "127.0.0.1"
				else:  #Use custom defined parameters
					proto = proto = "https" if config.oscaminfo.usessl.value else "http"
					ip = str(config.oscaminfo.ip.value)
					port = str(config.oscaminfo.port.value)
					user = str(config.oscaminfo.username.value)
					pwd = str(config.oscaminfo.password.value)
				if not blocked:
					ret = proto, ip, port, user, pwd, api, signstatus
		return ret

	def callApi(self, proto="http", ip="127.0.0.1", port="83", username=None, password=None, api="oscamapi", fmt="json", part="status", label="", log=False):
		webhandler = HTTPHandler if proto == "http" else HTTPSHandler(context=(create_default_context() if config.oscaminfo.verifycert.value else SkipCertificateVerification()))  # NOSONAR silence S4830 + S5527
		if part in ["status", "userstats"]:
			style, appendix = ("html", "&appendlog=1") if log else (fmt, "")
			url = "%s://%s:%s/%s.%s?part=status%s" % (proto, ip, port, api, style, appendix)  # e.g. http://127.0.0.1:8080/oscamapi.html?part=status&appendlog=1
		elif part in ["restart", "shutdown"]:
			url = "%s://%s:%s/shutdown.html?action=%s" % (proto, ip, port, part)  # e.g. http://127.0.0.1:8080//shutdown.html?action=restart or ...?action=shutdown
		elif label:
			key = "file" if part == "files" else "label"                                            # e.g. http://127.0.0.1:8080/oscamapi.html?part=files&file=oscam.conf
			url = "%s://%s:%s/%s.%s?part=%s&%s=%s" % (proto, ip, port, api, fmt, part, key, label)  # e.g. http://127.0.0.1:8080/oscamapi.json?part=entitlement&label=MyReader
		opener = build_opener(webhandler)
		if username and password and url:
			pwman = HTTPPasswordMgrWithDefaultRealm()
			pwman.add_password(None, url, username, password)
			authhandler = HTTPDigestAuthHandler(pwman)
			opener = build_opener(webhandler, authhandler)
		try:
			#print("[%s] DEBUG in module 'callApi': API call: %s" % (MODULE_NAME, url))
			data = opener.open(url, timeout=5).read()
			return True, url, data
		except (OSError, UnicodeError) as error:
			if hasattr(error, "reason"):
				errmsg = str(error.reason)
			elif hasattr(error, "errno"):
				errmsg = str(error.errno)
			else:
				errmsg = str(error)
			print("[%s] ERROR in module 'callApi': Unexpected error accessing WebIF: %s" % (MODULE_NAME, errmsg))
			return False, url, errmsg.encode(encoding="latin-1", errors="ignore")

	def updateLog(self):
		webifok, api, url, signstatus, result = self.openWebIF(log=True)
		ret, result = False, result.decode(encoding="latin-1", errors="ignore")
		if webifok:
			try:
				xml = XML(result).find("log")
				ret, result = True, xml.text.strip() if xml is not None else "<no log found>"
			except ParseError:
				pass
		return ret, result


class OSCamInfo(Screen, OSCamGlobals):
	skin = """
		<screen name="OSCamInfo" position="center,center" size="1950,1080" backgroundColor="#10101010" title="OSCam Information" flags="wfNoBorder" resolution="1920,1080">
			<ePixmap pixmap="icons/OscamLogo.png" position="15,15" size="80,80" scale="1" alphatest="blend" />
			<widget source="Title" render="Label" position="15,15" size="1905,60" font="Regular;40" halign="center" valign="center" foregroundColor="white" backgroundColor="#10101010" />
			<widget source="global.CurrentTime" render="Label" position="1710,15" size="210,90" font="Regular;75" noWrap="1" halign="center" valign="bottom" foregroundColor="#00FFFFFF" backgroundColor="#1A0F0F0F" transparent="1">
				<convert type="ClockToText">Default</convert>
			</widget>
			<widget source="global.CurrentTime" render="Label" position="1470,15" size="240,40" font="Regular;24" noWrap="1" halign="right" valign="bottom" foregroundColor="#00FFFFFF" backgroundColor="#1A0F0F0F" transparent="1">
				<convert type="ClockToText">Format:%A</convert>
			</widget>
			<widget source="global.CurrentTime" render="Label" position="1470,51" size="240,40" font="Regular;24" noWrap="1" halign="right" valign="bottom" foregroundColor="#00FFFFFF" backgroundColor="#1A0F0F0F" transparent="1">
				<convert type="ClockToText">Format:%e. %B</convert>
			</widget>
			<widget source="buildinfos" render="Label" position="360,64" size="1200,40" font="Regular;30" halign="center" valign="center" foregroundColor="#092CBDF" backgroundColor="#10101010"/>
			<widget source="extrainfos" render="Label" position="15,102" size="1905,32" font="Regular;26" halign="center" valign="center" foregroundColor="#092CBDF" backgroundColor="#10101010"/>
			<widget source="timerinfos" render="Label" position="15,136" size="1905,34" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#10101010"/>
			<!-- Server / Reader / Clients -->
			<eLabel text="#" position="15,172" size="23,36" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<eLabel text="Reader/User" position="40,172" size="173,36" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<eLabel text="AU" position="215,172" size="88,36" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<eLabel text="Address" position="305,172" size="168,36" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<eLabel text="Port" position="475,172" size="88,36" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<eLabel text="Protocol" position="565,172" size="223,36" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<eLabel text="srvid:caid@provid" position="790,172" size="268,36" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<eLabel text="Last Channel" position="1060,172" size="233,36" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<eLabel text="LB Value/Reader" position="1295,172" size="233,36" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<eLabel text="Online\nIdle" position="1530,172" size="163,36" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<eLabel text="Status" position="1695,172" size="210,36" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<widget source="outlist" render="Listbox" position="15,210" size="1890,600" backgroundColor="#10b3b3b3" enableWrapAround="1" scrollbarMode="showOnDemand" >
				<convert type="TemplatedMultiContent">
					{"template": [  # index 0 is backgroundcolor
					MultiContentEntryText(pos=(0,0), size=(23,75), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=1),  # type
					MultiContentEntryText(pos=(25,0), size=(173,75), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=2),  # Reader/User
					MultiContentEntryText(pos=(200,0), size=(88,75), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=3),  # AU
					MultiContentEntryText(pos=(290,0), size=(168,75), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=4),  # Adress
					MultiContentEntryText(pos=(460,0), size=(88,75), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=5),  # Port
					MultiContentEntryText(pos=(550,0), size=(223,75), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER|RT_WRAP, color=0x000000, backcolor=MultiContentTemplateColor(0), text=6),  # Protocol
					MultiContentEntryText(pos=(775,0), size=(268,75), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=7),  # srvid:caid@provid
					MultiContentEntryText(pos=(1045,0), size=(233,75), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER|RT_WRAP, color=0x000000, backcolor=MultiContentTemplateColor(0), text=8),  # Last Channel
					MultiContentEntryText(pos=(1280,0), size=(233,75), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=9),  # LB Value/Reader
					MultiContentEntryText(pos=(1515,0), size=(163,75), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER|RT_WRAP, color=0x000000, backcolor=MultiContentTemplateColor(0), text=10),  # Online+Idle
					MultiContentEntryText(pos=(1680,0), size=(210,75), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=11)  # Status
					], "fonts": [gFont("Regular",27)], "itemHeight":75
					}
				</convert>
			</widget>
			<widget name="logtext" position="15,812" size="1890,150" font="Regular;24" halign="left" valign="top" foregroundColor="black" backgroundColor="#10ECEAF6" noWrap="0" scrollbarMode="showNever" />
			<eLabel text="System Ram" position="15,964" size="171,42" font="Regular;27" halign="center" valign="center" foregroundColor="#FFFF30" backgroundColor="#105a5a5a" />
			<widget source="total" render="Label" position="188,964" size="228,42" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<widget source="used" render="Label" position="418,964" size="228,42" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<widget source="free" render="Label" position="648,964" size="228,42" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<widget source="buffer" render="Label" position="878,964" size="228,42" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<widget source="camname" render="Label" position="1108,964" size="125,42" font="Regular;27" valign="center" halign="center" foregroundColor="#FFFF30" backgroundColor="#105a5a5a" />
			<widget source="virtuell" render="Label" position="1235,964" size="338,42" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<widget source="resident" render="Label" position="1575,964" size="330,42" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<eLabel name="red" position="20,1010" size="10,65" backgroundColor="red" zPosition="1" />
			<eLabel name="green" position="320,1010" size="10,65" backgroundColor="green" zPosition="1" />
			<eLabel name="blue" position="920,1010" size="10,65" backgroundColor="blue" zPosition="1" />
			<widget source="key_red" render="Label" position="40,1020" size="380,42" font="Regular;30" halign="left" valign="center" foregroundColor="grey" />
			<widget source="key_green" render="Label" position="340,1020" size="380,42" font="Regular;30" halign="left" valign="center" foregroundColor="grey" />
			<widget source="key_blue" render="Label" position="940,1020" size="380,42" font="Regular;30" halign="left" valign="center" foregroundColor="grey" />
			<widget source="key_OK" render="Label" position="1185,1020" size="60,42" font="Regular;30" halign="center" valign="center" foregroundColor="black" backgroundColor="grey">
				<convert type="ConditionalShowHide" />
			</widget>
			<widget source="key_entitlements" render="Label" position="1260,1020" size="250,42" font="Regular;30" halign="left" valign="center" foregroundColor="grey">
				<convert type="ConditionalShowHide" />
			</widget>
			<widget source="key_menu" render="Label" position="1530,1020" size="150,42" font="Regular;30" halign="center" valign="center" foregroundColor="black" backgroundColor="grey" />
			<widget source="key_exit" render="Label" position="1730,1020" size="150,42" font="Regular;30" halign="center" valign="center" foregroundColor="black" backgroundColor="grey" />
		</screen>
		"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "OSCamInfo"
		self.setTitle(_("OSCamInfo: Information"))
		self.rulist = []
		self["buildinfos"] = StaticText()
		self["extrainfos"] = StaticText()
		self["timerinfos"] = StaticText()
		self["outlist"] = List([])
		self["logtext"] = ScrollLabel(_("<no log found>"))
		self["total"] = StaticText()
		self["used"] = StaticText()
		self["free"] = StaticText()
		self["buffer"] = StaticText()
		self["camname"] = StaticText()
		self["virtuell"] = StaticText()
		self["resident"] = StaticText()
		self["key_red"] = StaticText(_("Shutdown OSCam"))
		self["key_green"] = StaticText(_("Restart OSCam"))
		self["key_blue"] = StaticText(_("Show Log"))
		self["key_OK"] = StaticText()
		self["key_entitlements"] = StaticText()
		self["key_menu"] = StaticText(_("Menu"))
		self["key_exit"] = StaticText(_("Exit"))
		self["actions"] = HelpableActionMap(self, ["NavigationActions", "OkCancelActions", "ColorActions", "MenuActions"], {
			"ok": (self.keyOk, _("Show details")),
			"cancel": (self.exit, _("Close the screen")),
			"menu": (self.keyMenu, _("Open Settings")),
			"red": (self.keyShutdown, _("Shutdown OSCam")),
			"green": (self.keyRestart, _("Restart OSCam")),
			"blue": (self.keyBlue, _("Open Log"))
			}, prio=1, description=_("OSCamInfo Actions"))
		self.loop = eTimer()
		self.loop.callback.append(self.updateOScamData)
		self.onLayoutFinish.append(self.onLayoutFinished)
		self.bgColors = parameters.get("OSCamInfoBGcolors", (0x10fcfce1, 0x10f1f6e6, 0x10e2e0ef))

	def onLayoutFinished(self):
		self.showHideKeyOk()
		self["outlist"].onSelectionChanged.append(self.showHideKeyOk)
		if config.oscaminfo.userDataFromConf.value and self.confPath()[0] is None:
			config.oscaminfo.userDataFromConf.value = False
			config.oscaminfo.userDataFromConf.save()
			self["extrainfos"].setText(_("File oscam.conf not found.\nPlease enter username/password manually."))
		else:
			callInThread(self.updateOScamData)
			if config.oscaminfo.autoUpdate.value:
				self.loop.start(config.oscaminfo.autoUpdate.value * 1000, False)

	def updateOScamData(self):
		webifok, api, url, signstatus, result = self.openWebIF()
		ctime = datetime.fromisoformat(datetime.now(timezone.utc).astimezone().isoformat())
		currtime = "Protocol Time: %s - %s" % (ctime.strftime("%x"), ctime.strftime("%X"))
		na = _("n/a")
		tag, camname = {"oscamapi": ("oscam", "OSCam"), "ncamapi": ("ncam", "NCam"), None: (na, na)}.get(api)
		if webifok and result:
			jsonData = loads(result).get(tag, {})
			sysinfo = jsonData.get("sysinfo", {})
			# GENERAL INFOS (timing, memory usage)
			stime_iso = jsonData.get("starttime", None)
			starttime = "Start Time: %s - %s" % (datetime.fromisoformat(stime_iso).strftime("%x"), datetime.fromisoformat(stime_iso).strftime("%X")) if stime_iso else (na, na)
			runtime = "%s Run Time: %s" % (camname, jsonData.get("runtime", na))
			version = "%s: %s" % (camname, jsonData.get("version", na))
			srvidfile = "srvidfile: %s" % jsonData.get("srvidfile", na)
			url = "%s: %s//%s" % (_("Host"), url.split('/')[0], url.split('/')[2])
			signed = "%s: %s" % (_("Signed by"), signstatus) if signstatus else ""
			rulist = []
			# MAIN INFOS {'s': 'server', 'h': 'http', 'p': 'proxy', 'r': 'reader', 'c': 'cccam_ext', 'x': 'cache exchange', 'm': 'monitor'}
			outlist = []
			for client in jsonData.get("status", {}).get("client", []):
				connection = client.get("connection", {})
				request = client.get("request", {})
				times = client.get("times", {})
				currtype = client.get("type", "")
				readeruser = unquote({"s": "root", "h": "root", "p": client.get("rname_enc", ""), "r": client.get("rname_enc", ""), "c": client.get("name_enc", "")}.get(currtype, na))
				au = {"-1": "ON", "0": "OFF", "1": "ACTIVE"}.get(client.get("au", na), na)
				ip = connection.get("ip", "")
				if ip and config.softcam.hideServerName.value:
					ip = "\u2022" * len(ip)
				port = connection.get("port", na)
				protocol = "\n".join(client.get("protocol", "").split(" "))
				srinfo = "%s:%s@%s" % (request.get("srvid", na), request.get("caid", na), request.get("provid", na))
				chinfo = "%s\n%s" % (request.get("chname", na), request.get("chprovider", na))
				answered = request.get("answered", "")
				if answered and config.softcam.hideServerName.value:
					answered = "\u2022" * len(answered)
				ecmtime = request.get("ecmtime", na)
				lbvaluereader = "%s (%s ms)" % (answered, ecmtime) if answered and ecmtime else request.get("lbvalue", na)
				login_iso = times.get("login")
				loginfmt = datetime.fromisoformat(login_iso).strftime("%X").replace(" days", "d").replace(" day", "d") if login_iso else na
				idle_iso = times.get("idle")
				loginfmt += "\n%s" % self.strf_delta(timedelta(seconds=float(idle_iso)) if idle_iso else na)
				status = connection.get("status", na)
				totentitlements = connection.get("totentitlements", "0")
				totentitlements = int(totentitlements) if totentitlements.isdigit() else 0
				entitlements = connection.get("entitlements", [])
				locentitlements = 0
				for entitlement in entitlements:
					value = entitlement.get("locals", "0")
					value = int(value) if value.isdigit() else 0
					locentitlements = max(locentitlements, value)
				maxentitlements = locentitlements
				for entitlement in entitlements:
					for element in ["cccount", "ccchop1", "ccchop2", "ccchopx", "ccccurr", "cccres0", "cccres1", "cccresx", "cccreshare"]:
						value = entitlement.get(element, "0")
						value = int(value) if value.isdigit() else 0
						maxentitlements = max(maxentitlements, value)
				rulist.append((currtype, readeruser, totentitlements or maxentitlements))
				if currtype in ["p", "r"]:
					status += "\n(%s entitlements)" % totentitlements if totentitlements else "\n(%s of %s cards)" % (locentitlements, maxentitlements)
				bgcolor = self.bgColors[{"p": 0, "r": 0, "c": 1, "s": 2, "h": 2}.get(currtype, 5)]
				outlist.append((bgcolor, currtype, readeruser, au, ip, port, protocol, srinfo, chinfo, lbvaluereader, loginfmt, status))
			outlist.sort(key=lambda val: {"s": 0, "h": 1, "p": 2, "r": 3, "c": 4, "a": 5}[val[1]])  # sort according column 'client type' by customized sort order
			rulist.sort(key=lambda val: {"s": 0, "h": 1, "p": 2, "r": 3, "c": 4, "a": 5}[val[0]])  # sort according column 'client type' by customized sort order
			self.rulist = rulist
			self["buildinfos"].setText("%s | %s | %s" % (version, srvidfile, url))
			self["extrainfos"].setText("%s" % signed)
			self["timerinfos"].setText("%s | %s | %s" % (currtime, starttime, runtime))
			self["total"].setText("Total: %s" % sysinfo.get("mem_cur_total", na))
			self["used"].setText("Used: %s" % sysinfo.get("mem_cur_used", na))
			self["free"].setText("Free: %s" % sysinfo.get("mem_cur_free", na))
			self["buffer"].setText("Buffer: %s" % sysinfo.get("mem_cur_buff", na))
			self["camname"].setText("%s" % camname)
			self["virtuell"].setText("Virtuell memory: %s" % sysinfo.get("%s_vmsize" % tag, na))
			self["resident"].setText("Resident Set: %s" % sysinfo.get("%s_rsssize" % tag, na))
			self["outlist"].updateList(outlist)
			self.displayLog()
		else:
			self.loop.stop()
			self["buildinfos"].setText(url)
			self["extrainfos"].setText(_("Unexpected error accessing WebIF: %s") % result.decode(encoding="latin-1", errors="ignore"))
			self["timerinfos"].setText(currtime)  # set at least one element just for having the attribute 'activeComponents'

	def strf_delta(self, td):  # converts deltatime-format in hours (e.g. '2 days, 01:00' in '49:00:00')
		h, r = divmod(int(td.total_seconds()), 60 * 60)
		m, s = divmod(r, 60)
		h, m, s = (str(x).zfill(2) for x in (h, m, s))
		return f"{h}:{m}:{s}"

	def displayLog(self):
		logok, result = self.updateLog()
		if logok:
			self["logtext"].setText(result)
			self["logtext"].moveBottom()
		else:
			self.loop.stop()
			self["extrainfos"].setText(_("Unexpected error accessing WebIF: %s") % result)

	def showHideKeyOk(self):
		idx = self["outlist"].getSelectedIndex()
		if self.rulist and self.rulist[idx][2] > 0 and self.rulist[idx][0] in ["p", "r"]:
			self["key_OK"].setText(_("OK"))
			self["key_entitlements"].setText(_("Entitlements"))
		else:
			self["key_OK"].setText("")
			self["key_entitlements"].setText("")

	def menuCallback(self):
		callInThread(self.updateOScamData)
		self.keyCallback()

	def keyCallback(self):
		if config.oscaminfo.autoUpdate.value:
			self.loop.start(config.oscaminfo.autoUpdate.value * 1000, False)

	def keyOk(self):
		idx = self["outlist"].getSelectedIndex()
		if self.rulist and self.rulist[idx][2] > 0 and self.rulist[idx][0] in ["p", "r"]:
			self.loop.stop()
			self.session.openWithCallback(self.keyCallback, OSCamEntitlements, self.rulist[idx][1])

	def keyMenu(self):
		self.session.openWithCallback(self.menuCallback, OSCamInfoSetup)

	def keyShutdown(self):
		self.session.openWithCallback(boundFunction(self.msgboxCB, "shutdown"), MessageBox, _("Do you really want to shut down OSCam?\n\nATTENTION: To reactivate OSCam, a complete receiver restart must be carried out!"), MessageBox.TYPE_YESNO, timeout=10, default=False)

	def keyRestart(self):
		self.session.openWithCallback(boundFunction(self.msgboxCB, "restart"), MessageBox, _("Do you really want to restart OSCam?\n\nHINT: This will take about 5 seconds!"), MessageBox.TYPE_YESNO, timeout=10, default=False)

	def keyBlue(self):
		self.loop.stop()
		self.session.openWithCallback(self.keyCallback, OSCamInfoLog)

	def msgboxCB(self, action, answer):
		if answer:
			self.loop.stop()
			webifok, api, url, signstatus, result = self.openWebIF(part=action)
			if not webifok:
				print("[%s] ERROR in module 'msgboxCB': %s" % (MODULE_NAME, "Unexpected error accessing WebIF: %s" % result))
				self.session.open(MessageBox, _("Unexpected error accessing WebIF: %s" % result), MessageBox.TYPE_ERROR, timeout=3, close_on_any_key=True)

	def exit(self):
		self.loop.stop()
		self.close()


class OSCamEntitlements(Screen, OSCamGlobals):
	skin = """
		<screen name="OSCamEntitlements" position="center,center" size="1920,1080" backgroundColor="#10101010" title="OSCam Entitlements" flags="wfNoBorder" resolution="1920,1080">
			<ePixmap pixmap="icons/OscamLogo.png" position="15,15" size="80,80" scale="1" alphatest="blend" />
			<widget source="Title" render="Label" position="15,15" size="1905,60" font="Regular;40" halign="center" valign="center" foregroundColor="white" backgroundColor="#10101010" />
			<widget source="global.CurrentTime" render="Label" position="1710,15" size="210,90" font="Regular;75" noWrap="1" halign="center" valign="bottom" foregroundColor="#00FFFFFF" backgroundColor="#1A0F0F0F" transparent="1">
				<convert type="ClockToText">Default</convert>
			</widget>
			<widget source="global.CurrentTime" render="Label" position="1470,15" size="240,40" font="Regular;24" noWrap="1" halign="right" valign="bottom" foregroundColor="#00FFFFFF" backgroundColor="#1A0F0F0F" transparent="1">
				<convert type="ClockToText">Format:%A</convert>
			</widget>
			<widget source="global.CurrentTime" render="Label" position="1470,51" size="240,40" font="Regular;24" noWrap="1" halign="right" valign="bottom" foregroundColor="#00FFFFFF" backgroundColor="#1A0F0F0F" transparent="1">
				<convert type="ClockToText">Format:%e. %B</convert>
			</widget>
			<widget source="dheader0" render="Label" position="15,105" size="88,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # Type
			<widget source="dheader1" render="Label" position="105,105" size="103,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # CAID
			<widget source="dheader2" render="Label" position="210,105" size="118,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # Provid
			<widget source="dheader3" render="Label" position="330,105" size="268,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # ID
			<widget source="dheader4" render="Label" position="600,105" size="148,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # Class
			<widget source="dheader5" render="Label" position="750,105" size="163,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # Start Date
			<widget source="dheader6" render="Label" position="915,105" size="163,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # Expire Date
			<widget source="dheader7" render="Label" position="1080,105" size="825,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # Name
			<widget source="cheader0" render="Label" position="15,105" size="88,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # CAID
			<widget source="cheader1" render="Label" position="105,105" size="208,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # System
			<widget source="cheader2" render="Label" />  # Reshare (not used here)
			<widget source="cheader3" render="Label" />  # Hop (not used here)
			<widget source="cheader4" render="Label" />  # ShareID (not used here)
			<widget source="cheader5" render="Label" />  # RemoteID (not used here)
			<widget source="cheader6" render="Label" position="315,105" size="118,58" font="Regular;27" halign="left" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # ProvIDs
			<widget source="cheader7" render="Label" position="435,105" size="313,58" font="Regular;27" halign="left" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # Providers
			<widget source="cheader8" render="Label" position="750,105" size="268,58" font="Regular;27" halign="left" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # Nodes
			<widget source="cheader9" render="Label" position="1020,105" size="88,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # Locals
			<widget source="cheader10" render="Label" position="1110,105" size="88,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # Count
			<widget source="cheader11" render="Label" position="1200,105" size="73,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # Hop1
			<widget source="cheader12" render="Label" position="1275,105" size="73,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # Hop2
			<widget source="cheader13" render="Label" position="1350,105" size="73,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # Hopx
			<widget source="cheader14" render="Label" position="1425,105" size="73,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # Curr
			<widget source="cheader15" render="Label" position="1500,105" size="73,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # Res0
			<widget source="cheader16" render="Label" position="1575,105" size="73,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # Res1
			<widget source="cheader17" render="Label" position="1650,105" size="73,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # Res2
			<widget source="cheader18" render="Label" position="1725,105" size="73,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # Resx
			<widget source="cheader19" render="Label" position="1800,105" size="105,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />  # Reshare
			<parameters>
				<parameter name="OSCamInfoBGcolors" value="0x10fef2e6, 0x10f0f4e5" />
			</parameters>
			<widget source="entitleslist" render="Listbox" position="15,165" size="1890,828" backgroundColor="#10b3b3b3" enableWrapAround="1" scrollbarMode="showOnDemand" >
				<convert type="TemplatedMultiContent">
					{"templates":  # index 0 is backgroundcolor
						{	"default": (36, [
							MultiContentEntryText(pos=(0,0), size=(88,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=1),  # Type
							MultiContentEntryText(pos=(90,0), size=(103,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=2),  # CAID
							MultiContentEntryText(pos=(195,0), size=(118,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=3),  # Provid
							MultiContentEntryText(pos=(315,0), size=(268,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=4),  # ID
							MultiContentEntryText(pos=(585,0), size=(148,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=5),  # Class
							MultiContentEntryText(pos=(735,0), size=(163,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER|RT_WRAP, color=0x000000, backcolor=MultiContentTemplateColor(0), text=6),  # Start Date
							MultiContentEntryText(pos=(900,0), size=(163,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=7),  # Expire Date
							MultiContentEntryText(pos=(1065,0), size=(825,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER|RT_WRAP, color=0x000000, backcolor=MultiContentTemplateColor(0), text=8)  # Name
							]),
							"entitlements": (36, [  # index 3 to 6 (Reshare, Hop, ShareID, RemoteID) are not used here
							MultiContentEntryText(pos=(0,0), size=(88,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=1),  # Caid
							MultiContentEntryText(pos=(90,0), size=(208,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=2),  # System
							MultiContentEntryText(pos=(300,0), size=(118,36), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER|RT_ELLIPSIS, color=0x000000, backcolor=MultiContentTemplateColor(0), text=7),  # ProvIDs
							MultiContentEntryText(pos=(420,0), size=(313,36), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER|RT_ELLIPSIS, color=0x000000, backcolor=MultiContentTemplateColor(0), text=8),  # Providers
							MultiContentEntryText(pos=(735,0), size=(268,36), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER|RT_ELLIPSIS, color=0x000000, backcolor=MultiContentTemplateColor(0), text=9),  # Nodes
							MultiContentEntryText(pos=(1005,0), size=(88,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=10),  # Locals
							MultiContentEntryText(pos=(1095,0), size=(88,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=11),  # Count
							MultiContentEntryText(pos=(1185,0), size=(73,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=12),  # Hop1
							MultiContentEntryText(pos=(1260,0), size=(73,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=13),  # Hop2
							MultiContentEntryText(pos=(1335,0), size=(73,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=14),  # Hopx
							MultiContentEntryText(pos=(1410,0), size=(73,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=15),  # Curr
							MultiContentEntryText(pos=(1485,0), size=(73,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=16),  # Res0
							MultiContentEntryText(pos=(1560,0), size=(73,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=17),  # Res1
							MultiContentEntryText(pos=(1635,0), size=(73,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=18),  # Res2
							MultiContentEntryText(pos=(1710,0), size=(73,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=19),  # Resx
							MultiContentEntryText(pos=(1785,0), size=(105,36), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, color=0x000000, backcolor=MultiContentTemplateColor(0), text=20)  # Reshare
							])
						},
						"fonts": [gFont("Regular",27)], "itemHeight":36
					}
				</convert>
			</widget>
			<widget source="key_blue" render="Label" foregroundColor="blue" backgroundColor="blue" position="1150,1010" size="10,65" objectTypes="key_blue,StaticText">
				<convert type="ConditionalShowHide" />
			</widget>
			<widget source="key_blue" render="Label" position="1170,1020" size="380,42" font="Regular;30" halign="left" valign="center" foregroundColor="grey" objectTypes="key_blue,StaticText">
				<convert type="ConditionalShowHide" />
			</widget>
			<widget source="key_OK" render="Label" position="1395,1020" size="60,42" font="Regular;30" halign="center" valign="center" foregroundColor="black" backgroundColor="grey">
				<convert type="ConditionalShowHide" />
			</widget>
			<widget source="key_detailed" render="Label" position="1470,1020" size="250,42" font="Regular;30" halign="left" valign="center" foregroundColor="grey">
				<convert type="ConditionalShowHide" />
			</widget>
			<widget source="key_exit" render="Label" position="1730,1020" size="150,42" font="Regular;30" halign="center" valign="center" foregroundColor="black" backgroundColor="grey" />
		</screen>"""

	def __init__(self, session, readeruser):
		self.readeruser = readeruser
		Screen.__init__(self, session)
		self.skinName = "OSCamEntitlements"
		self.setTitle(_("OSCamInfo: Entitlements for '%s'") % self.readeruser)
		self.dheaders = ["type", "CAID", "Provid", "ID", "Class", "Start Date", "Expire Date", "Name"]
		self.cheaders = ["CAID", "System", "Reshare", "Hop", "ShareID", "RemoteID", "ProvIDs", "Providers", "Nodes", "Locals", "Count", "Hop1", "Hop2", "Hopx", "Curr", "Res0", "Res1", "Res2", "Resx", "Reshare"]
		self.showall = False
		self.externalreader = False
		self.entitleslist = []
		for idx in range(len(self.dheaders)):
			self["dheader%s" % idx] = StaticText()
		for idx in range(len(self.cheaders)):
			self["cheader%s" % idx] = StaticText()
		self["entitleslist"] = List([])
		self["key_blue"] = StaticText()
		self["key_OK"] = StaticText()
		self["key_detailed"] = StaticText()
		self["key_exit"] = StaticText(_("Exit"))
		self["actions"] = HelpableActionMap(self, ["NavigationActions", "OkCancelActions", "ColorActions"], {
			"ok": (self.keyOk, _("Show all details")),
			"cancel": (self.exit, _("Close the screen")),
			"blue": (self.keyBlue, _("Show all"))
			}, prio=1, description=_("OSCamInfo Actions"))
		self.onLayoutFinish.append(self.onLayoutFinished)
		self.bgColors = parameters.get("OSCamInfoBGcolors", (0x10fcfce1, 0x10f1f6e6, 0x10e2e0ef))
		self.loop = eTimer()
		self.loop.callback.append(self.updateEntitlements)
		if config.oscaminfo.autoUpdate.value:
			self.loop.start(config.oscaminfo.autoUpdate.value * 1000, False)

	def onLayoutFinished(self):
		self.showHideBlue()
		self.showHideKeyOk()
		self["entitleslist"].onSelectionChanged.append(self.showHideKeyOk)

		for idx in range(len(self.dheaders)):
			self["dheader%s" % idx].setText("")
		for idx in range(len(self.cheaders)):
			self["cheader%s" % idx].setText("")
		callInThread(self.updateEntitlements)

	def updateEntitlements(self):
		entitleslist = self.getJSONentitlements()
		if entitleslist:
			self["entitleslist"].style = "default"
			self.show_dheaders()
		else:
			entitleslist = self.getJSONstats()
			if entitleslist:
				if entitleslist[0][1] == "key":
					self["entitleslist"].style = "default"
					self.show_dheaders()
				else:
					self["entitleslist"].style = "entitlements"
					self.show_cheaders()
		self["entitleslist"].updateList(entitleslist)
		self.setTitle(_("OSCamInfo: %s Entitlements for '%s'") % (len(entitleslist), self.readeruser))
		self.entitleslist = entitleslist
		self.showHideBlue()
		self.showHideKeyOk()
		if not entitleslist:
			self.loop.stop()

	def getJSONentitlements(self):
		entitleslist = []
		webifok, api, url, signstatus, result = self.openWebIF(part="entitlement", label=self.readeruser)  # read JSON-entitlements
		if webifok and result:
			entitlements = loads(result).get("oscam", {}).get("entitlements", [])
			if entitlements:
				bgcoloridx = 0
				na = _("n/a")
				for entitle in entitlements:
					etype = entitle.get("type", na)
					caid = entitle.get("caid", na)
					provid = entitle.get("provid", na)
					eid = entitle.get("id", na)
					eclass = entitle.get("class", na)
					startdate = entitle.get("startDate", "1999-01-01")[:10]
					expiredate = entitle.get("expireDate", "1999-01-01")[:10]
					name = entitle.get("name", na)
					bgcolor = self.bgColors[bgcoloridx]
					entitleslist.append((bgcolor, etype, caid, provid, eid, eclass, startdate, expiredate, name))
					bgcoloridx = (bgcoloridx + 1) % 2  # only the first 2 colors
		return entitleslist

	def getJSONstats(self):
		entitleslist = []
		webifok, api, url, signstatus, result = self.openWebIF()  # read JSON-status
		if webifok and result:
			self.clients = loads(result).get("oscam", {}).get("status", {}).get("client", [])
			bgcoloridx = 0
			na = _("n/a")
			for client in self.clients:
				if client.get("type", "") in ["p", "r"] and client.get("rname_enc", "") == self.readeruser:
					for entitle in client.get("connection", {}).get("entitlements", []):
						bgcolor = self.bgColors[bgcoloridx]
						caid = entitle.get("caid", "")
						if caid:  # emulator
							provid = entitle.get("provid", na)
							expiredate = entitle.get("exp", na)
							entitleslist.append((bgcolor, "key", caid, provid, "", "", "", expiredate, "", "", "", "", "", "", "", "", "", "", "", "", ""))
							bgcoloridx = (bgcoloridx + 1) % 2  # only the first 2 colors
						else:  # external reader
							self.externalreader = True
							entitleslist = self.getXMLentitlements()
			return entitleslist

	def getXMLentitlements(self):
		entitleslist = []
		webifok, api, url, signstatus, result = self.openWebIF(part="entitlement", label=self.readeruser, fmt="xml")  # read XML-entitlements
		if webifok and result:
			reader = XML(result).find("reader")
			bgcoloridx = 0
			for card in reader.find("cardlist").findall("card"):
				bgcolor = self.bgColors[bgcoloridx]
				shareid = card.find("shareid").text
				remoteid = card.find("remoteid").text
				caid = card.get("caid", "")
				system = card.get("system", "")
				reshare = card.get("reshare", "")
				hop = card.get("hop", "")
				providlist = []
				providerlist = []
				for provider in card.find("providers").findall("provider"):
					providlist.append(provider.get("provid", ""))
					providerlist.append(provider.text)
				provid = ", ".join(providlist)
				ptext = ", ".join(providerlist)
				nodelist = []
				for node in card.find("nodes").findall("node"):
					nodelist.append(node.text)
				ntext = ", ".join(nodelist)
				hoplist = []
				for client in self.clients:  # find according CAID in JSONstats-clients
					if client.get("request", {}).get("caid", "") == caid:
							for entitle in client.get("connection", {}).get("entitlements", []):
								for key in ["locals", "cccount", "ccchop1", "ccchop2", "ccchopx", "ccccurr", "cccres0", "cccres1", "cccres2", "cccresx", "cccreshare"]:
									hoplist.append(entitle.get(key, ""))
							break
				if hoplist:
					entitleslist.append(tuple([bgcolor, caid, system, reshare, hop, shareid, remoteid, provid, ptext, ntext] + hoplist))
				elif self.showall:
					hoplist = [""] * 11
					entitleslist.append(tuple([bgcolor, caid, system, reshare, hop, shareid, remoteid, provid, ptext, ntext] + hoplist))
				bgcoloridx = (bgcoloridx + 1) % 2  # only the first 2 colors
		return entitleslist

	def show_dheaders(self):
		for idx in range(len(self.cheaders)):
			self["cheader%s" % idx].setText("")
		for idx, dheader in enumerate(self.dheaders):
			self["dheader%s" % idx].setText(dheader)

	def show_cheaders(self):
		for idx in range(len(self.dheaders)):
			self["dheader%s" % idx].setText("")
		for idx, cheader in enumerate(self.cheaders):
			self["cheader%s" % idx].setText(cheader)

	def showHideBlue(self):
		if self.externalreader:
			if self.showall:
				self["key_blue"].setText(_("Active only"))
			else:
				self["key_blue"].setText(_("Show all"))
		else:
			self["key_blue"].setText("")

	def showHideKeyOk(self):
		if self.externalreader:
			self["key_OK"].setText(_("OK"))
			self["key_detailed"].setText(_("Show details"))
		else:
			self["key_OK"].setText("")
			self["key_detailed"].setText("")

	def keyBlue(self):
		if self.showall:
			self["key_exit"].setText(_("Active only"))
		else:
			self["key_exit"].setText(_("Show all"))
		self.showall = not self.showall
		self.updateEntitlements()

	def keyCallback(self):
		if config.oscaminfo.autoUpdate.value:
			self.loop.start(config.oscaminfo.autoUpdate.value * 1000, False)

	def keyOk(self):
		entitlement = self.entitleslist[self["entitleslist"].getSelectedIndex()] if self.entitleslist else []
		if self.externalreader:
			self.loop.stop()
			self.session.openWithCallback(self.keyCallback, OSCamEntitleDetails, entitlement)

	def exit(self):
		self.loop.stop()
		self.close()


class OSCamEntitleDetails(Screen, OSCamGlobals):
	skin = """
		<screen name="OSCamEntitleDetails" position="center,center" size="765,1080" backgroundColor="#10101010" title="OSCam EntitleDetails" flags="wfNoBorder" resolution="1920,1080">
			<ePixmap pixmap="icons/OscamLogo.png" position="15,15" size="80,80" scale="1" alphatest="blend" />
			<widget source="Title" render="Label" position="105,15" size="660,60" font="Regular;40" halign="center" valign="center" foregroundColor="white" backgroundColor="#10101010" />
			<eLabel text="CAID" position="15,105" size="88,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<eLabel text="System" position="105,105" size="178,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<eLabel text="Reshare" position="285,105" size="118,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<eLabel text="Hop" position="405,105" size="73,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<eLabel text="ShareID" position="480,105" size="133,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<eLabel text="RemoteID" position="615,105" size="135,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<widget source="label0" render="Label" position="15,165" size="88,55" font="Regular;27" halign="center" valign="center" foregroundColor="black" backgroundColor="#10fef2e6" />  # CAID
			<widget source="label1" render="Label" position="105,165" size="178,55" font="Regular;27" halign="center" valign="center" foregroundColor="black" backgroundColor="#10fef2e6" />  # System
			<widget source="label2" render="Label" position="285,165" size="118,55" font="Regular;27" halign="center" valign="center" foregroundColor="black" backgroundColor="#10fef2e6" />  # Reshare
			<widget source="label3" render="Label" position="405,165" size="73,55" font="Regular;27" halign="center" valign="center" foregroundColor="black" backgroundColor="#10fef2e6" />  # Hop
			<widget source="label4" render="Label" position="480,165" size="133,55" font="Regular;27" halign="center" valign="center" foregroundColor="black" backgroundColor="#10fef2e6" />  # ShareID
			<widget source="label5" render="Label" position="615,165" size="135,55" font="Regular;27" halign="center" valign="center" foregroundColor="black" backgroundColor="#10fef2e6" />  # RemoteID
			<eLabel text="ProvIDs" position="15,225" size="735,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<widget source="ProvIDlist" render="Listbox" position="15,285" size="735,195" font="Regular;27" itemHeight="40" foregroundColor="black" backgroundColor="#10fef2e6" foregroundColorSelected="black" backgroundColorSelected="#10fef2e6" halign="center" valign="center" scrollbarMode="showOnDemand" >
				<convert type="StringList" />
			</widget>
			<eLabel text="Providers" position="15,485" size="735,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<widget source="Providerlist" render="Listbox" position="15,545" size="735,195" font="Regular;27" itemHeight="40" foregroundColor="black" backgroundColor="#10fef2e6" foregroundColorSelected="black" backgroundColorSelected="#10fef2e6" halign="center" valign="center" scrollbarMode="showOnDemand" >
				<convert type="StringList" />
			</widget>
			<eLabel text="Nodes" position="15,745" size="735,58" font="Regular;27" halign="center" valign="center" foregroundColor="white" backgroundColor="#105a5a5a" />
			<widget source="Nodelist" render="Listbox" position="15,805" size="735,195" font="Regular;27" itemHeight="40" foregroundColor="black" backgroundColor="#10fef2e6" foregroundColorSelected="black" backgroundColorSelected="#10fef2e6" halign="center" valign="center" scrollbarMode="showOnDemand" >
				<convert type="StringList" />
			</widget>
			<widget source="key_exit" render="Label" position="570,1020" size="150,42" font="Regular;30" halign="center" valign="center" foregroundColor="black" backgroundColor="grey" />
		</screen>
		"""

	def __init__(self, session, entitlement):
		def splitParts(slist, count):
			nlist = []
			for element in [slist[count * i:count * (i + 1)] for i in range(int(len(slist) / count + 1))]:
				elemstr = ", ".join(element)
				if elemstr:
					nlist.append(elemstr)
			return nlist

		Screen.__init__(self, session)
		self.skinName = "OSCamEntitleDetails"
		entitlelen = len(entitlement)
		self.setTitle(_("Entitlements for 'CAID %s'") % entitlement[1] if entitlelen else _("n/a"))
		for idx in range(len(entitlement)):
			if (idx + 1) < entitlelen:
				self["label%s" % idx] = StaticText(entitlement[idx + 1])
		self["ProvIDlist"] = List((splitParts(entitlement[7].split(", "), 6)) if entitlelen else _("n/a"))
		self['ProvIDlist'].selectionEnabled(0)
		self["Providerlist"] = List((splitParts(entitlement[8].split(", "), 2)) if entitlelen else _("n/a"))
		self['Providerlist'].selectionEnabled(0)
		self["Nodelist"] = List((splitParts(entitlement[9].split(", "), 2)) if entitlelen else _("n/a"))
		self['Nodelist'].selectionEnabled(0)
		self["key_exit"] = StaticText(_("Exit"))
		self["actions"] = HelpableActionMap(self, ["OkCancelActions"], {
			"ok": (self.close, _("Close the screen")),
			"cancel": (self.close, _("Close the screen")),
			}, prio=1, description=_("OSCamInfo Actions"))


class OSCamInfoLog(Screen, OSCamGlobals):
	skin = """
		<screen name="OSCamInfoLog" position="center,center" size="1920,1080" backgroundColor="#10101010" title="OSCamInfo Log" flags="wfNoBorder" resolution="1920,1080">
			<widget source="Title" render="Label" position="15,15" size="1905,60" font="Regular;40" halign="center" valign="center" foregroundColor="white" backgroundColor="#10101010" />
			<widget source="global.CurrentTime" render="Label" position="1635,15" size="260,60" font="Regular;40" halign="right" valign="center" foregroundColor="#0092CBDF" backgroundColor="#10101010">
				<convert type="ClockToText">Format:%H:%M:%S</convert>
			</widget>
			<widget name="logtext" position="15,70" size="1890,995" font="Regular;24" halign="left" valign="top" foregroundColor="black" backgroundColor="#ECEAF6" noWrap="0" scrollbarMode="showOnDemand" scrollbarForegroundColor="black" />
		</screen>
		"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "OSCamInfoLog"
		self.setTitle(_("OSCamInfo: Log"))
		self["logtext"] = ScrollLabel(_("<no log found>"))
		self["actions"] = HelpableActionMap(self, ["NavigationActions", "OkCancelActions"], {
			"ok": (self.exit, _("Close the screen")),
			"cancel": (self.exit, _("Close the screen")),
			"pageUp": (self.keyPageUp, _("Move up a page")),
			"up": (self.keyPageUp, _("Move up a page")),
			"down": (self.keyPageDown, _("Move down a page")),
			"pageDown": (self.keyPageDown, _("Move down a page"))
			}, prio=1, description=_("OSCamInfo Log Actions"))
		self.loop = eTimer()
		self.loop.callback.append(self.displayLog)
		self.onLayoutFinish.append(self.onLayoutFinished)

	def onLayoutFinished(self):
		if config.oscaminfo.autoUpdateLog.value:
			self.loop.start(config.oscaminfo.autoUpdateLog.value * 1000, False)
		callInThread(self.displayLog)

	def displayLog(self):
		logok, result = self.updateLog()
		if logok:
			self["logtext"].setText(result)
			self["logtext"].moveBottom()
		else:
			self.loop.stop()
			self["logtext"].setText(_("Unexpected error accessing WebIF: %s" % result))

	def keyPageDown(self):
		self["logtext"].pageDown()

	def keyPageUp(self):
		self["logtext"].pageUp()

	def exit(self):
		self.loop.stop()
		self.close()


class OSCamInfoSetup(Setup):
	def __init__(self, session):
		self.status = None
		self.oldIP = config.oscaminfo.ip.value
		self.hostValidator = compile(r"(\d*[a-zA-Z]+[\.]*\d*)+$")
		Setup.__init__(self, session, setup="OSCamInfoSetup")

	def selectionChanged(self):
		Setup.selectionChanged(self)
		self.validate()

	def changedEntry(self):
		Setup.changedEntry(self)
		self.validate()

	def validate(self):
		footnote = None
		if self.getCurrentItem() == config.oscaminfo.ip and self.oldIP != config.oscaminfo.ip.value:
			try:
				if not self.hostValidator.match(config.oscaminfo.ip.value):
					ip_address(config.oscaminfo.ip.value)
			except ValueError:
				footnote = _("IP address is invalid!")
			self.setFootnote(footnote)
			self.status = footnote

	def keySave(self):
		def keySaveCallback(result):
			Setup.keySave(self)
		if config.oscaminfo.ip.value != self.oldIP:
			try:
				getaddrinfo(config.oscaminfo.ip.value, config.oscaminfo.port.value)
				self.status = None
			except gaierror:
				self.status = _("Hostname cannot be resolved to IP address!")
		if self.status:
			self.session.openWithCallback(keySaveCallback, MessageBox, self.status, type=MessageBox.TYPE_WARNING)
		else:
			Setup.keySave(self)


class OscamInfoMenu(OSCamInfo):
	def __init__(self, session):
		print("[OscamInfoMenu] Warning: OscamInfoMenu has been deprecated, use OSCamInfo instead!")
		OSCamInfo.__init__(self, session)
