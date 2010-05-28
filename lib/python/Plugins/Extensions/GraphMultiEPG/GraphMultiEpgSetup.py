from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.Console import Console
from Components.ActionMap import ActionMap, NumberActionMap
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSelection, ConfigText, ConfigEnableDisable, KEY_LEFT, KEY_RIGHT, KEY_0, getConfigListEntry, ConfigNumber
from Components.ConfigList import ConfigList, ConfigListScreen

from Tools.Directories import *

class GraphMultiEpgSetup(Screen, ConfigListScreen):
	skin = """
        	<screen name="GraphMultiEPGSetup" position="center,center" size="560,435" title="Electronic Program Guide Setup">
                	<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
                	<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
                	<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
                	<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
                	<widget name="canceltext" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
                	<widget name="oktext" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
                	<widget name="config" position="10,50" size="550,395" />
		</screen>"""
		
	def __init__(self, session, args = None):
		Screen.__init__(self, session)
                self.setup_title = _("Graph MEpg Settings")
		
		self["oktext"] = Label(_("OK"))
		self["canceltext"] = Label(_("Cancel"))
		
		self["actions"] = ActionMap(["SetupActions"],
		{
			"ok": self.keySave,
			"save": self.keySave,
			"cancel": self.keyCancel,
		}, -1)
		
		self.onChangedEntry = [ ]
		self.session = session
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session)
		self.createSetup()

	def createSetup(self):
		print "Creating Graph Epg Setup"
		self.list = [ ]
		self.list.append(getConfigListEntry(_("Event Fontsize"), config.misc.graph_mepg.ev_fontsize))
		self.list.append(getConfigListEntry(_("Time Scale"), config.misc.graph_mepg.prev_time_period))
		self.list.append(getConfigListEntry(_("Items per Page "), config.misc.graph_mepg.items_per_page))
		self.list.append(getConfigListEntry(_("Skip Empty Services (may need restart)"), config.misc.graph_mepg.overjump))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

