# Volume Adjust 
# 2009 Black_64
#
# FIXED SERVICELIST GREENSCREEN BY SCOPE34 (AN)
# ADD AC3 SUPPORT BY BLACK_64

from Screens.Screen import Screen
from Screens.ChannelSelection import *
from Components.ActionMap import HelpableActionMap, ActionMap, NumberActionMap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.config import ConfigInteger, ConfigNothing, getConfigListEntry, ConfigNumber, ConfigYesNo
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.Label import Label
from Components.SelectionList import SelectionList
from Components.MenuList import MenuList
from ServiceReference import ServiceReference
from Plugins.Plugin import PluginDescriptor
from xml.etree.cElementTree import parse as ci_parse
from Tools.XMLTools import elementsWithTag, mergeText, stringToXML
from enigma import *
from os import system, path as os_path
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase
global ListChange
ListChange = None
config.Volume  = ConfigSubsection()
config.Volume.Enabled = ConfigYesNo(default=False)
config.Volume.AC3_vol  = ConfigInteger(default=10, limits=(0, 99))


class Volume_adjust(Screen):
	skin = """
		<screen position="center,center" size="595,456" title="Volume Adjust" >
			<widget name="ServiceList.desc" position="10,30" size="575,22" font="Regular;20" />
			<widget name="ServiceList" position="10,70" size="575,250" scrollbarMode="showOnDemand" />
			<ePixmap position="10,330" size="575,2" pixmap="skin_default/div-h.png" transparent="1" alphatest="on" />
			<ePixmap position="10,400" size="575,2" pixmap="skin_default/div-h.png" transparent="1" alphatest="on" />
			<widget source="press_menu" render="Label" position="10,330" zPosition="1" size="575,70" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<eLabel backgroundColor="red" position="10,447" size="140,3" zPosition="0" />
			<eLabel backgroundColor="green" position="155,447" size="140,3" zPosition="0" />
			<eLabel backgroundColor="yellow" position="300,447" size="140,3" zPosition="0" />
			<eLabel backgroundColor="blue" position="445,447" size="140,3" zPosition="0" />
			<widget source="key_red" render="Label" position="10,425" zPosition="1" size="140,22" font="Regular;18" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_green" render="Label" position="155,426" zPosition="1" size="140,22" font="Regular;18" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="300,425" zPosition="1" size="140,22" font="Regular;18" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_blue" render="Label" position="445,406" zPosition="1" size="140,40" font="Regular;18" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		</screen>"""

	def __init__(self, session):
		self.skin = Volume_adjust.skin
		Screen.__init__(self, session)
		# Path of the config file
		self.filename="/etc/volume.xml"
		global offset
		offset = 0
		self["key_red"] = StaticText(_("delete"))
		self["key_green"] = StaticText(_("add Service"))
		self["key_yellow"] = StaticText(_("change"))
		self["key_blue"] = StaticText(_("add Current"))
		self["press_menu"] = StaticText(_("press the menu button to set a general AC3/Dolby offset"))
		self["ServiceList.desc"] = Label(_("Channel \t\t\tVolume +"))

		self["actions"] = ActionMap(["ColorActions","OkCancelActions","MenuActions"],
			{
				"green": self.greenPressed,
				"red": self.redPressed,
				"yellow": self.yellowPressed,
				"blue": self.bluePressed,
				"menu": self.config_menu,
				"ok": self.okPressed,
				"cancel": self.cancel
			}, -1)

		self.servicelist = []
		self.read_volume=[]
		serviceList = ConfigList(self.servicelist)
		serviceList.list = self.servicelist
		serviceList.l.setList(self.servicelist)
		self["ServiceList"] = serviceList

		self.loadXML() # load the config file
		self.onShown.append(self.setWindowTitle)

	def setWindowTitle(self):
		self.setTitle(_("Volume Adjust"))

	def redPressed(self):
		# remove current line of the list
		self.delete()

	def greenPressed(self):
		# select service (shows the channel list)
		self.session.openWithCallback( self.finishedChannelSelection, mySmallChannelSelection, None)

	def yellowPressed(self):
		self.okPressed()

	def bluePressed(self):
		self.service = self.session.nav.getCurrentlyPlayingServiceReference()
		if not self.service is None:
			service = self.service.toCompareString()
			service_name = ServiceReference(self.service).getServiceName().replace('\xc2\x87', '').replace('\xc2\x86', '')
			service_name = service_name + '\t\t\t0'
			self.servicelist.append( (service_name , ConfigNothing(), 0, service))
			self.read_volume.append('0')
			offset = 0
			self.session.openWithCallback( self.VolumeChanged, Change_volume, service_name, offset)

	def config_menu(self):
		self.session.open(Volume_Config)

	def okPressed(self):
		# change the volume offset
		if len(self.servicelist):
			cur = self["ServiceList"].getCurrentIndex()
			global offset
			offset = int(self.read_volume[cur])
			tmp = self.servicelist[cur]
			service_name = tmp[0][0:-3].strip()
			self.session.openWithCallback( self.Change_vol_now, Change_volume, service_name, offset)

	def cancel(self):
		self.saveXML()
		self.close()

	def delete(self):
		cur = self["ServiceList"].getCurrent()
		cur1 = self["ServiceList"].getCurrentIndex()
		if cur and len(cur) > 2:
			self.servicelist.remove(cur)
			self.read_volume.remove(self.read_volume[cur1])
		self["ServiceList"].l.setList(self.servicelist)

	def finishedChannelSelection(self, *args):
		# update screen
		if len(args):
			ref=args[0]
			service_ref = ServiceReference(ref)
			service_name = service_ref.getServiceName()
			if find_in_list(self.servicelist, service_name, 0)==False:
				split_ref=service_ref.ref.toString().split(":")
				if split_ref[0] == "1":
					t = len(self.servicelist)
					k = len(self.read_volume)
					if t == k:
						global offset
						offset = 0
						self.session.openWithCallback( self.VolumeChanged, Change_volume, service_name, offset)
						self.read_volume.append (str(offset))
					service_name = service_name + self.Tabs(service_name) + self.read_volume[t]
					self.servicelist.append( (service_name , ConfigNothing(), 0, service_ref.ref.toString()))
					self["ServiceList"].l.setList(self.servicelist)

	def VolumeChanged(self, *args):
		# change volume offset after new entry
		global offset
		t = len(self.servicelist)
		tmp = self.servicelist[t-1]
		tmp0 = tmp[0][0:-3].strip()
		self.read_volume[t-1] = str(offset)
		service_name = tmp0 + self.Tabs(tmp0) + str(offset)
		self.servicelist[t-1] = ( (service_name , ConfigNothing(), 0, tmp[3]))
		self["ServiceList"].l.setList(self.servicelist)

	def Change_vol_now(self, *args):
		# change volume offset after selection in list
		global offset
		t = self["ServiceList"].getCurrentIndex()
		tmp = self.servicelist[t]
		tmp0 = tmp[0][0:-3].strip()
		self.read_volume[t] = str(offset)
		service_name = tmp0 + self.Tabs(tmp0) + str(offset)
		self.servicelist[t] = ( (service_name , ConfigNothing(), 0, tmp[3]))
		self["ServiceList"].l.setList(self.servicelist)

	def Tabs(self, name):
		# remove escape chars and check lenght
		k = 0
		for let in name:
			if ord(let) > 1 and ord(let) < 128:
				k+=1
		print '[Volume Adjust] length service name = ' + str(k)
		if k > 28:
			return '\t'
		elif k > 18:
			return '\t\t'
		else:
			return '\t\t\t'

	def saveXML(self):
		# save the config file
		global ListChange
		ListChange = True
		try:
			fp = file(self.filename, 'w')
			fp.write("<?xml version=\"1.0\" encoding=\"utf-8\" ?>\n")
			fp.write("<adjustlist>\n")
			fp.write("\t<channels>\n")
			fp.write("\t\t<id>%s</id>\n" % 'services')
			t=0
			for item in self.servicelist:
				if len(self.servicelist):
					# remove the volume offset from service name
					tmp = item[0]
					tmp = tmp[0:-3].strip()
					# write line in the XML file
					if item[2]==1:
						fp.write("\t\t<provider name=\"%s\" dvbnamespace=\"%s\" volume=\"%s\" />\n" % (tmp, item[3], self.read_volume[t]))
					else:
						fp.write("\t\t<service name=\"%s\" ref=\"%s\" volume=\"%s\" />\n"  % (tmp, item[3], self.read_volume[t]))
					t+=1
			fp.write("\t</channels>\n")
			fp.write("</adjustlist>\n")
			fp.close()
		except:
			#os.unlink(self.filename) # gives a GS WHY ???
			print "[Volume Adjust] error writing xml..."

	def loadXML(self):
		print "[Volume Adjust] load xml..."
		if not os_path.exists(self.filename):
			return
		self.read_services=[]
		self.read_volume=[]
		try:
			tree = ci_parse(self.filename).getroot()
			for channels in tree.findall("channels"):
				for service in  channels.findall("service"):
					read_service_name = service.get("name").encode("UTF-8")
					read_service_ref = service.get("ref").encode("UTF-8")
					read_service_volume = service.get("volume").encode("UTF-8")
					self.read_services.append (read_service_ref)
					self.read_volume.append (read_service_volume)
		except:
			print "[Volume Adjust] error parsing xml..."

		for item in self.read_services:
			if len(item):
				self.finishedChannelSelection(item)
		self["ServiceList"].l.setList(self.servicelist)

