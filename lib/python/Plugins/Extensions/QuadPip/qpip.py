from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigSelection, getConfigListEntry
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap, MovingPixmap
from Screens.MessageBox import MessageBox
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import fileExists
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

from Components.Sources.List import List
from Components.Label import Label
from Components.ActionMap import HelpableActionMap
from Components.MenuList import MenuList

from Screens.ChannelSelection import ChannelSelectionBase
from enigma import eServiceReference
from enigma import eListboxPythonMultiContent
from enigma import eTimer
from ServiceReference import ServiceReference
from Components.FileList import FileList
from Components.Button import Button
from Screens.ChoiceBox import ChoiceBox
from Screens.QuadPiP import QuadPiP

from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.HelpMenu import HelpableScreen

import pickle
import os

from Components.config import config, ConfigSubsection, ConfigNumber
from Components.Slider import Slider

from Components.SystemInfo import SystemInfo

config.plugins.quadpip = ConfigSubsection()
config.plugins.quadpip.lastchannel = ConfigNumber(default = 1)

ENABLE_QPIP_PROCPATH = "/proc/stb/video/decodermode"

def setDecoderMode(value):
	if os.access(ENABLE_QPIP_PROCPATH, os.F_OK):
		open(ENABLE_QPIP_PROCPATH,"w").write(value)
		return open(ENABLE_QPIP_PROCPATH,"r").read().strip() == value

class QuadPipChannelEntry:
	def __init__(self, name, idx, ch1, ch2, ch3, ch4):
		self.name = name
		self.idx = idx
		self.channel = {"1" : ch1, "2" : ch2, "3" : ch1, "4" : ch1,}

	def __str__(self):
		return "idx : %d, name : %s, ch0 : %s, ch1 : %s, ch2 : %s, ch3 : %s"\
					% (self.idx, self.name, self.channel.get("1"), self.channel.get("2"), self.channel.get("3"), self.channel.get("4"))

	def __cmp__(self, other):
		return self.idx - other.idx

	def getName(self):
		return self.name

	def getIndex(self):
		return self.idx

	def setChannel(self, idx, chName, sref):
		if self.channel.has_key(idx):
			self.channel[idx] = (chName, sref)
			return True

		return False

	def deleteChannel(self, idx):
		if self.channel.has_key(idx):
			self.channel[idx] = None
			return True

		return False

	def getChannel(self, idx):
		return self.channel.get(idx, None)

	def getChannelName(self, idx):
		chName = None
		ch = self.getChannel(idx)
		if ch:
			chName = ch[0]

		if chName is None:
			chName = _(" <No Channel>")

		return chName

	def getChannelSref(self, idx):
		chSref = None
		ch = self.getChannel(idx)
		if ch:
			chSref = ch[1]
		return chSref

	def setIndex(self, idx):
		self.idx = idx

	def setName(self, name):
		self.name = name

class QuadPipChannelData:
	def __init__(self):
		self.PipChannelList = []
		self.pipChannelDataPath = "/etc/enigma2/quadPipChannels.dat"
		self.dataLoad()

	def dataSave(self):
		fd = open(self.pipChannelDataPath, "w")
		pickle.dump(self.PipChannelList, fd)
		fd.close()
		#print "[*] dataSave"

	def dataLoad(self):
		if not os.access(self.pipChannelDataPath, os.R_OK):
			return

		fd = open(self.pipChannelDataPath, "r")
		self.PipChannelList = pickle.load(fd)
		fd.close()
		#print "[*] dataLoad"

	def getPipChannels(self):
		return self.PipChannelList

	def length(self):
		return len(self.PipChannelList)

class QuadPipChannelList(QuadPipChannelData):
	def __init__(self):
		QuadPipChannelData.__init__(self)
		self._curIdx = config.plugins.quadpip.lastchannel.value # starting from 1
		self.defaultEntryPreName = _("Quad PiP channel ")

	def saveAll(self):
		self.dataSave()
		config.plugins.quadpip.lastchannel.value = self._curIdx
		config.plugins.quadpip.lastchannel.save()

	def setIdx(self, value):
		if self._curIdx != value:
			self._curIdx = value
			config.plugins.quadpip.lastchannel.value = self._curIdx
			config.plugins.quadpip.lastchannel.save()

	def getIdx(self):
		return self._curIdx

	def getCurrentChannel(self):
		return self.getChannel(self._curIdx)

	def getChannel(self, idx):
		for ch in self.PipChannelList:
			if idx == ch.getIndex():
				return ch

		return None

	def addNewChannel(self, newChannel):
		self.PipChannelList.append(newChannel)

	def removeChannel(self, _channel):
		if self.getIdx() == _channel.getIndex():
			self.setIdx(0) # set invalid index

		self.PipChannelList.remove(_channel)

	def sortPipChannelList(self):
		self.PipChannelList.sort()
		newIdx = 1
		for ch in self.PipChannelList:
			ch.setIndex(newIdx)
			chName = ch.getName()
			if chName.startswith(self.defaultEntryPreName):
				ch.setName("%s%d" % (self.defaultEntryPreName, ch.getIndex()))
			newIdx += 1

	def getDefaultPreName(self):
		return self.defaultEntryPreName

