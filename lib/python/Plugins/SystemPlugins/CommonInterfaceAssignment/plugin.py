from Screens.Screen import Screen
from Screens.ChannelSelection import *
from Components.ActionMap import HelpableActionMap, ActionMap, NumberActionMap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.config import ConfigNothing
from Components.ConfigList import ConfigList
from Components.Label import Label
from Components.SelectionList import SelectionList
from Components.MenuList import MenuList
from ServiceReference import ServiceReference
from Plugins.Plugin import PluginDescriptor
from xml.etree.cElementTree import parse as ci_parse
from Tools.XMLTools import elementsWithTag, mergeText, stringToXML
from enigma import eDVBCI_UI, eDVBCIInterfaces

from os import system, path as os_path

class CIselectMainMenu(Screen):
	skin = """
		<screen position="205,150" size="310,270"  title="CI Assignment" >
			<widget name="CiList" position="10,10" size="290,200" scrollbarMode="showOnDemand" />
			<ePixmap position="10,210" size="290,2" pixmap="skin_default/div-h.png" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/red.png" position="10,220" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="160,220" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="10,220" zPosition="1" size="140,40" font="Regular;19" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="160,220" zPosition="1" size="140,40" font="Regular;19" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		</screen>"""

	def __init__(self, session, args = 0):
		self.skin = CIselectMainMenu.skin
		Screen.__init__(self, session)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Config"))

		self["actions"] = ActionMap(["ColorActions","SetupActions"],
			{
				"green": self.greenPressed,
				"red": self.redPressed,
				"yellow": self.yellowPressed,
				"ok": self.greenPressed,
				"cancel": self.cancel
			}, -1)

		NUM_CI=eDVBCIInterfaces.getInstance().getNumOfSlots()

		print "[CI_Wizzard] FOUND %d CI Slots " % NUM_CI

		self.dlg = None
		self.state = { }
		self.list = [ ]
		if NUM_CI > 0:
			for slot in range(NUM_CI):
				state = eDVBCI_UI.getInstance().getState(slot)
				if state == 0:
					appname = _("Slot %d") %(slot+1) + " - " + _("no module")
				elif state == 1:	
					appname = _("Slot %d") %(slot+1) + " - " + _("init modules")
				elif state == 2:
					appname = _("Slot %d") %(slot+1) + " - " + eDVBCI_UI.getInstance().getAppName(slot)
				self.list.append( (appname, ConfigNothing(), 0, slot) )
		else:
			self.list.append( (_("no CI slots found") , ConfigNothing(), 1, -1) )

		menuList = ConfigList(self.list)
		menuList.list = self.list
		menuList.l.setList(self.list)
		self["CiList"] = menuList

	def greenPressed(self):
		cur = self["CiList"].getCurrent()
		if cur and len(cur) > 2:
			action = cur[2]
			slot = cur[3]
			if action == 1:
				print "[CI_Wizzard] there is no CI Slot in your receiver"
			else:
				print "[CI_Wizzard] selected CI Slot : %d" % slot
				if config.usage.setup_level.index > 1: # advanced
					self.session.open(CIconfigMenu, slot)
				else:
					self.session.open(easyCIconfigMenu, slot)

	def yellowPressed(self):
		NUM_CI=eDVBCIInterfaces.getInstance().getNumOfSlots()
		print "[CI_Check] FOUND %d CI Slots " % NUM_CI
		if NUM_CI > 0:
			for ci in range(NUM_CI):
				print eDVBCIInterfaces.getInstance().getDescrambleRules(ci)
#		else:
#			print "no ci found"

	def redPressed(self):
		print "[CI_Config] RED BUTTON not implemented yet - only use self.cancel()"
		self.cancel()

	def cancel(self):
		self.close()