class Change_volume(ConfigListScreen, Screen):
	skin = """
		<screen position="center,center" size="310,190"  title="Change Volume offset" >
			<widget name="config" position="10,10" size="290,210" scrollbarMode="showOnDemand" />
			<ePixmap position="10,130" size="290,2" pixmap="skin_default/div-h.png" transparent="1" alphatest="on" />
			<eLabel backgroundColor="red" position="10,181" size="90,3" zPosition="0" />
			<eLabel backgroundColor="green" position="110,181" size="90,3" zPosition="0" />
			<eLabel backgroundColor="yellow" position="210,181" size="90,3" zPosition="0" />
			<widget source="key_red" render="Label" position="10,158" zPosition="1" size="90,22" font="Regular;19" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_green" render="Label" position="110,158" zPosition="1" size="90,22" font="Regular;19" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="210,158" zPosition="1" size="90,22" font="Regular;19" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		</screen>"""

	def __init__(self, session, name, vol):
		self.skin = Change_volume.skin
		Screen.__init__(self, session)
		self.offset = ConfigNumber(default="0")
		global offset
		self.offset.setValue(str(offset))
		self.Clist = []
		self.Clist.append(getConfigListEntry(_(name), self.offset))
		ConfigListScreen.__init__(self, self.Clist)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Ok"))
		self["key_yellow"] = StaticText(_("+/-"))
		self["actions"] = ActionMap(["ColorActions","SetupActions"],
		{
			"ok": self.ok, 
			"cancel": self.cancel, 
			"green": self.greenPressed,
			"red": self.cancel,
			"yellow": self.yellowPressed,
		}, -2)
		self.onShown.append(self.setWindowTitle)

	def setWindowTitle(self):
		self.setTitle(_("Change Volume offset"))

	def greenPressed(self):
		global offset
		offset  = self.offset.value
		self.close()

	def yellowPressed(self):
		global offset
		offset  = self.offset.value * -1
		self.offset.setValue(str(offset))
		self["config"].list = self.Clist
		self["config"].l.setList(self.Clist)

	def ok(self):
		self.greenPressed()

	def cancel(self):
		self.close()

