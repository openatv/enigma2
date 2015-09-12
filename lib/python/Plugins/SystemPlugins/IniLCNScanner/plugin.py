# plugin from Sif Team, with some modds for EGAMI use

from enigma import eDVBDB, eServiceID, eServiceReference, eServiceCenter
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.ConfigList import ConfigListScreen
from Components.config import getConfigListEntry, config, ConfigSubsection, ConfigYesNo, ConfigSelection, configfile
from Tools.Directories import resolveFilename, SCOPE_CONFIG
from Tools.ServiceReference import service_types_tv_ref, service_types_radio_ref, serviceRefAppendPath, hdmiInServiceRef
from Plugins.Plugin import PluginDescriptor
from boxbranding import getMachineBuild
import os
import sys
import xml.etree.cElementTree

class LCN():
	service_types_tv = service_types_tv_ref.toString()
	service_types_radio = service_types_radio_ref.toString()
	sr_marker_terr_lcn_tv = eServiceReference(eServiceReference.idDVB, eServiceReference.isMarker)
	sr_marker_terr_lcn_tv.setName("Terrestrial TV LCN")
	sr_marker_terr_lcn_radio = eServiceReference(eServiceReference.idDVB, eServiceReference.isMarker)
	sr_marker_terr_lcn_radio.setName("Terrestrial RADIO LCN")
	sr_filler = eServiceReference(
		eServiceReference.idDVB,
		eServiceReference.isInvisible | eServiceReference.isNumberedMarker | eServiceReference.isMarker,
		0xD
	)
	sr_marker = eServiceReference(
		eServiceReference.idDVB,
		eServiceReference.isMarker
	)
	sr_tv_bouquet_entry = eServiceReference(
		eServiceReference.idDVB,
		eServiceReference.isInvisible | eServiceReference.isNumberedMarker | eServiceReference.isMarker,
		eServiceID.dTv
	)
	sr_tv_bouquet_entry.setPath('FROM BOUQUET "userbouquet.terrestrial_lcn.tv" ORDER BY bouquet')
	sr_radio_bouquet_entry = eServiceReference(
		eServiceReference.idDVB,
		eServiceReference.isInvisible | eServiceReference.isNumberedMarker | eServiceReference.isMarker,
		eServiceID.dRadio
	)
	sr_radio_bouquet_entry.setPath('FROM BOUQUET "userbouquet.terrestrial_lcn.radio" ORDER BY bouquet')

	def __init__(self, dbfile, rulefile, rulename, bouquetfile):
		self.dbfile = dbfile
		self.bouquetfile = bouquetfile
		self.lcnlist = []
		self.markers = []
		self.e2services = []
		mdom = xml.etree.cElementTree.parse(rulefile)
		self.root = None
		for x in mdom.getroot():
			if x.tag == "ruleset" and x.get("name") == rulename:
				self.root = x
				return

	def addLcnToList(self, namespace, nid, tsid, sid, lcn, signal):
		for x in self.lcnlist:
			if x[0] == lcn and x[1] == namespace and x[2] == nid and x[3] == tsid and x[4] == sid and x[5] == signal:
				return

		if lcn == 0:
			return

		for i in range(0, len(self.lcnlist)):
			if self.lcnlist[i][0] == lcn:
				if self.lcnlist[i][5] > signal:
					self.addLcnToList(namespace, nid, tsid, sid, lcn + 350, signal)
				else:
					znamespace = self.lcnlist[i][1]
					znid = self.lcnlist[i][2]
					ztsid = self.lcnlist[i][3]
					zsid = self.lcnlist[i][4]
					zsignal = self.lcnlist[i][5]
					self.lcnlist[i][1] = namespace
					self.lcnlist[i][2] = nid
					self.lcnlist[i][3] = tsid
					self.lcnlist[i][4] = sid
					self.lcnlist[i][5] = signal
					self.addLcnToList(znamespace, znid, ztsid, zsid, lcn + 350, zsignal)
				return
			elif self.lcnlist[i][0] > lcn:
				self.lcnlist.insert(i, [lcn, namespace, nid, tsid, sid, signal])
				return

		self.lcnlist.append([lcn, namespace, nid, tsid, sid, signal])

	def renumberLcn(self, range, rule):
		tmp = range.split("-")
		if len(tmp) != 2:
			return

		min = int(tmp[0])
		max = int(tmp[1])

		for x in self.lcnlist:
			if x[0] >= min and x[0] <= max:
				value = x[0]
				cmd = "x[0] = " + rule
				try:
					exec cmd
				except Exception, e:
					print "[LCNScanner]", e

	def addMarker(self, position, text):
		self.markers.append([position, text])

	def read(self, serviceType):
		self.readE2Services(serviceType)

		try:
			f = open(self.dbfile)
		except Exception, e:
			print "[LCNScanner]", e
			return

		while True:
			line = f.readline()
			if line == "":
				break

			line = line.strip()
			#print "[LCNScanner]", line
			if len(line) != 38:
				continue

			tmp = line.split(":")
			if len(tmp) != 6:
				continue

			self.addLcnToList(int(tmp[0], 16), int(tmp[1], 16), int(tmp[2], 16), int(tmp[3], 16), int(tmp[4]), int(tmp[5]))
		f.close()

		if self.root is not None:
			for x in self.root:
				if x.tag == "rule":
					if x.get("type") == "renumber":
						self.renumberLcn(x.get("range"), x.text)
						self.lcnlist.sort(key=lambda z: int(z[0]))
					elif x.get("type") == "marker":
						self.addMarker(int(x.get("position")), x.text)

		self.markers.sort(key=lambda z: int(z[0]))

	def readE2Services(self, serviceType):
		self.e2services = []
		if serviceType == "TV":
			ref = serviceRefAppendPath(service_types_tv_ref, ' ORDER BY name')
		elif serviceType == "RADIO":
			ref = serviceRefAppendPath(service_types_radio_ref, ' ORDER BY name')
		serviceHandler = eServiceCenter.getInstance()
		servicelist = serviceHandler.list(ref)
		if servicelist is not None:
			while True:
				service = servicelist.getNext()
				if not service.valid():  # check if end of list
					break

				unsigned_orbpos = service.getUnsignedData(4) >> 16
				if unsigned_orbpos == 0xEEEE:  # Terrestrial
					self.e2services.append(service)

	def writeBouquet(self, filename, name_marker, extras=[]):
		try:
			f = open('/etc/enigma2/' + filename, "w")
		except Exception, e:
			print "[LCNScanner]", e
			return

		self.newlist = []
		count = 0

		for x in self.lcnlist:
			count += 1
			while x[0] != count:
				self.newlist.append([count, 11111111, 11111, 111, 111, 111111])
				count += 1
			if x[0] == count:
				self.newlist.append(x)

		#for x in self.e2services:
			#print "[LCNScanner]", " self.e2services:", x.toString()

		#for x in self.newlist:
			#print "[LCNScanner]", " NEW LIST LCN :", x

		#print "[LCNScanner]", " New LIST LEN: " , len(self.newlist)

		print "[LCN] writeTVBouquet write", "#NAME " + name_marker.getName() #ZZ
		f.write("#NAME " + name_marker.getName() + "\n")
		f.write("#SERVICE " + name_marker.toString() + "\n")
		f.write("##DESCRIPTION " + name_marker.getName() + "\n")
		for x in self.newlist:
			if int(x[1]) == 11111111:
				#print "[LCNScanner]", x[0], " Detected 111111111111 service"
				f.write("#SERVICE " + self.sr_filler.toString() + "\n")
				continue

			if len(self.markers) > 0:
				if x[0] > self.markers[0][0]:
					f.write("#SERVICE " + self.sr_marker.toString() + "\n")
					f.write("#DESCRIPTION ------- " + self.markers[0][1] + " -------\n")
					self.markers.remove(self.markers[0])
			refstr = "1:0:1:%x:%x:%x:%x:0:0:0:" % (x[4], x[3], x[2], x[1])  # temporary ref
			refsplit = eServiceReference(refstr).toString().split(":")
			added = False
			for tref in self.e2services:
				tmp = tref.toString().split(":")
				if tmp[3] == refsplit[3] and tmp[4] == refsplit[4] and tmp[5] == refsplit[5] and tmp[6] == refsplit[6]:
					f.write("#SERVICE " + tref.toString() + "\n")
					added = True
					break

			if not added:  # no service found? something wrong? a log should be a good idea. Anyway we add an empty line so we keep the numeration
				f.write("#SERVICE " + self.sr_filler.toString() + "\n")

		# Add extra services
		for x in extras:
			f.write("#SERVICE " + x.toString() + "\n")

		f.close()

	def writeTVBouquet(self):
		# Add HDMI-IN
		if getMachineBuild() in ('inihdp'):
			extras = [hdmiInServiceRef()]
		else:
			extras = []
		self.writeBouquet("userbouquet.terrestrial_lcn.tv", self.sr_marker_terr_lcn_tv, extras)
		self.addInTVBouquets()

	def addInBouquets(self, bouquets_filename, bouquet_filename, bouquet_entry):
		f = open('/etc/enigma2/' + bouquets_filename, 'r')
		ret = f.read().split("\n")
		f.close()

		i = 0
		while i < len(ret):
			if ret[i].find(bouquet_filename) >= 0:
				return
			i += 1

		f = open('/etc/enigma2/' + bouquets_filename, 'w')
		f.write(ret[0] + "\n")
		f.write("#SERVICE " + bouquet_entry.toString() + "\n")
		i = 1
		while i < len(ret):
			f.write(ret[i] + "\n")
			i += 1

	def addInTVBouquets(self):
		self.addInBouquets("bouquets.tv", "userbouquet.terrestrial_lcn.tv", self.sr_tv_bouquet_entry)

	def writeRadioBouquet(self):
		self.writeBouquet("userbouquet.terrestrial_lcn.radio", self.sr_marker_terr_lcn_radio)
		self.addInRadioBouquets()

	def addInRadioBouquets(self):
		self.addInBouquets("bouquets.radio", "userbouquet.terrestrial_lcn.radio", self.sr_radio_bouquet_entry)

	def reloadBouquets(self):
		eDVBDB.getInstance().reloadBouquets()