class CIconfigMenu(Screen):
	skin = """
		<screen position="60,80" size="595,436" title="CI Assignment" >
			<widget name="CAidList.desc" position="10,10" size="575,22" font="Regular;20" />
			<widget name="CAidList" position="10,40" size="575,45" font="Regular;20" />
			<widget name="ServiceList.desc" position="10,90" size="575,22" font="Regular;20" />
			<widget name="ServiceList" position="10,120" size="575,250" scrollbarMode="showOnDemand" />
			<ePixmap position="10,380" size="575,2" pixmap="skin_default/div-h.png" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/red.png" position="10,390" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="155,390" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="300,390" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="445,390" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="10,390" zPosition="1" size="140,40" font="Regular;19" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="155,390" zPosition="1" size="140,40" font="Regular;19" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="300,390" zPosition="1" size="140,40" font="Regular;19" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_blue" render="Label" position="445,390" zPosition="1" size="140,40" font="Regular;19" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		</screen>"""

	def __init__(self, session, ci_slot="9"):
		self.skin = CIconfigMenu.skin
		Screen.__init__(self, session)
		self.ci_slot=ci_slot
		self.filename="/etc/enigma2/ci"+str(self.ci_slot)+".xml"
		
		self["key_red"] = StaticText(_("delete"))
		self["key_green"] = StaticText(_("add Service"))
		self["key_yellow"] = StaticText(_("add Provider"))
		self["key_blue"] = StaticText(_("select CAId"))
		self["CAidList.desc"] = Label(_("assigned CAIds"))
		self["ServiceList.desc"] = Label(_("assigned Services/Provider"))

		self["actions"] = ActionMap(["ColorActions","SetupActions"],
			{
				"green": self.greenPressed,
				"red": self.redPressed,
				"yellow": self.yellowPressed,
				"blue": self.bluePressed,
				"ok": self.okPressed,
				"cancel": self.cancel
			}, -1)
			
		print "[CI_Wizzard_Config] Configuring CI Slots : %d  " % self.ci_slot

		i=0
		self.caidlist=[]
		print eDVBCIInterfaces.getInstance().readCICaIds(self.ci_slot)
		for caid in eDVBCIInterfaces.getInstance().readCICaIds(self.ci_slot):
			i+=1
			self.caidlist.append((str(hex(int(caid))),str(caid),i))

		print "[CI_Wizzard_Config_CI%d] read following CAIds from CI: %s" %(self.ci_slot, self.caidlist)
		self.selectedcaid =[]
		self.servicelist = []
		self.caids=_("no CAId selected")
		self["CAidList"] = Label(self.caids)

		serviceList = ConfigList(self.servicelist)
		serviceList.list = self.servicelist
		serviceList.l.setList(self.servicelist)
		self["ServiceList"] = serviceList

		self.loadXML()
		# if config mode !=advanced autoselect any caid
		if config.usage.setup_level.index <= 1: # advanced
			self.selectedcaid=self.caidlist

	def redPressed(self):
		self.delete()

	def greenPressed(self):
		self.session.openWithCallback( self.finishedChannelSelection, myChannelSelection, None)

	def yellowPressed(self):
		self.session.openWithCallback( self.finishedProviderSelection, myProviderSelection, None)

	def bluePressed(self):
		self.session.openWithCallback(self.finishedCAidSelection, CAidSelect, self.caidlist, self.selectedcaid)

	def okPressed(self):
		print "[CI_Config_CI%d] OK BUTTON not implemented yet" %self.ci_slot

	def cancel(self):
		self.saveXML()
		activate_all(self)
		self.close()

	def delete(self):
		cur = self["ServiceList"].getCurrent()
		if cur and len(cur) > 2:
			self.servicelist.remove(cur)
		self["ServiceList"].l.setList(self.servicelist)

	def finishedChannelSelection(self, *args):
		if len(args):
			ref=args[0]
			service_ref = ServiceReference(ref)
			service_name = service_ref.getServiceName()
			if find_in_list(self.servicelist, service_name, 0)==False:
				split_ref=service_ref.ref.toString().split(":")
				if split_ref[0] == "1":			#== dvb service und nicht muell von None
					self.servicelist.append( (service_name , ConfigNothing(), 0, service_ref.ref.toString()) )
					self["ServiceList"].l.setList(self.servicelist)

	def finishedProviderSelection(self, *args):
		if len(args)>1: # bei nix selected kommt nur 1 arg zurueck (==None)
			name=args[0]
			dvbnamespace=args[1]
			if find_in_list(self.servicelist, name, 0)==False:
				self.servicelist.append( (name , ConfigNothing(), 1, dvbnamespace) )
				self["ServiceList"].l.setList(self.servicelist)

	def finishedCAidSelection(self, *args):
		if len(args):
			self.selectedcaid=args[0]
			self.caids=""
			for item in self.selectedcaid:
				if len(self.caids):
					self.caids+= ", " + item[0]
				else:
					self.caids=item[0]
		else:
			self.selectedcaid=[]
			self.caids=_("no CAId selected")
		self["CAidList"].setText(self.caids)

	def saveXML(self):
		try:
			fp = file(self.filename, 'w')
			fp.write("<?xml version=\"1.0\" encoding=\"utf-8\" ?>\n")
			fp.write("<ci>\n")
			fp.write("\t<slot>\n")
			fp.write("\t\t<id>%s</id>\n" % self.ci_slot)
			for item in self.selectedcaid:
				if len(self.selectedcaid):
					fp.write("\t\t<caid id=\"%s\" />\n" % item[0])
			for item in self.servicelist:
				if len(self.servicelist):
					if item[2]==1:
						fp.write("\t\t<provider name=\"%s\" dvbnamespace=\"%s\" />\n" % (item[0], item[3]))
					else:
						fp.write("\t\t<service name=\"%s\" ref=\"%s\" />\n"  % (item[0], item[3]))
			fp.write("\t</slot>\n")
			fp.write("</ci>\n")
			fp.close()
		except:
			print "[CI_Config_CI%d] xml not written" %self.ci_slot
			os.unlink(self.filename)

	def loadXML(self):
		if not os_path.exists(self.filename):
			return

		def getValue(definitions, default):
			ret = ""
			Len = len(definitions)
			return Len > 0 and definitions[Len-1].text or default

		try:
			tree = ci_parse(self.filename).getroot()
			self.read_services=[]
			self.read_providers=[]
			self.usingcaid=[]
			self.ci_config=[]