class mySmallChannelSelection(ChannelSelectionBase):

	skin = """
		<screen position="center,center" size="560,430" title="Select service to add...">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" />
			<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" />
			<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" />
			<widget name="key_yellow" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" />
			<widget name="key_blue" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" />
			<widget name="list" position="00,45" size="560,364" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, title):
		self.skin = mySmallChannelSelection.skin
		ChannelSelectionBase.__init__(self, session)
		self.onShown.append(self.__onExecCallback)
		self.bouquet_mark_edit = OFF
		service = self.session.nav.getCurrentService()
		if service:
			info = service.info()
			if info:
				refstr = info.getInfoString(iServiceInformation.sServiceref)
				self.servicelist.setPlayableIgnoreService(eServiceReference(refstr))
		self["actions"] = ActionMap(["OkCancelActions", "TvRadioActions", "ChannelSelectBaseActions"],
			{
				"cancel": self.cancel,
				"ok": self.channelSelected,
				"keyRadio": self.setModeRadio,
				"keyTV": self.setModeTv
			})

	def __onExecCallback(self):
		self.setModeTv()
		self.setTitle(_("Select service to add..."))

	def channelSelected(self):
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

def find_in_list(list, search, listpos=0):
	# check for double entry's in list (only service name)
	for item in list:
		tmp = item[listpos]
		tmp0 = tmp[0:-3].strip()
		if tmp0==search:
			return True
	return False

class Volume_Config(ConfigListScreen, Screen):
	skin = """
		<screen position="center,center" size="360,210"  title="Volume Config" >
			<widget name="config" position="10,10" size="340,75" scrollbarMode="showOnDemand" />
			<ePixmap position="10,80" size="340,2" pixmap="skin_default/div-h.png" transparent="1" alphatest="on" />
			<widget source="infotext" render="Label" position="10,80" zPosition="1" size="340,70" font="Regular;19" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<ePixmap position="10,150" size="340,2" pixmap="skin_default/div-h.png" transparent="1" alphatest="on" />
			<eLabel backgroundColor="red" position="20,201" size="100,3" zPosition="0" />
			<eLabel backgroundColor="green" position="130,201" size="100,3" zPosition="0" />
			<eLabel backgroundColor="yellow" position="240,201" size="100,3" zPosition="0" />
			<widget source="key_red" render="Label" position="20,168" zPosition="1" size="100,40" font="Regular;19" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_green" render="Label" position="130,168" zPosition="1" size="100,40" font="Regular;19" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="240,168" zPosition="1" size="100,40" font="Regular;19" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		</screen>"""

	def __init__(self, session):
		self.skin = Volume_Config.skin
		Screen.__init__(self, session)
		self.oldEnable = config.Volume.Enabled.value
		self.oldOffset = config.Volume.AC3_vol.value
		self.Clist = []
		self.Clist.append(getConfigListEntry(_('Enable AC3/Dolby'), config.Volume.Enabled))
		self.Clist.append(getConfigListEntry(_('AC3/Dolby offset'), config.Volume.AC3_vol))
		ConfigListScreen.__init__(self, self.Clist)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("+/-"))
		self["infotext"] = StaticText(_("this offset will only be used if the channel has not its own volume offset"))
		self["actions"] = ActionMap(["ColorActions","SetupActions"],
		{
			"ok": self.ok, 
			"cancel": self.cancel, 
			"green": self.greenPressed,
			"red": self.cancel,
			"yellow": self.yellowPressed,
		}, -2)
		self.onShown.append(self.setWindowTitle)

	def setWindowTitle(self):
		self.setTitle(_("Volume Config"))

	def greenPressed(self):
		config.Volume.save()
		self.close()

	def yellowPressed(self):
		#config.Volume.Enabled.value = False
		#config.Volume.AC3_vol.value = 10
		config.Volume.AC3_vol.setValue(config.Volume.AC3_vol.value * -1)
		self["config"].list = self.Clist
		self["config"].l.setList(self.Clist)

	def ok(self):
		self.greenPressed()

	def cancel(self):
		config.Volume.Enabled.setValue(self.oldEnable)
		config.Volume.AC3_vol.setValue(self.oldOffset)
		config.Volume.save()
		self.close()