class LCNBuildHelper():
	def __init__(self):
		self.bouquetlist = []
		for x in self.readBouquetsTvList("/etc/enigma2"):
			self.bouquetlist.append((x[0], x[1]))

		self.rulelist = []
		mdom = xml.etree.cElementTree.parse(os.path.dirname(sys.modules[__name__].__file__) + "/rules.xml")
		for x in mdom.getroot():
			if x.tag == "ruleset":
				self.rulelist.append((x.get("name"), x.get("name")))

		config.lcn = ConfigSubsection()
		config.lcn.enabled = ConfigYesNo(True)
		config.lcn.bouquet = ConfigSelection(default="userbouquet.LastScanned.tv", choices=self.bouquetlist)
		config.lcn.rules = ConfigSelection(self.rulelist)

	def readBouquetsTvList(self, pwd):
		return self.readBouquetsList(pwd, "bouquets.tv")

	def readBouquetsRadioList(self, pwd):
		return self.readBouquetsList(pwd, "bouquets.radio")

	def readBouquetsList(self, pwd, bouquetname):
		try:
			f = open(pwd + "/" + bouquetname)
		except Exception, e:
			print "[LCNScanner]", e
			return

		ret = []

		while True:
			line = f.readline()
			if line == "":
				break

			if line[:8] != "#SERVICE":
				continue

			filename = None
			bouquetlistref = eServiceReference(line[8:].strip())
			bqpath = bouquetlistref.getPath()
			if bqpath.startswith("FROM BOUQUET"):
				bqparts = bqpath.split('"', 3)
				if len(bqparts) == 3:
					filename = bqparts[1]
				else:
					filename = bqpath

			if filename:
				try:
					fb = open(pwd + "/" + filename)
				except Exception, e:
					print "[LCNScanner]", e
					continue

				tmp = fb.readline().strip()
				if tmp.startswith("#NAME "):
					ret.append([filename, tmp[6:]])
				else:
					ret.append([filename, filename])
				fb.close()

		return ret

	def buildAfterScan(self):
		if config.lcn.enabled.value:
			self.buildlcn(True)

	def buildlcn(self, suppressmessages=False):
		rule = self.rulelist[0][0]
		for x in self.rulelist:
			if x[0] == config.lcn.rules.value:
				rule = x[0]
				break

		bouquet = self.rulelist[0][0]
		for x in self.bouquetlist:
			if x[0] == config.lcn.bouquet.value:
				bouquet = x[0]
				break

		lcn = LCN(resolveFilename(SCOPE_CONFIG, "lcndb"), os.path.dirname(sys.modules[__name__].__file__) + "/rules.xml", rule, resolveFilename(SCOPE_CONFIG, bouquet))
		lcn.read("TV")
		if len(lcn.lcnlist) > 0:
			lcn.writeTVBouquet()
		else:
			if not suppressmessages:
				self.session.open(MessageBox, _("No entry in lcn db. Please do a service scan."), MessageBox.TYPE_INFO)

		lcn.read("RADIO")
		if len(lcn.lcnlist) > 0:
			lcn.writeRadioBouquet()
		else:
			if not suppressmessages:
				self.session.open(MessageBox, _("No entry in lcn db. Please do a service scan."), MessageBox.TYPE_INFO)

		lcn.reloadBouquets()