#			for ci in tree.findall("ci"):
			for slot in tree.findall("slot"):
				read_slot = getValue(slot.findall("id"), False).encode("UTF-8")
				print "ci " + read_slot

				i=0
				for caid in slot.findall("caid"):
					read_caid = caid.get("id").encode("UTF-8")
					self.selectedcaid.append((str(read_caid),str(read_caid),i))
					self.usingcaid.append(long(read_caid,16))
					i+=1

				for service in  slot.findall("service"):
					read_service_name = service.get("name").encode("UTF-8")
					read_service_ref = service.get("ref").encode("UTF-8")
					self.read_services.append (read_service_ref)

				for provider in  slot.findall("provider"):
					read_provider_name = provider.get("name").encode("UTF-8")
					read_provider_dvbname = provider.get("dvbnamespace").encode("UTF-8")
					self.read_providers.append((read_provider_name,read_provider_dvbname))

				self.ci_config.append((int(read_slot), (self.read_services, self.read_providers, self.usingcaid)))
		except:
			print "[CI_Config_CI%d] error parsing xml..." %self.ci_slot

		for item in self.read_services:
			if len(item):
				self.finishedChannelSelection(item)

		for item in self.read_providers:
			if len(item):
				self.finishedProviderSelection(item[0],item[1])

		print self.ci_config
		self.finishedCAidSelection(self.selectedcaid)
		self["ServiceList"].l.setList(self.servicelist)

class easyCIconfigMenu(CIconfigMenu):
	skin = """
		<screen position="80,80" size="470,420" title="CI Assignment" >
			<widget name="ServiceList.desc" position="10,10" size="420,22" font="Regular;20" />
			<widget name="ServiceList" position="10,40" size="450,340" scrollbarMode="showOnDemand" />
			<ePixmap position="10,360" size="450,2" pixmap="skin_default/div-h.png" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/red.png" position="10,370" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="160,370" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="310,370" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="10,370" zPosition="1" size="140,40" font="Regular;19" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="160,370" zPosition="1" size="140,40" font="Regular;19" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="310,370" zPosition="1" size="140,40" font="Regular;19" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		</screen>"""

	def __init__(self, session, ci_slot="9"):
		ci=ci_slot
		CIconfigMenu.__init__(self, session, ci_slot)
		self.skin = easyCIconfigMenu.skin
	
		self["actions"] = ActionMap(["ColorActions","SetupActions"],
		{
			"green": self.greenPressed,
			"red": self.redPressed,
			"yellow": self.yellowPressed,
			"blue": self.bluePressed,
			"ok": self.okPressed,
			"cancel": self.cancel
		}, -1)
	
	def bluePressed(self):
		print "do nothing"

class CAidSelect(Screen):
	skin = """
		<screen position="210,140" size="310,290"  title="select CAId's" >
			<widget name="list" position="10,10" size="290,210" scrollbarMode="showOnDemand" />
			<ePixmap position="10,230" size="290,2" pixmap="skin_default/div-h.png" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/red.png" position="10,240" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="160,240" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="10,240" zPosition="1" size="140,40" font="Regular;19" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="160,240" zPosition="1" size="140,40" font="Regular;19" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		</screen>"""
	
	def __init__(self, session, list, selected_caids):
		self.skin = CAidSelect.skin
		Screen.__init__(self, session)

		self.list = SelectionList()
		self["list"] = self.list

		for listindex in range(len(list)):
			if find_in_list(selected_caids,list[listindex][0],0):
				self.list.addSelection(list[listindex][0], list[listindex][1], listindex, True)
			else:
				self.list.addSelection(list[listindex][0], list[listindex][1], listindex, False)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))

		self["actions"] = ActionMap(["ColorActions","SetupActions"],
		{
			"ok": self.list.toggleSelection, 
			"cancel": self.cancel, 
			"green": self.greenPressed,
			"red": self.cancel
		}, -1)

	def greenPressed(self):
		list = self.list.getSelectionsList()
		print list
		self.close(list)

	def cancel(self):
		self.close()