quad_pip_channel_list_instance = QuadPipChannelList()

class CreateQuadPipChannelEntry(ChannelSelectionBase):
	skin_default_1080p = """
		<screen name="CreateQuadPipChannelEntry" position="center,center" size="1500,850" flags="wfNoBorder">
			<widget source="Title" render="Label" position="100,60" size="1300,60" zPosition="3" font="Semiboldit;52" halign="left" valign="center" backgroundColor="#25062748" transparent="1" />
			<ePixmap pixmap="skin_default/buttons/red.png" position="137,140" size="140,40" alphatest="blend" />
 			<ePixmap pixmap="skin_default/buttons/green.png" position="492,140" size="140,40" alphatest="blend" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="837,140" size="140,40" alphatest="blend" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="1192,140" size="140,40" alphatest="blend" />
			<widget name="key_red" position="137,140" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget name="key_green" position="492,140" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />
			<widget name="key_yellow" position="837,140" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" foregroundColor="#ffffff" transparent="1" />
			<widget name="key_blue" position="1192,140" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" foregroundColor="#ffffff" transparent="1" />
			<widget name="list" position="100,200" size="1250,365" serviceItemHeight="40" serviceNumberFont="Regular;28" serviceNameFont="Regular;28" serviceInfoFont="Semibold;24" foregroundColorServiceNotAvail="#58595b" transparent="1" scrollbarMode="showOnDemand" />
			<widget name="textChannels" position="100,580" size="1250,30" font="Regular;33" transparent="1" />
			<widget name="selectedList" position="110,620" size="700,160" font="Regular;28" itemHeight="40" transparent="1" />
			<widget name="description" position="860,630" size="650,160" font="Regular;28" halign="left" transparent="1" />
		</screen>
		"""
	skin_default_720p = """
		<screen name="CreateQuadPipChannelEntry" position="center,center" size="1000,610" flags="wfNoBorder">
			<widget source="Title" render="Label" position="40,40" size="910,40" zPosition="3" font="Semiboldit;32" backgroundColor="#25062748" transparent="1" />
			<ePixmap pixmap="skin_default/buttons/red.png" position="75,80" size="140,40" alphatest="blend" />
 			<ePixmap pixmap="skin_default/buttons/green.png" position="325,80" size="140,40" alphatest="blend" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="575,80" size="140,40" alphatest="blend" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="825,80" size="140,40" alphatest="blend" />
			<widget name="key_red" position="75,80" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget name="key_green" position="325,80" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />
			<widget name="key_yellow" position="575,80" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" foregroundColor="#ffffff" transparent="1" />
			<widget name="key_blue" position="825,80" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" foregroundColor="#ffffff" transparent="1" />
			<widget name="list" position="60,130" size="700,255" transparent="1" scrollbarMode="showOnDemand" foregroundColorServiceNotAvail="#58595b" />
			<widget name="textChannels" position="60,400" size="850,20" font="Regular;24" transparent="1" />
			<widget name="selectedList" position="70,430" size="480,150" font="Regular;22" itemHeight="25" transparent="1" />
			<widget name="description" position="590,460" size="350,150" font="Regular;22" halign="left" transparent="1" />
		</screen>
		"""
	skin_default_576p = """
		<screen name="CreateQuadPipChannelEntry" position="center,center" size="680,520" flags="wfNoBorder">
			<widget source="Title" render="Label" position="30,20" size="600,30" zPosition="3" font="Regular;22" backgroundColor="#25062748" transparent="1" />
			<ePixmap pixmap="skin_default/buttons/red.png" position="15,60" size="140,40" alphatest="blend" />
 			<ePixmap pixmap="skin_default/buttons/green.png" position="185,60" size="140,40" alphatest="blend" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="355,60" size="140,40" alphatest="blend" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="525,60" size="140,40" alphatest="blend" />
			<widget name="key_red" position="15,60" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget name="key_green" position="185,60" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />
			<widget name="key_yellow" position="355,60" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" foregroundColor="#ffffff" transparent="1" />
			<widget name="key_blue" position="525,60" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" foregroundColor="#ffffff" transparent="1" />
			<widget name="list" position="50,115" size="580,230" transparent="1" scrollbarMode="showOnDemand" foregroundColorServiceNotAvail="#58595b" />
			<widget name="textChannels" position="45,360" size="295,20" font="Regular;22" transparent="1" />
			<widget name="selectedList" position="50,385" size="290,100" font="Regular;20" itemHeight="22" transparent="1" />
			<widget name="description" position="360,390" size="310,140" font="Regular;20" halign="left" transparent="1" />
		</screen>
		"""
	def __init__(self, session, defaultEntryName, channel = None):
		ChannelSelectionBase.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "QuadPipChannelEditActions"],
		{
			"cancel": self.Exit,
			"ok": self.channelSelected,
			"toggleList" : self.toggleCurrList,
			"editName" : self.editEntryName,
			"up": self.goUp,
			"down": self.goDown,
		}, -1)

		self.session = session
		dh = self.session.desktop.size().height()
		self.skin = {1080:CreateQuadPipChannelEntry.skin_default_1080p, \
						720:CreateQuadPipChannelEntry.skin_default_720p, \
						576:CreateQuadPipChannelEntry.skin_default_576p}.get(dh, CreateQuadPipChannelEntry.skin_default_1080p)

		self.defaultEntryName = defaultEntryName
		self["textChannels"] = Label(" ")
		self["description"] = Label(" ")

		self.currList = None

		self.newChannel = channel
		self.descChannels = []
		self.prepareChannels()
		self["selectedList"] = MenuList(self.descChannels, True)
		self.selectedList = self["selectedList"]

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTvMode()
		self.showFavourites()
		self.switchToServices()
		self.updateEntryName()

	def updateEntryName(self):
		self["textChannels"].setText("%s :" % self.newChannel.getName())

	def editEntryName(self):
		self.session.openWithCallback(self.editEntryNameCB, VirtualKeyBoard, title = (_("Input channel name.")), text = self.newChannel.getName())

	def editEntryNameCB(self, newName):
		if newName:
			self.newChannel.setName(newName)
			self.updateEntryName()

	def updateDescription(self):
		if self.currList == "channelList":
			desc = _("EPG key : Switch to quad PiP entry\nOk key : Add to new entry\nPVR key : Input channel name\nExit key : Finish channel edit")
		else:
			desc = _("EPG key : Switch to channel list\nOk key : Remove selected channel\nPVR key : Input channel name\nExit key : Finish channel edit")

		self["description"].setText(desc)

	def prepareChannels(self):
		if self.newChannel is None:
			self.newChannel = QuadPipChannelEntry(self.defaultEntryName, 99999, None, None, None, None)

		self.updateDescChannels()

	def updateDescChannels(self):
		self.descChannels = []
		for idx in range(1,5):
			sIdx = str(idx)
			_isEmpty = False
			chName = self.newChannel.getChannelName(sIdx)
			if chName is None:
				chName = _(" <empty>")
				_isEmpty = True
			self.descChannels.append(("%d)  %s" % (idx, chName), sIdx, _isEmpty))	

	def updateDescChannelList(self):
		self["selectedList"].setList(self.descChannels)

	def goUp(self):
		if self.currList == "channelList":
			self.servicelist.moveUp()
		else:
			self.selectedList.up()

	def goDown(self):
		if self.currList == "channelList":
			self.servicelist.moveDown()
		else:
			self.selectedList.down()

	def toggleCurrList(self):
		if self.currList == "channelList":
			self.switchToSelected()
		else:
			self.switchToServices()

	def switchToServices(self):
		self.servicelist.selectionEnabled(1)
		self.selectedList.selectionEnabled(0)
		self.currList = "channelList"
		self.updateDescription()

	def switchToSelected(self):
		self.servicelist.selectionEnabled(0)
		self.selectedList.selectionEnabled(1)
		self.currList = "selectedList"
		self.updateDescription()

	def channelSelected(self): # just return selected service
		if self.currList == "channelList":
			ref = self.getCurrentSelection()
			if (ref.flags & 7) == 7:
				self.enterPath(ref)
			elif not (ref.flags & eServiceReference.isMarker):
				ref = self.getCurrentSelection()
				serviceName = ServiceReference(ref).getServiceName()
				sref = ref.toString()
				#self.addChannel(serviceName, sref)
				_title = _('Choice where to put "%s"') % serviceName
				_list = []
				for idx in range(1,5):
					sIdx = str(idx)
					_isEmpty = False
					chName = self.newChannel.getChannelName(sIdx)
					_list.append((chName, sIdx, serviceName, sref, _isEmpty))

				self.session.openWithCallback(self.choiceIdxCallback, ChoiceBox, title=_title, list=tuple(_list))
		else:
			self.removeChannel()

	def choiceIdxCallback(self, answer):
		if answer is not None:
			(desc, sIdx, serviceName, sref, _isEmpty) = answer
			self.addChannel(sIdx, serviceName, sref)

	def addChannel(self, sIdx, serviceName, sref):
		if self.newChannel.setChannel(sIdx, serviceName, sref):
			self.updateDescChannels()
			self.updateDescChannelList()

	def removeChannel(self):
		cur = self.selectedList.getCurrent()
		if cur:
			sIdx = cur[1]
			if self.newChannel.deleteChannel(sIdx):
				self.updateDescChannels()
				self.updateDescChannelList()

	def getNewChannel(self):
		for idx in range(1,5):
			sIdx = str(idx)
			ch = self.newChannel.getChannel(sIdx)
			if ch is not None:
				return self.newChannel

		return None

	def Exit(self):
		self.close(self.getNewChannel())

