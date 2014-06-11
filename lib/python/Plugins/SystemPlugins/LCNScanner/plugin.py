# plugin from Sif Team

from enigma import eDVBDB, eServiceReference, eServiceCenter
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.ConfigList import ConfigListScreen
from Components.config import getConfigListEntry, config, ConfigSubsection, ConfigYesNo, ConfigSelection, configfile
from Tools.Directories import resolveFilename, SCOPE_CONFIG
from Plugins.Plugin import PluginDescriptor
import os
import sys
import re
import shutil
import xml.etree.cElementTree

class LCN():
	service_types_tv = '1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 22) || (type == 25) || (type == 134) || (type == 195)'
	service_types_radio = '1:7:2:0:0:0:0:0:0:0:(type == 2)'
	
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
			if x[0] == lcn and x[1] == namespace and x[2] == nid and x[3] == tsid and x[4] == sid:
				return
		
		if lcn == 0:
			return
		
		for i in range(0, len(self.lcnlist)):
			if self.lcnlist[i][0] == lcn:
				if self.lcnlist[i][5] > signal:
					self.addLcnToList(namespace, nid, tsid, sid, lcn + 16536, signal)
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
					self.addLcnToList(znamespace, znid, ztsid, zsid, lcn + 16536, zsignal)
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
					print e

	def addMarker(self, position, text):
		self.markers.append([position, text])
		
	def read(self, serviceType):
		self.readE2Services(serviceType)
		
		try:
			f = open(self.dbfile)
		except Exception, e:
			print e
			return
		
		while True:
			line = f.readline()
			if line == "":
				break
				
			line = line.strip()
			#print line
			if len(line) != 38:
				continue
			
			tmp = line.split(":")
			if len(tmp) != 6:
				continue
			
			self.addLcnToList(int(tmp[0], 16), int(tmp[1], 16), int(tmp[2], 16), int(tmp[3], 16), int(tmp[4]), int(tmp[5]))
		
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
			refstr = '%s ORDER BY name'%(self.service_types_tv)
		elif serviceType == "RADIO":
			refstr = '%s ORDER BY name'%(self.service_types_radio)
		ref = eServiceReference(refstr)
		serviceHandler = eServiceCenter.getInstance()
		servicelist = serviceHandler.list(ref)
		if not servicelist is None:
			while True:
				service = servicelist.getNext()
				if not service.valid(): #check if end of list
					break
					
				unsigned_orbpos = service.getUnsignedData(4) >> 16
				if unsigned_orbpos == 0xEEEE: #Terrestrial
					self.e2services.append(service.toString())
					
	def writeTVBouquet(self):
		try:
			f = open('/etc/enigma2/userbouquet.terrestrial_lcn.tv', "w")
		except Exception, e:
			print e
			return

		self.newlist = []
		count = 0
		#for x in self.lcnlist:
			#print " LISTA LCN:", x
			
		for x in self.lcnlist:
			count += 1
			while x[0] != count:
				self.newlist.append([count, 11111111, 11111, 111, 111, 111111])
				count += 1
			if x[0] == count:
				self.newlist.append(x)

		#for x in self.e2services:
			#print " self.e2services:", x


		#for x in self.newlist:
			#print " NEW LIST LCN :", x
			
		#print " New LIST LEN: " , len(self.newlist)
			
		f.write("#NAME Terrestrial TV LCN\n")
		f.write("#SERVICE 1:64:0:0:0:0:0:0:0:0::Terrestrial TV LCN\n")
		f.write("##DESCRIPTION Terrestrial TV LCN\n")
		for x in self.newlist:
			if int(x[1]) == 11111111:
				#print x[0], " Detected 111111111111 service"
				f.write("#SERVICE 1:832:d:0:0:0:0:0:0:0:\n")
				continue
				
			if len(self.markers) > 0:
				if x[0] > self.markers[0][0]:
					f.write("#SERVICE 1:64:0:0:0:0:0:0:0:0:\n")
					f.write("#DESCRIPTION ------- " + self.markers[0][1] + " -------\n")
					self.markers.remove(self.markers[0])
			refstr = "1:0:1:%x:%x:%x:%x:0:0:0:" % (x[4],x[3],x[2],x[1]) # temporary ref
			refsplit = eServiceReference(refstr).toString().split(":")
			added = False
			for tref in self.e2services:
				tmp = tref.split(":")
				if tmp[3] == refsplit[3] and tmp[4] == refsplit[4] and tmp[5] == refsplit[5] and tmp[6] == refsplit[6]:
					f.write("#SERVICE " + tref + "\n")
					added = True
					break

			if not added: # no service found? something wrong? a log should be a good idea. Anyway we add an empty line so we keep the numeration
				f.write("#SERVICE 1:832:d:0:0:0:0:0:0:0:\n")

		f.close()
		self.addInTVBouquets()

	def addInTVBouquets(self):
		f = open('/etc/enigma2/bouquets.tv', 'r')
		ret = f.read().split("\n")
		f.close()
		
		i = 0
		while i < len(ret):
			if ret[i].find("userbouquet.terrestrial_lcn.tv") >= 0:
				return
			i += 1
			
		f = open('/etc/enigma2/bouquets.tv', 'w')
		f.write(ret[0]+"\n")
		f.write('#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.terrestrial_lcn.tv" ORDER BY bouquet\n')
		i = 1
		while i < len(ret):
			f.write(ret[i]+"\n")
			i += 1

	def writeRadioBouquet(self):
		try:
			f = open('/etc/enigma2/userbouquet.terrestrial_lcn.radio', "w")
		except Exception, e:
			print e
			return

		self.newlist = []
		count = 0
		#for x in self.lcnlist:
			#print " LISTA LCN:", x
			
		for x in self.lcnlist:
			count += 1
			while x[0] != count:
				self.newlist.append([count, 11111111, 11111, 111, 111, 111111])
				count += 1
			if x[0] == count:
				self.newlist.append(x)

		#for x in self.e2services:
			#print " self.e2services:", x


		#for x in self.newlist:
			#print " NEW LIST LCN :", x
			
		#print " New LIST LEN: " , len(self.newlist)
			
		f.write("#NAME Terrestrial Radio LCN\n")
		f.write("#SERVICE 1:64:0:0:0:0:0:0:0:0::Terrestrial RADIO LCN\n")
		f.write("##DESCRIPTION Terrestrial RADIO LCN\n")
		for x in self.newlist:
			if int(x[1]) == 11111111:
				#print x[0], " Detected 111111111111 service"
				f.write("#SERVICE 1:832:d:0:0:0:0:0:0:0:\n")
				continue
				
			if len(self.markers) > 0:
				if x[0] > self.markers[0][0]:
					f.write("#SERVICE 1:64:0:0:0:0:0:0:0:0:\n")
					f.write("#DESCRIPTION ------- " + self.markers[0][1] + " -------\n")
					self.markers.remove(self.markers[0])
			refstr = "1:0:2:%x:%x:%x:%x:0:0:0:" % (x[4],x[3],x[2],x[1]) # temporary ref
			refsplit = eServiceReference(refstr).toString().split(":")
			added = False
			for tref in self.e2services:
				tmp = tref.split(":")
				if tmp[3] == refsplit[3] and tmp[4] == refsplit[4] and tmp[5] == refsplit[5] and tmp[6] == refsplit[6]:
					f.write("#SERVICE " + tref + "\n")
					added = True
					break

			if not added: # no service found? something wrong? a log should be a good idea. Anyway we add an empty line so we keep the numeration
				f.write("#SERVICE 1:832:d:0:0:0:0:0:0:0:\n")

		f.close()
		self.addInRadioBouquets()
		
	def addInRadioBouquets(self):
		f = open('/etc/enigma2/bouquets.radio', 'r')
		ret = f.read().split("\n")
		f.close()
		
		i = 0
		while i < len(ret):
			if ret[i].find("userbouquet.terrestrial_lcn.radio") >= 0:
				return
			i += 1
			
		f = open('/etc/enigma2/bouquets.radio', 'w')
		f.write(ret[0]+"\n")
		f.write('#SERVICE 1:7:2:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.terrestrial_lcn.radio" ORDER BY bouquet\n')
		i = 1
		while i < len(ret):
			f.write(ret[i]+"\n")
			i += 1
			
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
		config.lcn.bouquet = ConfigSelection(default = "userbouquet.LastScanned.tv", choices = self.bouquetlist)
		config.lcn.rules = ConfigSelection(self.rulelist)

	def readBouquetsTvList(self, pwd):
		return self.readBouquetsList(pwd, "bouquets.tv")

	def readBouquetsRadioList(self, pwd):
		return self.readBouquetsList(pwd, "bouquets.radio")

	def readBouquetsList(self, pwd, bouquetname):
		try:
			f = open(pwd + "/" + bouquetname)
		except Exception, e:
			print e
			return
			
		ret = []
		
		while True:
			line = f.readline()
			if line == "":
				break
				
			if line[:8] != "#SERVICE":
				continue
				
			tmp = line.strip().split(":")
			line = tmp[len(tmp)-1]
			
			filename = None
			if line[:12] == "FROM BOUQUET":
				tmp = line[13:].split(" ")
				filename = tmp[0].strip("\"")
			else:
				filename = line
				
			if filename:
				try:
					fb = open(pwd + "/" + filename)
				except Exception, e:
					print e
					continue
					
				tmp = fb.readline().strip()
				if tmp[:6] == "#NAME ":
					ret.append([filename, tmp[6:]])
				else:
					ret.append([filename, filename])
				fb.close()
				
		return ret
		
	def buildAfterScan(self):
		if config.lcn.enabled.value == True:
			self.buildlcn(True)
		
	def buildlcn(self, suppressmessages = False):
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

		ConfigListScreen.__init__(self, self.list, session = session)
		self["key_red"] = Button(_("Rebuild"))
		self["key_green"] = Button(_("Exit"))
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
				{
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
		if config.lcn.enabled.value == True:
			self.session.openWithCallback(self.confirm, MessageBox, _("Rebuild LCN bouquet now?"), MessageBox.TYPE_YESNO, default = True)
		else:
			self.keySave()
			configfile.save()
			
def LCNScannerMain(session, **kwargs):
	session.open(LCNScannerPlugin)
	
def LCNScannerSetup(menuid, **kwargs):
	if menuid == "scan":
		return [("LCN Scanner", LCNScannerMain, "lcnscanner", None)]
	else:
		return []

def Plugins(**kwargs):
	return PluginDescriptor(name="LCN", description=_("LCN plugin for DVB-T/T2 services"), where = PluginDescriptor.WHERE_MENU, fnc=LCNScannerSetup)
	#return PluginDescriptor(name="LCN", description=_("LCN plugin for DVB-T/T2 services"), where = PluginDescriptor.WHERE_PLUGINMENU, fnc=LCNScannerMain)