class myProviderSelection(ChannelSelectionBase):
	skin = """
		<screen position="80,80" size="560,430" title="Select provider to add...">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
			<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="key_yellow" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget name="key_blue" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
			<widget name="list" position="00,45" size="560,364" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, title):
		ChannelSelectionBase.__init__(self, session)
		self.onShown.append(self.__onExecCallback)

		self["actions"] = ActionMap(["OkCancelActions", "ChannelSelectBaseActions"],
			{
				"showFavourites": self.doNothing,
				"showAllServices": self.doNothing,
				"showProviders": self.doNothing,
				"showSatellites": self.doNothing,
				"cancel": self.cancel,
				"ok": self.channelSelected,
			})
		self["key_red"] = StaticText(_(""))
		self["key_green"] = StaticText(_(""))
		self["key_yellow"] = StaticText(_(""))
		self["key_blue"] = StaticText(_(""))

	def doNothing(self):
		print "nothing to do..."

	def __onExecCallback(self):
		self.showSatellites()

	def channelSelected(self): # just return selected service
		ref = self.getCurrentSelection()
		splited_ref=ref.toString().split(":")
		if ref.flags == 7 and splited_ref[6] != "0":
			self.dvbnamespace=splited_ref[6]
			self.enterPath(ref)
		else:
			self.close(ref.getName(), self.dvbnamespace)

	def showSatellites(self):
		if not self.pathChangeDisabled:
			refstr = '%s FROM SATELLITES ORDER BY satellitePosition'%(self.service_types)
			if not self.preEnterPath(refstr):
				ref = eServiceReference(refstr)
				justSet=False
				prev = None

				if self.isBasePathEqual(ref):
					if self.isPrevPathEqual(ref):
						justSet=True
					prev = self.pathUp(justSet)
				else:
					currentRoot = self.getRoot()
					if currentRoot is None or currentRoot != ref:
						justSet=True
						self.clearPath()
						self.enterPath(ref, True)
				if justSet:
					serviceHandler = eServiceCenter.getInstance()
					servicelist = serviceHandler.list(ref)
					if not servicelist is None:
						while True:
							service = servicelist.getNext()
							if not service.valid(): #check if end of list
								break
							unsigned_orbpos = service.getUnsignedData(4) >> 16
							orbpos = service.getData(4) >> 16
							if orbpos < 0:
								orbpos += 3600
							if service.getPath().find("FROM PROVIDER") != -1:
								service_type = _("Providers")
								try:
									# why we need this cast?
									service_name = str(nimmanager.getSatDescription(orbpos))
								except:
									if unsigned_orbpos == 0xFFFF: #Cable
										service_name = _("Cable")
									elif unsigned_orbpos == 0xEEEE: #Terrestrial
										service_name = _("Terrestrial")
									else:
										if orbpos > 1800: # west
											orbpos = 3600 - orbpos
											h = _("W")
										else:
											h = _("E")
										service_name = ("%d.%d" + h) % (orbpos / 10, orbpos % 10)
								service.setName("%s - %s" % (service_name, service_type))
								self.servicelist.addService(service)
						self.servicelist.finishFill()
						if prev is not None:
							self.setCurrentSelection(prev)

	def cancel(self):
		self.close(None)

class myChannelSelection(ChannelSelectionBase):
	skin = """
		<screen position="80,80" size="560,430" title="Select service to add...">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
			<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="key_yellow" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget name="key_blue" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
			<widget name="list" position="00,45" size="560,364" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, title):
		ChannelSelectionBase.__init__(self, session)
		self.onShown.append(self.__onExecCallback)
		service = self.session.nav.getCurrentService()
		if service:
			info = service.info()
			if info:
				refstr = info.getInfoString(iServiceInformation.sServiceref)
				self.servicelist.setPlayableIgnoreService(eServiceReference(refstr))

		self["actions"] = ActionMap(["OkCancelActions", "TvRadioActions", "ChannelSelectBaseActions"],
			{
				"showProviders": self.doNothing,
				"showSatellites": self.doNothing,
				"cancel": self.cancel,
				"ok": self.channelSelected,
				"keyRadio": self.setModeRadio,
				"keyTV": self.setModeTv
			})

		self["key_green"] = StaticText(_(""))
		self["key_yellow"] = StaticText(_(""))

	def __onExecCallback(self):
		self.setModeTv()

	def doNothing(self):
		print "nothing to do..."

	def channelSelected(self): # just return selected service
		ref = self.getCurrentSelection()
		if (ref.flags & 7) == 7:
			self.enterPath(ref)
		elif not (ref.flags & eServiceReference.isMarker):
			ref = self.getCurrentSelection()
			self.close(ref)

	def setModeTv(self):
		self.setTvMode()
		self.showFavourites()

	def setModeRadio(self):
		self.setRadioMode()
		self.showFavourites()

	def cancel(self):
		self.close(None)