class QuadPiPChannelSelection(Screen, HelpableScreen):
	skin = """
		<screen position="%s,%s" size="%d,%d">
			<ePixmap pixmap="skin_default/buttons/red.png" position="%d,%d" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="%d,%d" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="%d,%d" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="%d,%d" size="140,40" alphatest="on" />
			<widget name="key_red" position="%d,%d" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#9f1313" transparent="1" />
			<widget name="key_green" position="%d,%d" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#1f771f" transparent="1" />
			<widget name="key_yellow" position="%d,%d" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#a08500" transparent="1" />
			<widget name="key_blue" position="%d,%d" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#18188b" transparent="1" />
			<widget source="ChannelList" render="Listbox" position="%d,%d" size="%d,%d" scrollbarMode="showOnDemand">
				<convert type="TemplatedMultiContent">
				{"template":
					[
						MultiContentEntryText(pos = (%d, %d), size = (%d, %d), font=0, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 0),
						MultiContentEntryText(pos = (%d, %d), size = (%d, %d), font=1, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 1),
						MultiContentEntryText(pos = (%d, %d), size = (%d, %d), font=1, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 2),
						MultiContentEntryText(pos = (%d, %d), size = (%d, %d), font=1, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 3),
						MultiContentEntryText(pos = (%d, %d), size = (%d, %d), font=1, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 4),
					],
					"fonts": [gFont("Regular", %d), gFont("Regular", %d)],
					"itemHeight": %d
				}
				</convert>
			</widget>
		</screen>
		"""
	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.setTitle(_("Quad PiP Channel Selection"))

		dw = self.session.desktop.size().width()
		dh = self.session.desktop.size().height()
		pw, ph = {1080:("center", "center"), 720:("center", "center"), 576:("center", "20%")}.get(dh, ("center", "center"))
		(sw, sh) = {1080:(dw/3, dh/2), 720:(int(dw/2), int(dh/1.5)), 576:(int(dw/1.3), int(dh/1.5))}.get(dh, (28, 24))
		button_margin = 5
		button_h = 40
		list_y = 40+button_margin*3
		self.fontSize = {1080:(28, 24), 720:(24,20), 576:(20,18)}.get(dh, (28, 24))
		self.skin = QuadPiPChannelSelection.skin % (pw, ph, \
														sw, sh+list_y, \
														sw/8-70, button_margin, \
														sw/8-70+sw/4, button_margin, \
														sw/8-70+sw/4*2, button_margin, \
														sw/8-70+sw/4*3, button_margin, \
														sw/8-70, button_margin, \
														sw/8-70+sw/4, button_margin, \
														sw/8-70+sw/4*2, button_margin, \
														sw/8-70+sw/4*3, button_margin, \
														0, list_y, sw, sh, \
														sw/16, 1, sw-sw/16*2, sh/13, \
														sw/11, 1+sh/13, 			sw-sw/16*2-sw/8, sh/18, \
														sw/11, 1+sh/13+sh/18, 	sw-sw/16*2-sw/8, sh/18, \
														sw/11, 1+sh/13+sh/18*2, 	sw-sw/16*2-sw/8, sh/18, \
														sw/11, 1+sh/13+sh/18*3, 	sw-sw/16*2-sw/8, sh/18, \
														self.fontSize[0], self.fontSize[1], \
														sh/3)
		self["key_red"] = Label(_("Select"))
		self["key_green"] = Label(_("Add"))
		self["key_yellow"] = Label(_("Remove"))
		self["key_blue"] = Label(_("Edit"))

		self.PipChannelListApply = []
		self["ChannelList"] = List(self.PipChannelListApply)

		self["qpipActions"] = HelpableActionMap(self, "QuadPipSetupActions",
		{
			"red": (self.keyRed, _("Select Quad Channels")),
			"green": (self.keyGreen, _("Add New Quad Channel Entry")),
			"yellow": (self.keyYellow, _("Remove Quad Channel Entry")),
			"blue": (self.keyBlue, _("Edit Quad Channel Entry")),
		}, -2)

		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
		{
			"ok": (self.keyOk, _("Select Quad Channels")),
			"cancel": (self.keyCancel, _("Exit Quad Channel Selection")),
		}, -2)

		self.oldPosition = None

		global quad_pip_channel_list_instance
		self.qpipChannelList = quad_pip_channel_list_instance

		self.oldPosition = self.qpipChannelList.getIdx()-1

		self.onLayoutFinish.append(self.layoutFinishedCB)

	def layoutFinishedCB(self):
		self.updateDisplay()
		self.updatePosition()

	def keyOk(self):
		idx = self.getCurrentIndex()
		if idx != -1:
			self.qpipChannelList.setIdx(idx)

		self.close()

	def keyCancel(self):
		self.close()

	def keyRed(self):
		self.keyOk()

	def keyGreen(self):
		self.session.openWithCallback(self.CreateQuadPipChannelEntryCB, CreateQuadPipChannelEntry, self.getDefaultEntryName(), None)

	def keyYellow(self):
		curChannel = self.getSelectedChannel()
		if curChannel:
			self.session.openWithCallback(self.removeCallback, MessageBox, _("Really delete this entry?"))

	def removeCallback(self, answer):
		curChannel = self.getSelectedChannel()
		if answer and curChannel:
			self.oldPosition = self["ChannelList"].getIndex()
			self.qpipChannelList.removeChannel(curChannel)
			self.force_exit = True
			self.updateChannelList()

	def keyBlue(self):
		curChannel = self.getSelectedChannel()
		if curChannel:
			self.oldPosition = self["ChannelList"].getIndex()
			self.qpipChannelList.removeChannel(curChannel)
			self.session.openWithCallback(self.CreateQuadPipChannelEntryCB, CreateQuadPipChannelEntry, None, curChannel)

	def getCurrentIndex(self):
		idx = -1
		cur = self["ChannelList"].getCurrent()
		if cur:
			idx = cur[5]

		return idx

	def getSelectedChannel(self):
		selectedChannel = None
		idx = self.getCurrentIndex()
		if idx != -1:
			selectedChannel = self.qpipChannelList.getChannel(idx)

		return selectedChannel

	def getDefaultEntryName(self):
		return "%s%d" % (self.qpipChannelList.getDefaultPreName(), self.qpipChannelList.length() + 1)

	def CreateQuadPipChannelEntryCB(self, newChannel):
		if newChannel:
			self.qpipChannelList.addNewChannel(newChannel)
			self.qpipChannelList.sortPipChannelList()
			self.oldPosition = newChannel.getIndex()-1
			self.updateDisplay()
			self.updatePosition()

	def updateDisplay(self):
		self.PipChannelListApply = []
		for ch in self.getChannelList():
			entry = []

			entryName = ch.getName()
			if not entryName:
				entryName = "%s%d" % (self.qpipChannelList.getDefaultPreName(), ch.getIndex())

			if self.qpipChannelList.getIdx() == ch.getIndex():
				entryName += _(" (current channel)")

			entry.append(entryName)
			entry.append("1) " + ch.getChannelName("1"))
			entry.append("2) " + ch.getChannelName("2"))
			entry.append("3) " + ch.getChannelName("3"))
			entry.append("4) " + ch.getChannelName("4"))
			entry.append(ch.getIndex())
			self.PipChannelListApply.append(tuple(entry))

		self["ChannelList"].setList(self.PipChannelListApply)

	def updatePosition(self):
		if self.oldPosition:
			if self["ChannelList"].count() > self.oldPosition:
				self["ChannelList"].setIndex(self.oldPosition)
			self.oldPosition = None

	def updateChannelList(self):
		self.qpipChannelList.sortPipChannelList()
		self.updateDisplay()
		self.updatePosition()

	def getChannelList(self):
		return self.qpipChannelList.getPipChannels()