class LCNScannerPlugin(Screen, ConfigListScreen, LCNBuildHelper):
	skin = """
		<screen position="center,center" size="560,400" title="LCN Scanner">
			<widget name="config" position="5,5" size="550,350" scrollbarMode="showOnDemand" zPosition="1"/>

			<widget name="key_red" position="0,360" size="140,40" valign="center" halign="center" zPosition="5" transparent="1" foregroundColor="white" font="Regular;18"/>
			<widget name="key_green" position="140,360" size="140,40" valign="center" halign="center" zPosition="5" transparent="1" foregroundColor="white" font="Regular;18"/>

			<ePixmap name="red" pixmap="skin_default/buttons/red.png" position="0,360" size="140,40" zPosition="4" transparent="1" alphatest="on"/>
			<ePixmap name="green" pixmap="skin_default/buttons/green.png" position="140,360" size="140,40" zPosition="4" transparent="1" alphatest="on"/>
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		LCNBuildHelper.__init__(self)

		self.list = [
			getConfigListEntry(_("Enable terrestrial LCN:"), config.lcn.enabled),
			getConfigListEntry(_("Terrestrial bouquet:"), config.lcn.bouquet),
			getConfigListEntry(_("LCN rules:"), config.lcn.rules),
		]

		ConfigListScreen.__init__(self, self.list, session=session)
		self["key_red"] = Button(_("Rebuild"))
		self["key_green"] = Button(_("Exit"))
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
			"red": self.ok,
			"green": self.keyCancel,
			"cancel": self.keyCancel,
		}, -2)

	def confirm(self, confirmed):
		if confirmed:
			self.buildlcn()

		self.keySave()
		configfile.save()

	def ok(self):
		if config.lcn.enabled.value:
			self.session.openWithCallback(self.confirm, MessageBox, _("Rebuild LCN bouquet now?"), MessageBox.TYPE_YESNO, default=True)
		else:
			self.keySave()
			configfile.save()

def LCNScannerMain(session, **kwargs):
	session.open(LCNScannerPlugin)

def LCNScannerSetup(menuid, **kwargs):
	#if menuid == "scan":
	#	return [("LCN Scanner", LCNScannerMain, "lcnscanner", None)]
	return []

def Plugins(**kwargs):
	return PluginDescriptor(name="LCN", description=_("LCN plugin for DVB-T/T2 services"), where=PluginDescriptor.WHERE_MENU, fnc=LCNScannerSetup)
	#return PluginDescriptor(name="LCN", description=_("LCN plugin for DVB-T/T2 services"), where=PluginDescriptor.WHERE_PLUGINMENU, fnc=LCNScannerMain)