def activate_all(session):
	NUM_CI=eDVBCIInterfaces.getInstance().getNumOfSlots()
	print "[CI_Activate] FOUND %d CI Slots " % NUM_CI
	if NUM_CI > 0:
		ci_config=[]
		def getValue(definitions, default):
			# Initialize Output
			ret = ""
			# How many definitions are present
			Len = len(definitions)
			return Len > 0 and definitions[Len-1].text or default	

		for ci in range(NUM_CI):
			filename="/etc/enigma2/ci"+str(ci)+".xml"

			if not os_path.exists(filename):
				print "[CI_Activate_Config_CI%d] no config file found" %ci

			try:
				tree = ci_parse(filename).getroot()
				read_services=[]
				read_providers=[]
				usingcaid=[]
				for slot in tree.findall("slot"):
					read_slot = getValue(slot.findall("id"), False).encode("UTF-8")

					for caid in slot.findall("caid"):
						read_caid = caid.get("id").encode("UTF-8")
						usingcaid.append(long(read_caid,16))

					for service in slot.findall("service"):
						read_service_ref = service.get("ref").encode("UTF-8")
						read_services.append (read_service_ref)

					for provider in slot.findall("provider"):
						read_provider_name = provider.get("name").encode("UTF-8")
						read_provider_dvbname = provider.get("dvbnamespace").encode("UTF-8")
						read_providers.append((read_provider_name,long(read_provider_dvbname,16)))

					ci_config.append((int(read_slot), (read_services, read_providers, usingcaid)))
			except:
				print "[CI_Activate_Config_CI%d] error parsing xml..." %ci

		for item in ci_config:
			print "[CI_Activate] activate CI%d with following settings:" %item[0]
			print item[0]
			print item[1]
			try:
				eDVBCIInterfaces.getInstance().setDescrambleRules(item[0],item[1])
			except:
				print "[CI_Activate_Config_CI%d] error setting DescrambleRules..." %item[0]

def find_in_list(list, search, listpos=0):
	for item in list:
		if item[listpos]==search:
			return True
	return False

global_session = None

def sessionstart(reason, session):
	global global_session
	global_session = session

def autostart(reason, **kwargs):
	global global_session
	if reason == 0:
		print "[CI_Assignment] activating ci configs:"
		activate_all(global_session)
	elif reason == 1:
		global_session = None

def main(session, **kwargs):
	session.open(CIselectMainMenu)

def menu(menuid, **kwargs):
	if menuid == "setup" and eDVBCIInterfaces.getInstance().getNumOfSlots():
		return [(_("Common Interface Assignment"), main, "ci_assign", 11)]
	return [ ]

def Plugins(**kwargs):
	if config.usage.setup_level.index > 1:
		return [PluginDescriptor( where = PluginDescriptor.WHERE_SESSIONSTART, fnc = sessionstart ),
				PluginDescriptor( where = PluginDescriptor.WHERE_AUTOSTART, fnc = autostart ),
				PluginDescriptor( name = "CommonInterfaceAssignment", description = _("a gui to assign services/providers/caids to common interface modules"), where = PluginDescriptor.WHERE_MENU, fnc = menu )]
	else:
		return [PluginDescriptor( where = PluginDescriptor.WHERE_SESSIONSTART, fnc = sessionstart ),
				PluginDescriptor( where = PluginDescriptor.WHERE_AUTOSTART, fnc = autostart ),
				PluginDescriptor( name = "CommonInterfaceAssignment", description = _("a gui to assign services/providers to common interface modules"), where = PluginDescriptor.WHERE_MENU, fnc = menu )]