class FocusShowHide:
	STATE_HIDDEN = 0
	STATE_SHOWN = 1

	def __init__(self):
		self.__state = self.STATE_SHOWN
		self.hideTimer = eTimer()
		self.hideTimer.callback.append(self.hideTimerCB)
		self.onLayoutFinish.append(self.startHideTimer)

	def startHideTimer(self):
		self.hideTimer.stop()
		self.hideTimer.start(5000, True)

	def hideTimerCB(self):
		self.hideFocus()

	def isShown(self):
		return self.__state == self.STATE_SHOWN

	def showFocus(self):
		self.show()
		self.__state = self.STATE_SHOWN
		self.startHideTimer()

	def hideFocus(self):
		self.hideTimer.stop()
		self.hide()
		self.__state = self.STATE_HIDDEN

	def toggleShow(self):
		if self.__state == self.STATE_SHOWN:
			self.hideFocus()
		elif self.__state == self.STATE_HIDDEN:
			self.showFocus()

class QuadPipScreen(Screen, FocusShowHide, HelpableScreen):
	skin = """
		<screen position="0,0" size="%d,%d" backgroundColor="transparent" flags="wfNoBorder">
			<widget name="ch1" position="240,240" zPosition="1" size="480,60" font="Regular; %d" halign="center" valign="center" foregroundColor="white" backgroundColor="#ffffffff" alphatest="on" borderWidth="2"/>
			<widget name="ch2" position="1200,240" zPosition="1" size="480,60" font="Regular; %d" halign="center" valign="center" foregroundColor="white" backgroundColor="#ffffffff" alphatest="on" borderWidth="2"/>
			<widget name="ch3" position="240,780" zPosition="1" size="480,60" font="Regular; %d" halign="center" valign="center" foregroundColor="white" backgroundColor="#ffffffff" alphatest="on" borderWidth="2"/>
			<widget name="ch4" position="1200,780" zPosition="1" size="480,60" font="Regular; %d" halign="center" valign="center" foregroundColor="white" backgroundColor="#ffffffff" alphatest="on" borderWidth="2"/>
			<widget name="text1" position="%d,%d" zPosition="2" size="%d,%d" font="Regular; %d" halign="left" valign="center" alphatest="on" borderWidth="2"/>
			<widget name="text2" position="%d,%d" zPosition="2" size="%d,%d" font="Regular; %d" halign="left" valign="center" alphatest="on" borderWidth="2"/>
			<widget name="focus" position="0,0" zPosition="-1" size="960,540" backgroundColor="#ffffffff" borderWidth="5" borderColor="#e61616" alphatest="on" />
		</screen>
		"""
	def __init__(self, session):
		self.session = session
		self.session.qPips = None
		Screen.__init__(self, session)
		FocusShowHide.__init__(self)
		HelpableScreen.__init__(self)
		self.setTitle(_("Quad PiP Screen"))

		self["actions"] = HelpableActionMap(self, "QuadPipSetupActions",
		{
			"cancel": (self.keyExit, _("Exit quad PiP")),
			"ok": (self.keyOk, _("Zap focused channel on full screen")),
			"left": (self.keyLeft, _("Select channel audio")),
			"right": (self.keyRight, _("Select channel audio")),
			"up": (self.keyUp, _("Select channel audio")),
			"down": (self.keyDown, _("Select channel audio")),
			"channelup" : (self.KeyChannel, _("Show channel selection")),
			"channeldown" : (self.KeyChannel, _("Show channel selection")),
			"menu" : (self.KeyChannel, _("Show channel selection")),
			"channelPrev" : (self.KeyPrev, _("Prev quad PiP channel")),
			"channelNext" : (self.KeyNext, _("Next quad PiP channel")),
			"red" : (self.KeyRed, _("Show/Hide focus bar")),
		}, -1)

		self["ch1"] = Label(_(" "))
		self["ch2"] = Label(_(" "))
		self["ch3"] = Label(_(" "))
		self["ch4"] = Label(_(" "))
		self["text1"] = Label(_("  Red key : Show/Hide channel name"))
		self["text2"] = Label(_("  Menu key : Select quad channel"))
		self["focus"] = Slider(-1, -1)

		self.currentPosition = 1 # 1~4
		self.updatePositionList()

		self.skin = QuadPipScreen.skin % (self.session.desktop.size().width(), self.session.desktop.size().height(), \
												self.fontSize, self.fontSize, self.fontSize, self.fontSize, \
												self.text1Pos[0], self.text1Pos[1], self.text1Pos[2], self.text1Pos[3], self.fontSize, \
												self.text2Pos[0], self.text2Pos[1], self.text2Pos[2], self.text2Pos[3], self.fontSize)
		self.oldService = None
		self.curChannel = None
		self.curPlayAudio = -1

		global quad_pip_channel_list_instance
		self.qpipChannelList = quad_pip_channel_list_instance

		self.oldFccEnable = False
		self.oldMinitvEanble = False

		self.onLayoutFinish.append(self.layoutFinishedCB)

		self.notSupportTimer = eTimer()
		self.notSupportTimer.callback.append(self.showNotSupport)

		self.noChannelTimer = eTimer()
		self.noChannelTimer.callback.append(self.noChannelTimerCB)

		self.forceToExitTimer = eTimer()
		self.forceToExitTimer.callback.append(self.forceToExitTimerCB)

	def forceToExitTimerCB(self):
		self.session.openWithCallback(self.close, MessageBox, _("Quad PiP is not available."), MessageBox.TYPE_ERROR)

	def showNotSupport(self):
		self.session.openWithCallback(self.close, MessageBox, _("Box or driver is not support Quad PiP."), MessageBox.TYPE_ERROR)

	def noChannelTimerCB(self):
		self.session.openWithCallback(self.ChannelSelectCB, QuadPiPChannelSelection)

	def layoutFinishedCB(self):
		if not os.access(ENABLE_QPIP_PROCPATH, os.F_OK):
			self.notSupportTimer.start(100, True)
			return

		self.onClose.append(self.__onClose)

		if self.session.pipshown: # try to disable pip
			self.session.pipshown = False
			del self.session.pip

		self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.stopService()

		if SystemInfo.get("FastChannelChange", False):
			self.disableFCC()

		if SystemInfo.get("MiniTV", False):
			self.disableMiniTV()

		ret = setDecoderMode("mosaic")
		if ret is not True:
			self.forceToExitTimer.start(0, True)
			return

		self.moveLabel()

		if self.qpipChannelList.length() == 0:
			self.noChannelTimer.start(10, True)
		else:
			self.playLastChannel()

	def __onClose(self):
		self.disableQuadPip()
		setDecoderMode("normal")

		if SystemInfo.get("FastChannelChange", False):
			self.enableFCC()

		if SystemInfo.get("MiniTV", False):
			self.enableMiniTV()

		self.qpipChannelList.saveAll()
		self.session.nav.playService(self.oldService)

	def getChannelPosMap(self, w, h):
		rectMap = {}
		ch1 = (0, 0, int(w*0.5), int(h*0.5))
		ch2 = (int(w*0.5), 0, int(w*0.5), int(h*0.5))
		ch3 = (0, int(h*0.5), int(w*0.5), int(h*0.5))
		ch4 = (int(w*0.5), int(h*0.5), int(w*0.5), int(h*0.5))
		rectMap = (None, ch1, ch2, ch3, ch4)

		return rectMap

	def updatePositionList(self):
		w = self.session.desktop.size().width()
		h = self.session.desktop.size().height()
		self.framePosMap = self.getChannelPosMap(w, h)
		self.eVideoPosMap = self.getChannelPosMap(720, 576)

		self.movePositionMap = {}
		self.movePositionMap["left"] = [-1, 2, 1, 4, 3]
		self.movePositionMap["right"] = [-1, 2, 1, 4, 3]
		self.movePositionMap["up"] = [-1, 3, 4, 1, 2]
		self.movePositionMap["down"] = [-1, 3, 4, 1, 2]

		self.labelPositionMap = {}
		self.labelPositionMap["ch1"] = (w/8,		h/4-h/36,		w/4,	h/18)
		self.labelPositionMap["ch2"] = (w/8+w/2,	h/4-h/36,		w/4,	h/18)
		self.labelPositionMap["ch3"] = (w/8,		h/4-h/36+h/2,	w/4,	h/18)
		self.labelPositionMap["ch4"] = (w/8+w/2,	h/4-h/36+h/2,	w/4,	h/18)

		self.decoderIdxMap = [None, 0, 1, 2, 3]

		self.fontSize = {1080:40, 720:28, 576:18}.get(h, 40)
		self.text1Pos = (w-w/3, h-h/18-h/18, w/3, h/18)
		self.text2Pos = (w-w/3, h-h/18, w/3, h/18)

	def moveFrame(self):
		self.showFocus()
		pos = self.framePosMap[self.currentPosition]
		self["focus"].resize(int(pos[2]), int(pos[3]))
		self["focus"].move(int(pos[0]), int(pos[1]))

	def moveLabel(self):
		posMap = self.labelPositionMap

		ch1_posMap = posMap["ch1"]
		self["ch1"].move(int(ch1_posMap[0]), int(ch1_posMap[1]))
		self["ch1"].resize(int(ch1_posMap[2]), int(ch1_posMap[3]))

		ch2_posMap = posMap["ch2"]
		self["ch2"].move(int(ch2_posMap[0]), int(ch2_posMap[1]))
		self["ch2"].resize(int(ch2_posMap[2]), int(ch2_posMap[3]))

		ch3_posMap = posMap["ch3"]
		self["ch3"].move(int(ch3_posMap[0]), int(ch3_posMap[1]))
		self["ch3"].resize(int(ch3_posMap[2]), int(ch3_posMap[3]))

		ch4_posMap = posMap["ch4"]
		self["ch4"].move(int(ch4_posMap[0]), int(ch4_posMap[1]))
		self["ch4"].resize(int(ch4_posMap[2]), int(ch4_posMap[3]))

	def keyExit(self):
		self.close()

	def keyOk(self):
		if self.isShown():
			channel = self.qpipChannelList.getCurrentChannel()
			if channel:
				chInfo = channel.getChannel(str(self.currentPosition))
				if chInfo:
					(sname, sref) = chInfo
					self.oldService = eServiceReference(sref)
					self.close()
		else:
			self.showFocus()

	def keyLeft(self):
		newPosition = self.movePositionMap["left"][self.currentPosition]
		self.selectPosition(newPosition)

	def keyRight(self):
		newPosition = self.movePositionMap["right"][self.currentPosition]
		self.selectPosition(newPosition)

	def keyUp(self):
		newPosition = self.movePositionMap["up"][self.currentPosition]
		self.selectPosition(newPosition)

	def keyDown(self):
		newPosition = self.movePositionMap["down"][self.currentPosition]
		self.selectPosition(newPosition)

	def KeyChannel(self):
		self.session.openWithCallback(self.ChannelSelectCB, QuadPiPChannelSelection)

	def KeyPrev(self):
		curIdx = self.qpipChannelList.getIdx()
		curIdx -= 1
		if curIdx == 0:
			curIdx = self.qpipChannelList.length()
		self.qpipChannelList.setIdx(curIdx)
		self.playLastChannel()

	def KeyNext(self):
		curIdx = self.qpipChannelList.getIdx()
		curIdx += 1
		if curIdx > self.qpipChannelList.length():
			curIdx = 1
		self.qpipChannelList.setIdx(curIdx)
		self.playLastChannel()

	def KeyRed(self):
		self.toggleShow()

	def selectPosition(self, pos):
		self.currentPosition = pos
		self.moveFrame()
		self.selectAudio()

	def selectAudio(self):
		if self.curPlayAudio == -1:
			return

		if self.curPlayAudio != self.currentPosition:
			if self.session.qPips and len(self.session.qPips) >= self.currentPosition:
				self.playAudio(self.curPlayAudio, False)
				self.playAudio(self.currentPosition, True)

	def disableQuadPip(self):
		if self.session.qPips is not None:
			for qPip in self.session.qPips:
				del qPip

			self.session.qPips = None
			self.curPlayAudio = -1

		self.updateChannelName(None)

	def ChannelSelectCB(self):
		if self.qpipChannelList.length() == 0:
			self.disableQuadPip()
		else:
			self.playLastChannel()

	def playLastChannel(self, first=True):
		if self.qpipChannelList.length() == 0:
			return

		channel = self.qpipChannelList.getCurrentChannel()
		if channel:
			self.playChannel(channel)
		elif first:
			self.qpipChannelList.setIdx(1)
			self.playLastChannel(False)

		return channel

	def playChannel(self, channel):
		print "[playChannel] channel : ", channel

		if self.curChannel and self.curChannel == channel.channel:
			return

		self.disableQuadPip()
		self.selectPosition(1)

		self.curChannel = channel.channel.copy()

		self.session.qPips = []
		for idx in range(1,5):
			chInfo = channel.getChannel(str(idx))
			if chInfo is None:
				continue

			(sname, sref) = chInfo

			qPipShown = False

			decoderIdx = self.decoderIdxMap[idx]
			pos = self.eVideoPosMap[idx]
			#print "===================================================================="
			#print "sname : ", sname
			#print "sref : ", sref
			#print "decoderIdx : " , decoderIdx
			#print "pos : ", pos
			#print "===================================================================="

			qPipInstance =  self.session.instantiateDialog(QuadPiP, decoderIdx, pos)
			qPipInstance.setAnimationMode(0)
			qPipInstance.show()

			isPlayAudio = False
			if self.currentPosition == idx:
				isPlayAudio = True
				self.curPlayAudio = idx

			if qPipInstance.playService(eServiceReference(sref), isPlayAudio):
				self.session.qPips.append(qPipInstance)
			else:
				print "play failed, ", sref
				del qPipInstance

		self.updateChannelName(channel)
		self.showFocus()

	def playAudio(self, idx, value):
		qPipInstance = self.session.qPips[idx-1]
		qPipInstance.setQpipMode(True, value)

		if value:
			self.curPlayAudio = idx
		else:
			self.curPlayAudio = -1

	def updateChannelName(self, channel):
		for idx in range(1,5):
			self["ch%d" % idx].setText((channel and channel.getChannelName(str(idx))) or _("No channel"))

	def disableFCC(self):
		try:
			self.oldFccEnable = config.plugins.fccsetup.activate.value
			if self.oldFccEnable:
				config.plugins.fccsetup.activate.value = False
				from Plugins.SystemPlugins.FastChannelChange.plugin import FCCChanged
				FCCChanged()
		except:
			self.oldFccEnable = False

	def enableFCC(self):
		if self.oldFccEnable:
			try:
				config.plugins.fccsetup.activate.value = self.oldFccEnable
				from Plugins.SystemPlugins.FastChannelChange.plugin import FCCChanged
				FCCChanged()
			except:
				pass

	def disableMiniTV(self):
		try:
			self.oldMinitvEanble = config.plugins.minitv.enable.value
			if self.oldMinitvEanble:
				config.plugins.minitv.enable.value = False
		except:
			self.oldFccEnable = False

	def enableMiniTV(self):
		if self.oldMinitvEanble:
			try:
				config.plugins.minitv.enable.value = self.oldMinitvEanble
			except:
				pass

