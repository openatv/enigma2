from Screen import Screen

from Components.Label import Label
from Components.Pixmap import Pixmap, MultiPixmap

class PVRState(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["state"] = Label(text="")
		self["speed"] = Label(text="")
		self["statusicon"] = MultiPixmap()

class TimeshiftState(PVRState):
	pass

class PTSTimeshiftState(Screen):
	skin = """
		<screen position="center,40" zPosition="2" size="420,70" backgroundColor="transpBlack" flags="wfNoBorder">
			<widget name="state" position="10,3" size="80,27" font="Regular;20" halign="center" backgroundColor="transpBlack" />
			<widget source="session.CurrentService" render="Label" position="95,5" size="200,27" font="Regular;20" halign="left" foregroundColor="white" backgroundColor="transpBlack">
				<convert type="ServicePosition">Position</convert>
			</widget>
			<widget source="session.CurrentService" render="Label" position="280,5" size="120,27" font="Regular;20" halign="right" foregroundColor="white" backgroundColor="transpBlack">
				<convert type="ServicePosition">Length</convert>
			</widget>
			<widget name="PTSSeekPointer" position="0,30" zPosition="3" size="19,20" pixmap="/usr/share/enigma2/skin_default/timeline-now.png" alphatest="on" />
			<ePixmap position="15,33" size="390,15" zPosition="1" pixmap="/usr/share/enigma2/skin_default/slider_back.png" alphatest="on"/>
			   <widget source="session.CurrentService" render="Progress" position="15,33" size="390,15" zPosition="2" pixmap="/usr/share/enigma2/skin_default/slider.png" transparent="1">
				<convert type="ServicePosition">Position</convert>
			</widget>
			<widget name="eventname" position="60,49" zPosition="4" size="320,20" font="Regular;18" halign="center" backgroundColor="transpBlack" />
			<widget name="statusicon" position="12,45" size="20,20" zPosition="5" alphatest="on" pixmaps="ViX_HD_Common/icons/play.png,ViX_HD_Common/icons/pause.png,ViX_HD_Common/icons/stop.png,ViX_HD_Common/icons/forward.png,ViX_HD_Common/icons/backward.png,ViX_HD_Common/icons/slow.png" />
			<widget name="speed" position="35,47" size="80,15" font="Regular; 17" halign="left" foregroundColor="infobar-frgrnd" backgroundColor="infobar_sunken" transparent="1" zPosition="5" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self["state"] = Label(text="")
		self["speed"] = Label(text="")
		self["statusicon"] = MultiPixmap()
		self["PTSSeekPointer"] = Pixmap()
		self["eventname"] = Label(text="")