class Volume:
	def __init__(self, session):
		# autostarting instance, comes active when info is updated (zap)
		self.session = session
		self.service = None
		self.onClose = [ ]
		self.read_services=[]
		self.read_volume=[]
		self.__event_tracker = ServiceEventTracker(screen=self,eventmap=
			{
				iPlayableService.evUpdatedInfo: self.__evUpdatedInfo,
			})
		self.volctrl = eDVBVolumecontrol.getInstance()
		self.volchange = None
		self.oldvol = 0
		self.oldservice = ""
		self.filen="/etc/volume.xml"
		self.startonce = True

	def loadXML(self):
		# load the list
		print "[Volume Adjust] load xml..."
		if not os_path.exists(self.filen):
			return
		self.read_services=[]
		self.read_volume=[]
		try:
			tree = ci_parse(self.filen).getroot()
			for channels in tree.findall("channels"):
				for service in  channels.findall("service"):
					read_service_name = service.get("name").encode("UTF-8")
					read_service_ref = service.get("ref").encode("UTF-8")
					read_service_volume = service.get("volume").encode("UTF-8")
					self.read_services.append (read_service_ref)
					self.read_volume.append (read_service_volume)
		except:
			print "[Volume Adjust] error parsing xml..."
		for i in self.read_services:
			print i


	def __evUpdatedInfo(self):
		# here it starts the actual routine to change the volume offset
		print "[Volume Adjust] Update Info"
		if not self.startonce:
			self.setvolume()
		vol = self.volctrl.getVolume()
		print "[Volume Adjust] Volume = " + str(vol)
		global ListChange
		# Check if list is updated (new save) or no list loaded
		if ListChange or len(self.read_services) == 0:
			self.loadXML()
			ListChange = None
		self.service = self.session.nav.getCurrentlyPlayingServiceReference()
		if not self.service is None:
			service = self.service.toCompareString()
			# check for new channel (zap)
			if service <> self.oldservice:
				print '[Volume Adjust] New Channel'
				# store new channel
				self.oldservice = service
				# calculate normal volume (subtract previous offset of the actual volume)
				vol3 = str(self.volctrl.getVolume())
				print '[Volume Adjust] oldvol = ' + str(self.oldvol)
				normalvol = int(vol3) - self.oldvol
				# don't forget to update the actual volume variable
				# don't change the volume if the offset = 0
				if self.oldvol != 0:
					# change the volume to previous volume
					self.oldvol = 0
					self.volctrl.setVolume(normalvol, normalvol)
				found = None
				tel = 0
				# search the new channel in list
				for i in self.read_services:
					if i == service:
						# service found
						print '[Volume Adjust] Found adjust volume channel'
						found = True
						break
					tel +=1
				# if channel found in list, search volume offset and change the volume
				if found:
					voloffset = self.read_volume[tel]
					print '[Volume Adjust] offset = ' + voloffset
					# calculate new volume
					vol1 = int(voloffset)
					vol2 = str(self.volctrl.getVolume())
					newvol = int(vol2) + vol1
					print '[Volume Adjust] newvol = ' + str(newvol)
					# set the new volume
					self.volctrl.setVolume(newvol, newvol)
					# store the new offset, need to change it back when new channel not in list
					self.oldvol = int(voloffset)
				else:
					if config.Volume.Enabled.value:
						print '[Volume Adjust] Check for AC3/Dolby'
						if self.isCurrentAudioAC3DTS():
							vol = self.volctrl.getVolume()
							newvol = int(vol) + config.Volume.AC3_vol.value
							print '[Volume Adjust] newvol AC3/Dolby = ' + str(newvol)
							self.volctrl.setVolume(newvol, newvol)
							self.oldvol = config.Volume.AC3_vol.value

	def setvolume(self):
		vol = 50
		vol = config.audio.volume.value
		print '[Setvolume] start with volume ' + str(vol)
		self.volctrl.setVolume(vol, vol)
		self.startonce = True

	def isCurrentAudioAC3DTS(self):
		service = self.session.nav.getCurrentService()
		audio = service.audioTracks()
		if audio:
			try: # uhh, servicemp3 leads sometimes to OverflowError Error
				tracknr = audio.getCurrentTrack()
				i = audio.getTrackInfo(tracknr)
				description = i.getDescription();
				print '[Volume Adjust] description: ' + description
				if "AC3" in description or "DTS" in description or "Dolby Digital" == description:
					print '[Volume Adjust] AudioAC3Dolby = YES'
					return True
			except:
				print '[Volume Adjust] Fault AudioAC3Dolby = NO'
				return False
		print '[Volume Adjust] AudioAC3Dolby = NO'
		return False


VolumeInstance = None


def sessionstart(reason, session):
	global VolumeInstance
	if VolumeInstance is None:
		VolumeInstance = Volume(session)

def main(session, **kwargs):
	session.open(Volume_adjust)

def menu(menuid, **kwargs):
	if menuid == "audio_menu":
		return [(_("Volume Adjust"), main, "Volume_Adjust", 5)]
	return [ ]

def Plugins(**kwargs):
	return [PluginDescriptor( where = PluginDescriptor.WHERE_SESSIONSTART, fnc = sessionstart ),
			PluginDescriptor( name = "Volume Adjust", description = _("select channels to add a offset to the Volume"), where = PluginDescriptor.WHERE_MENU, fnc = menu )]

