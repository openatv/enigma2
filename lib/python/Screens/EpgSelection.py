from Screen import Screen
from Components.AVSwitch import AVSwitch
from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap
from Components.Button import Button
from Components.config import config, ConfigClock, NoSave, ConfigSelection, getConfigListEntry, ConfigText, ConfigDateTime, ConfigSubList, ConfigYesNo
from Components.ConfigList import ConfigListScreen
from Components.EpgList import EPGList, EPG_TYPE_SINGLE, EPG_TYPE_SIMILAR, EPG_TYPE_MULTI, EPG_TYPE_ENHANCED, EPG_TYPE_INFOBAR, EPG_TYPE_GRAPH
from Components.Label import Label
from Components.GUIComponent import GUIComponent
from Components.HTMLComponent import HTMLComponent
from Components.Pixmap import Pixmap
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.Event import Event
from Components.SystemInfo import SystemInfo
from Components.TimerSanityCheck import TimerSanityCheck
from Components.UsageConfig import preferredTimerPath, defaultMoviePath
from Screens.MovieSelection import getPreferredTagEditor
from Screens.TimerEdit import TimerSanityConflict
from Screens.EventView import EventViewSimple
from Screens.MessageBox import MessageBox
from Tools.Directories import pathExists, resolveFilename, SCOPE_CURRENT_SKIN, SCOPE_LANGUAGE, SCOPE_PLUGINS
from Tools.LoadPixmap import LoadPixmap
from TimeDateInput import TimeDateInput
from enigma import eServiceReference, getDesktop, eEPGCache, eTimer, eServiceCenter, eListbox, eListboxPythonMultiContent, eRect, ePicLoad, gFont, RT_HALIGN_LEFT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_WRAP
from RecordTimer import RecordTimerEntry, parseEvent, AFTEREVENT
from TimerEntry import TimerEntry
from ServiceReference import ServiceReference
from time import time, strftime, localtime, mktime
from datetime import datetime

mepg_config_initialized = False

config.misc.EPGSort = ConfigSelection(default="Time", choices = [
				("Time", _("Time")),
				("AZ", _("Alphanumeric"))
				])

class EPGSelection(Screen):
	data = resolveFilename(SCOPE_CURRENT_SKIN,"skin.xml")
	data = data.replace('/ skin.xml','/skin.xml')
	data = file(resolveFilename(SCOPE_CURRENT_SKIN,"skin.xml")).read()
	if data.find('xres="1280"') >= 0:
		QuickEPG = """
			<screen name="QuickEPG" position="0,505" size="1280,215" title="QuickEPG" backgroundColor="transparent" flags="wfNoBorder">
				<ePixmap alphatest="off" pixmap="DMConcinnity-HD/infobar-hd.png" position="0,0" size="1280,220" zPosition="0"/>
				<widget source="Service" render="Picon" position="60,75" size="100,60" transparent="1" zPosition="2" alphatest="blend">
					<convert type="ServiceName">Reference</convert>
				</widget>
				<widget source="Service" render="Label" position="0,42" size="1280,36" font="Regular;26" valign="top" halign="center" noWrap="1" backgroundColor="#101214" foregroundColor="#cccccc" transparent="1" zPosition="2" >
					<convert type="ServiceName">Name</convert>
				</widget>
				<widget name="list" position="340,80" size="640,54" backgroundColor="#101214" foregroundColor="#cccccc" transparent="1" itemHeight="27" zPosition="2"/>
				<ePixmap pixmap="DMConcinnity-HD/buttons/red.png" position="260,160" size="25,25" alphatest="blend" />
				<widget name="key_red" position="300,164" zPosition="1" size="130,20" font="Regular; 20" backgroundColor="#101214" foregroundColor="#cccccc" transparent="1" />
				<ePixmap pixmap="DMConcinnity-HD/buttons/green.png" position="450,160" size="25,25" alphatest="blend" />
				<widget name="key_green" position="490,164" zPosition="1" size="130,20" font="Regular; 20" backgroundColor="#101214" foregroundColor="#cccccc" transparent="1" />
				<ePixmap pixmap="DMConcinnity-HD/buttons/yellow.png" position="640,160" size="25,25" alphatest="blend" />
				<widget name="key_yellow" position="680,164" zPosition="1" size="130,20" font="Regular; 20" backgroundColor="#101214" foregroundColor="#cccccc" transparent="1" />
				<ePixmap pixmap="DMConcinnity-HD/buttons/blue.png" position="830,160" size="25,25" alphatest="blend" />
				<widget name="key_blue" position="870,164" zPosition="1" size="150,20" font="Regular; 20" backgroundColor="#101214" foregroundColor="#cccccc" transparent="1" />
			</screen>"""
		GraphEPG = """
			<screen name="GraphicalEPG" position="center,center" size="1280,720" backgroundColor="#000000" title="Programme Guide">
				<eLabel text="Programme Guide" position="460,20" size="480,30" font="Regular;26" foregroundColor="#FFFFFF" backgroundColor="#000000" shadowColor="#000000" halign="center" transparent="1" />
				<widget name="date" position="40,20" size="180,30" font="Regular;26" halign="left"  foregroundColor="#00e5b243" backgroundColor="#000000" transparent="1" />

				<widget source="global.CurrentTime" render="Label" position="283, 20" size="90,30" font="Regular;26" foregroundColor="#FFFFFF" backgroundColor="#000000" shadowColor="#000000" halign="right" transparent="1">
					<convert type="ClockToText">Default</convert>
				</widget>
				<widget source="global.CurrentTime" render="Label" position="1070, 20" size="160,30" font="Regular;26" foregroundColor="#FFFFFF" backgroundColor="#000000" shadowColor="#000000" halign="right" transparent="1">
					<convert type="ClockToText">Format:%d.%m.%Y</convert>
				</widget>
				<widget name="lab1" position="0,90" size="1280,480" font="Regular;24" halign="center" valign="center" backgroundColor="#000000" transparent="0" zPosition="2" />
				<widget name="timeline_text" position="9, 60" size="1230,30" foregroundColor="#00e5b243" backgroundColor="#000000" transparent="1"/>
				<widget name="list" position="40,90" size="1200, 480" scrollbarMode="showNever" transparent="1" />
				<widget name="timeline0" position="0,90" zPosition="2" size="2,480" pixmap="skin_default/timeline.png" />
				<widget name="timeline1" position="0,90" zPosition="2" size="2,480" pixmap="skin_default/timeline.png" />
				<widget name="timeline2" position="0,90" zPosition="2" size="2,480" pixmap="skin_default/timeline.png" />
				<widget name="timeline3" position="0,90" zPosition="2" size="2,480" pixmap="skin_default/timeline.png" />
				<widget name="timeline4" position="0,90" zPosition="2" size="2,480" pixmap="skin_default/timeline.png" />
				<widget name="timeline5" position="0,90" zPosition="2" size="2,480" pixmap="skin_default/timeline.png" />

				<widget name="timeline_now" position="0, 90" zPosition="2" size="19, 480" pixmap="/usr/share/enigma2/skin_default/GraphEPG/timeline-now.png" alphatest="on" />
				<widget source="Event" render="Label" position="5, 575" size="100, 30" font="Regular;26" foregroundColor="#00e5b243" backgroundColor="#000000" shadowColor="#000000" halign="right" transparent="1">
					<convert type="EventTime">StartTime</convert>
					<convert type="ClockToText" />
				</widget>
				<widget source="Event" render="Label" position="113, 575" size="100, 30" font="Regular;26" foregroundColor="#00e5b243" backgroundColor="#000000" shadowColor="#000000" halign="left" transparent="1">
					<convert type="EventTime">EndTime</convert>
					<convert type="ClockToText">Format:- %H:%M</convert>
				</widget>
				<widget source="Event" render="Label" position="230,575" size="1010,30" font="Regular;26" foregroundColor="#00e5b243" backgroundColor="#000000" transparent="1" halign="left">
					<convert type="EventName">Name</convert>
				</widget>
				<widget source="Event" render="Label" position="40, 605" zPosition="1" size="1200, 73" font="Regular;20" foregroundColor="#00dddddd" backgroundColor="#000000" shadowColor="#000000" transparent="1">
					<convert type="EventName">ExtendedDescription</convert>
				</widget>
					<ePixmap pixmap="skin_default/buttons/red.png" position="270, 675" size="25,25" alphatest="blend" />
				<widget name="key_red" position="305, 679" size="150, 24" font="Regular;20" foregroundColor="#9F1313" backgroundColor="#000000" shadowColor="#000000" halign="left" valign="top" transparent="1" />
					<ePixmap pixmap="skin_default/buttons/green.png" position="460, 675" size="25,25" alphatest="blend" />
				<widget name="key_green" position="495, 679" size="150, 24" font="Regular;20" foregroundColor="#00389416" backgroundColor="#000000" shadowColor="#000000" halign="left" valign="top" transparent="1" />
					<ePixmap pixmap="skin_default/buttons/yellow.png" position="670, 675" size="25,25" alphatest="blend" />
				<widget name="key_yellow" position="705, 679" size="150, 24" font="Regular;20" foregroundColor="#B59E01" backgroundColor="#000000" shadowColor="#000000" halign="left" valign="top" transparent="1" />
					<ePixmap pixmap="skin_default/buttons/blue.png" position="860, 675" size="25,25" alphatest="blend" />
				<widget name="key_blue" position="895, 679" size="150, 24" font="Regular;20" foregroundColor="#1E28B6" backgroundColor="#000000" shadowColor="#000000" halign="left" valign="top" transparent="1" />
			</screen>"""
		GraphEPGPIG = """
			<screen name="GraphicalEPGPIG" position="center,center" size="1280,720" backgroundColor="#000000" title="Programme Guide" flags="wfNoBorder">
				<eLabel text="Programme Guide" position="460,20" size="480,30" font="Regular;26" foregroundColor="#FFFFFF" backgroundColor="#000000" shadowColor="#000000" halign="center" transparent="1" />
				<widget name="date" position="40,20" size="180,30" font="Regular;26" halign="left" foregroundColor="#00e5b243" backgroundColor="#000000" transparent="1" />
				<widget source="global.CurrentTime" render="Label" position="283, 20" size="90,30" font="Regular;26" foregroundColor="#FFFFFF" backgroundColor="#000000" shadowColor="#000000" halign="right" transparent="1">
					<convert type="ClockToText">Default</convert>
				</widget>
				<widget source="global.CurrentTime" render="Label" position="1070, 20" size="160,30" font="Regular;26" foregroundColor="#FFFFFF" backgroundColor="#000000" shadowColor="#000000" halign="right" transparent="1">
					<convert type="ClockToText">Format:%d.%m.%Y</convert>
				</widget>
				<eLabel position="858,60" size="382,215" zPosition="2" backgroundColor="#000000" foregroundColor="#000000" />
				<widget source="session.VideoPicture" render="Pig" position="860,62" size="378,211" zPosition="3" backgroundColor="#ff000000" />
				<widget source="Event" render="Label" position="5,60" size="100, 30" font="Regular;26" foregroundColor="#00e5b243" backgroundColor="#000000" shadowColor="#000000" halign="right" transparent="1">
					<convert type="EventTime">StartTime</convert>
					<convert type="ClockToText" />
				</widget>
				<widget source="Event" render="Label" position="113,60" size="100, 30" font="Regular;26" foregroundColor="#00e5b243" backgroundColor="#000000" shadowColor="#000000" halign="left" transparent="1">
					<convert type="EventTime">EndTime</convert>
					<convert type="ClockToText">Format:- %H:%M</convert>
				</widget>
				<widget source="Event" render="Label" position="230,60" size="600,30" font="Regular;26" foregroundColor="#00e5b243" backgroundColor="#000000" transparent="1" halign="left">
					<convert type="EventName">Name</convert>
				</widget>
				<widget source="Event" render="Label" position="40,90" zPosition="1" size="790,185" font="Regular;20" foregroundColor="#00dddddd" backgroundColor="#000000" shadowColor="#000000" transparent="1" valign="top">
					<convert type="EventName">ExtendedDescription</convert>
				</widget>
				<widget name="lab1" position="40,320" size="1200,350" font="Regular;24" halign="center" valign="center" backgroundColor="#000000" transparent="0" zPosition="2" />
				<widget name="timeline_text" position="9,290" size="1230,30" foregroundColor="#00e5b243" backgroundColor="#000000" transparent="1" />
				<widget name="list" position="40,320" size="1200,350" scrollbarMode="showNever" transparent="1" />
				<widget name="timeline0" position="0,320" zPosition="1" size="2,350" pixmap="skin_default/timeline.png" />
				<widget name="timeline1" position="0,320" zPosition="1" size="2,350" pixmap="skin_default/timeline.png" />
				<widget name="timeline2" position="0,320" zPosition="1" size="2,350" pixmap="skin_default/timeline.png" />
				<widget name="timeline3" position="0,320" zPosition="1" size="2,350" pixmap="skin_default/timeline.png" />
				<widget name="timeline4" position="0,320" zPosition="1" size="2,350" pixmap="skin_default/timeline.png" />
				<widget name="timeline5" position="0,320" zPosition="1" size="2,350" pixmap="skin_default/timeline.png" />
				<widget name="timeline_now" position="0,320" zPosition="2" size="19,350" pixmap="/usr/share/enigma2/skin_default/GraphEPG/timeline-now.png" alphatest="on" />
				<ePixmap pixmap="skin_default/buttons/red.png" position="270, 675" size="25,25" alphatest="blend" />
				<widget name="key_red" position="305, 679" size="150, 24" font="Regular;20" foregroundColor="#9F1313" backgroundColor="#000000" shadowColor="#000000" halign="left" valign="top" transparent="1" />
				<ePixmap pixmap="skin_default/buttons/green.png" position="460, 675" size="25,25" alphatest="blend" />
				<widget name="key_green" position="495, 679" size="150, 24" font="Regular;20" foregroundColor="#00389416" backgroundColor="#000000" shadowColor="#000000" halign="left" valign="top" transparent="1" />
				<ePixmap pixmap="skin_default/buttons/yellow.png" position="670, 675" size="25,25" alphatest="blend" />
				<widget name="key_yellow" position="705, 679" size="150, 24" font="Regular;20" foregroundColor="#B59E01" backgroundColor="#000000" shadowColor="#000000" halign="left" valign="top" transparent="1" />
				<ePixmap pixmap="skin_default/buttons/blue.png" position="860, 675" size="25,25" alphatest="blend" />
				<widget name="key_blue" position="895, 679" size="150, 24" font="Regular;20" foregroundColor="#1E28B6" backgroundColor="#000000" shadowColor="#000000" halign="left" valign="top" transparent="1" />
			</screen>"""

	else:
		QuickEPG = """
			<screen name="QuickEPG" position="0,325" size="720,276" title="QuickEPG" backgroundColor="transparent" flags="wfNoBorder" >
				<ePixmap alphatest="off" pixmap="DMConcinnity-HD/infobar.png" position="0,0" size="720,156" zPosition="1"/>
				<eLabel backgroundColor="#41080808" position="0,156" size="720,110" zPosition="2"/>
				<widget borderColor="#0f0f0f" borderWidth="1" backgroundColor="#16000000" font="Enigma;24" foregroundColor="#00f0f0f0" halign="left" noWrap="1" position="88,120" render="Label" size="68,28" source="global.CurrentTime" transparent="1" zPosition="3">
					<convert type="ClockToText">Default</convert>
				</widget>		
				<widget borderColor="#0f0f0f" borderWidth="1" backgroundColor="#16000000" font="Enigma;16" noWrap="1" position="54,100" render="Label" size="220,22" source="global.CurrentTime" transparent="1" valign="bottom" zPosition="3">
					<convert type="ClockToText">Date</convert>
				</widget>
				<widget source="Service" render="Picon" position="50,150" size="100,60" transparent="1" zPosition="4" alphatest="blend">
					<convert type="ServiceName">Reference</convert>
				</widget>
				<widget source="Service" render="Label" borderColor="#0f0f0f" borderWidth="1" backgroundColor="#16000000" font="Enigma;24" foregroundColor="#00f0f0f0" halign="center" position="160,120" size="400,28" transparent="1" valign="bottom" zPosition="3" >
					<convert type="ServiceName">Name</convert>
				</widget>
				<widget name="list" position="160,160" size="500,45" backgroundColor="#41080808" foregroundColor="#cccccc" transparent="1" itemHeight="22" zPosition="4"/>
				<ePixmap pixmap="DMConcinnity-HD/buttons/red.png" position="80,210" size="25,25" alphatest="blend" zPosition="4" />
				<widget name="key_red" position="110,213" size="100,20" font="Regular; 17" halign="left" backgroundColor="#101214" foregroundColor="#cccccc" transparent="1" zPosition="4" />
				<ePixmap pixmap="DMConcinnity-HD/buttons/green.png" position="210,210" size="25,25" alphatest="blend" zPosition="4" />
				<widget name="key_green" position="240,213" size="100,20" font="Regular; 17" halign="left" backgroundColor="#101214" foregroundColor="#cccccc" transparent="1" zPosition="4" />
				<ePixmap pixmap="DMConcinnity-HD/buttons/yellow.png" position="340,210" size="25,25" alphatest="blend" zPosition="4" />
				<widget name="key_yellow" position="370,213" size="100,20" font="Regular; 17" halign="left" backgroundColor="#101214" foregroundColor="#cccccc" transparent="1" zPosition="4" />
				<ePixmap pixmap="DMConcinnity-HD/buttons/blue.png" position="470,210" size="25,25" alphatest="blend" zPosition="4" />
				<widget name="key_blue" position="500,213" size="150,20" font="Regular; 17" halign="left" backgroundColor="#101214" foregroundColor="#cccccc" transparent="1" zPosition="4" />
			</screen>"""
		GraphEPG = """
			<screen name="GraphicalEPG" position="center,center" size="720,576" backgroundColor="#000000" title="Programme Guide">
				<widget source="Title" render="Label" position="200,18" size="380,28" font="Regular;22" foregroundColor="#FFFFFF" backgroundColor="#000000" shadowColor="#000000" halign="center" transparent="1" />
				<widget name="date" position="30,18" size="180,24" font="Regular;20" halign="left"  foregroundColor="#00e5b243" backgroundColor="#000000" transparent="1" />
				<widget source="global.CurrentTime" render="Label" position="140, 18" size="90,24" font="Regular;20" foregroundColor="#FFFFFF" backgroundColor="#000000" shadowColor="#000000" halign="right" transparent="1">
						<convert type="ClockToText">Default</convert>
				</widget>
				<widget source="global.CurrentTime" render="Label" position="525, 18" size="160,24" font="Regular;20" foregroundColor="#FFFFFF" backgroundColor="#000000" shadowColor="#000000" halign="right" transparent="1">
					<convert type="ClockToText">Format:%d.%m.%Y</convert>
				</widget>
				<widget name="timeline_text" position="10, 40" size="690,25" foregroundColor="#00e5b243" backgroundColor="#000000" transparent="1"/>
				<widget name="lab1" position="25,65" size="665,378" font="Regular;24" halign="center" valign="center" backgroundColor="#000000" transparent="0" zPosition="2" />
				<widget name="list" position="25,65" size="665,378" scrollbarMode="showNever" transparent="1" />
				<widget name="timeline0" position="0,140" zPosition="1" size="0,0" pixmap="skin_default/timeline.png" />
				<widget name="timeline1" position="0,140" zPosition="1" size="0,0" pixmap="skin_default/timeline.png" />
				<widget name="timeline2" position="0,140" zPosition="1" size="0,0" pixmap="skin_default/timeline.png" />
				<widget name="timeline3" position="0,140" zPosition="1" size="0,0" pixmap="skin_default/timeline.png" />
				<widget name="timeline4" position="0,140" zPosition="1" size="0,0" pixmap="skin_default/timeline.png" />
				<widget name="timeline5" position="0,140" zPosition="1" size="0,0" pixmap="skin_default/timeline.png" />
				<widget name="timeline_now" position="10, 65" zPosition="2" size="19, 378" pixmap="/usr/share/enigma2/skin_default/GraphEPG/timeline-now.png" alphatest="on" />
				<widget source="Event" render="Label" position="10,445" size="70,26" font="Regular;22" foregroundColor="#00e5b243" backgroundColor="#000000" shadowColor="#000000" halign="right" transparent="1">
					<convert type="EventTime">StartTime</convert>
					<convert type="ClockToText" />
				</widget>
				<widget source="Event" render="Label" position="88,445" size="80,26" font="Regular;22" foregroundColor="#00e5b243" backgroundColor="#000000" shadowColor="#000000" halign="left" transparent="1">
					<convert type="EventTime">EndTime</convert>
					<convert type="ClockToText">Format:- %H:%M</convert>
				</widget>
				<widget source="Event" render="Label" position="165,445" size="535,26" font="Regular;22" foregroundColor="#00e5b243" backgroundColor="#000000" transparent="1" halign="left">
					<convert type="EventName">Name</convert>
				</widget>
				<widget source="Event" render="Label" position="30, 465" zPosition="1" size="667, 75" font="Regular;18" foregroundColor="#00dddddd" backgroundColor="#000000" shadowColor="#000000" transparent="1">
					<convert type="EventName">ExtendedDescription</convert>
				</widget>
				<ePixmap pixmap="skin_default/buttons/red.png" position="70, 537" size="18,18" alphatest="blend" />
				<widget name="key_red" position="95, 539" size="125, 26" font="Regular;18" foregroundColor="#9F1313" backgroundColor="#000000" shadowColor="#000000" halign="left" valign="top" transparent="1" />
				<ePixmap pixmap="skin_default/buttons/green.png" position="220, 537" size="18,18" alphatest="blend" />
				<widget name="key_green" position="245, 539" size="125, 26" font="Regular;18" foregroundColor="#00389416" backgroundColor="#000000" shadowColor="#000000" halign="left" valign="top" transparent="1" />
				<ePixmap pixmap="skin_default/buttons/yellow.png" position="370, 537" size="18,18" alphatest="blend" />
				<widget name="key_yellow" position="395, 539" size="125, 26" font="Regular;18" foregroundColor="#B59E01" backgroundColor="#000000" shadowColor="#000000" halign="left" valign="top" transparent="1" />
				<ePixmap pixmap="skin_default/buttons/blue.png" position="520, 537" size="18,18" alphatest="blend" />
				<widget name="key_blue" position="545, 539" size="125, 26" font="Regular;18" foregroundColor="#1E28B6" backgroundColor="#000000" shadowColor="#000000" halign="left" valign="top" transparent="1" />
			</screen>
			"""
		GraphEPGPIG = """
			<screen name="GraphicalEPG" position="center,center" size="720,576" backgroundColor="#000000" title="Programme Guide" flags="wfNoBorder">
				<widget source="Title" render="Label" position="200,18" size="380,28" font="Regular;22" foregroundColor="#FFFFFF" backgroundColor="#000000" shadowColor="#000000" halign="center" transparent="1" />
				<widget name="date" position="30,18" size="180,24" font="Regular;20" halign="left" foregroundColor="#00e5b243" backgroundColor="#000000" transparent="1" />
				<widget source="global.CurrentTime" render="Label" position="140, 18" size="90,24" font="Regular;20" foregroundColor="#FFFFFF" backgroundColor="#000000" shadowColor="#000000" halign="right" transparent="1">
					<convert type="ClockToText">Default</convert>
				</widget>
				<widget source="global.CurrentTime" render="Label" position="525, 18" size="160,24" font="Regular;20" foregroundColor="#FFFFFF" backgroundColor="#000000" shadowColor="#000000" halign="right" transparent="1">
					<convert type="ClockToText">Format:%d.%m.%Y</convert>
				</widget>
				<widget source="Event" render="Label" position="10,47" size="70,26" font="Regular;22" foregroundColor="#00e5b243" backgroundColor="#000000" shadowColor="#000000" halign="right" transparent="1">
					<convert type="EventTime">StartTime</convert>
					<convert type="ClockToText" />
				</widget>
				<widget source="Event" render="Label" position="88,47" size="80,26" font="Regular;22" foregroundColor="#00e5b243" backgroundColor="#000000" shadowColor="#000000" halign="left" transparent="1">
					<convert type="EventTime">EndTime</convert>
					<convert type="ClockToText">Format:- %H:%M</convert>
				</widget>
				<widget source="Event" render="Label" position="165,47" size="535,26" font="Regular;22" foregroundColor="#00e5b243" backgroundColor="#000000" transparent="1" halign="left">
					<convert type="EventName">Name</convert>
				</widget>
				<widget source="Event" render="Label" position="30,73" zPosition="1" size="375,125" font="Regular;18" foregroundColor="#00dddddd" backgroundColor="#000000" shadowColor="#000000" transparent="1" valign="top">
					<convert type="EventName">ExtendedDescription</convert>
				</widget>
				<eLabel position="413,45" size="273,154" zPosition="2" backgroundColor="#000000" foregroundColor="#000000" />
				<widget name="lab1" position="25,235" size="665,278" font="Regular;24" halign="center" valign="center" backgroundColor="#000000" transparent="0" zPosition="2" />
				<widget source="session.VideoPicture" render="Pig" position="415,47" size="269,150" zPosition="3" backgroundColor="#ff000000" />
				<widget name="timeline_text" position="10,210" size="690,25" foregroundColor="#00e5b243" backgroundColor="#000000" transparent="1" />
				<widget name="list" position="25,235" size="665,278" scrollbarMode="showNever" transparent="1" />
				<widget name="timeline0" position="0,235" zPosition="1" size="0,0" pixmap="skin_default/timeline.png" />
				<widget name="timeline1" position="0,235" zPosition="1" size="0,0" pixmap="skin_default/timeline.png" />
				<widget name="timeline2" position="0,235" zPosition="1" size="0,0" pixmap="skin_default/timeline.png" />
				<widget name="timeline3" position="0,235" zPosition="1" size="0,0" pixmap="skin_default/timeline.png" />
				<widget name="timeline4" position="0,235" zPosition="1" size="0,0" pixmap="skin_default/timeline.png" />
				<widget name="timeline5" position="0,235" zPosition="1" size="0,0" pixmap="skin_default/timeline.png" />
				<widget name="timeline_now" position="10,235" zPosition="2" size="19,278" pixmap="/usr/share/enigma2/skin_default/GraphEPG/timeline-now.png" alphatest="on" />
				<ePixmap pixmap="skin_default/buttons/red.png" position="70, 537" size="18,18" alphatest="blend" />
				<widget name="key_red" position="95, 539" size="125, 26" font="Regular;18" foregroundColor="#9F1313" backgroundColor="#000000" shadowColor="#000000" halign="left" valign="top" transparent="1" />
				<ePixmap pixmap="skin_default/buttons/green.png" position="220, 537" size="18,18" alphatest="blend" />
				<widget name="key_green" position="245, 539" size="125, 26" font="Regular;18" foregroundColor="#00389416" backgroundColor="#000000" shadowColor="#000000" halign="left" valign="top" transparent="1" />
				<ePixmap pixmap="skin_default/buttons/yellow.png" position="370, 537" size="18,18" alphatest="blend" />
				<widget name="key_yellow" position="395, 539" size="125, 26" font="Regular;18" foregroundColor="#B59E01" backgroundColor="#000000" shadowColor="#000000" halign="left" valign="top" transparent="1" />
				<ePixmap pixmap="skin_default/buttons/blue.png" position="520, 537" size="18,18" alphatest="blend" />
				<widget name="key_blue" position="545, 539" size="125, 26" font="Regular;18" foregroundColor="#1E28B6" backgroundColor="#000000" shadowColor="#000000" halign="left" valign="top" transparent="1" />
			</screen>"""
	EMPTY = 0
	ADD_TIMER = 1
	REMOVE_TIMER = 2
	
	ZAP = 1

	def __init__(self, session, service, zapFunc=None, eventid=None, bouquetChangeCB=None, serviceChangeCB=None, EPGtype = None,  bouquetname=""):
		Screen.__init__(self, session)
		if EPGtype:
			self.StartBouquet = EPGtype
			EPGtype = None
		if zapFunc == 'infobar':
			self.InfobarEPG = True
			zapFunc = None
		else:
			self.InfobarEPG = False
		if serviceChangeCB == 'graph':
			self.GraphicalEPG = True
			serviceChangeCB = None
		else:
			self.GraphicalEPG = False
		self.bouquetChangeCB = bouquetChangeCB
		self.serviceChangeCB = serviceChangeCB
		self.ask_time = -1 #now
		self.closeRecursive = False
		self.saved_title = None
		self.oldService = ""
		self["Service"] = ServiceEvent()
		self["Event"] = Event()
		Screen.setTitle(self, _("Programme Guide"))
		if isinstance(service, str) and eventid != None:
			self.type = EPG_TYPE_SIMILAR
			self["key_yellow"] = Button()
			self["key_blue"] = Button()
			self["key_red"] = Button()
			self["key_green"] = Button()
			self.currentService=service
			self.eventid = eventid
			self.zapFunc = None
		elif isinstance(service, list):
			if self.GraphicalEPG:
				self.type = EPG_TYPE_GRAPH
				if not config.GraphEPG.PIG.value:
					self.skin = self.GraphEPG
					self.skinName = "GraphicalEPG"
				else:
					self.skin = self.GraphEPGPIG
					self.skinName = "GraphicalEPGPIG"
				now = time()
				tmp = now % 900
				self.ask_time = now - tmp
				self.closeRecursive = False
				self.key_red_choice = self.EMPTY
				self.key_green_choice = self.EMPTY
				self.key_yellow_choice = self.EMPTY
				self.key_blue_choice = self.EMPTY
				self['lab1'] = Label()
				self["timeline_text"] = TimelineText()
				self["Event"] = Event()
				self.time_lines = [ ]
				for x in (0,1,2,3,4,5):
					pm = Pixmap()
					self.time_lines.append(pm)
					self["timeline%d"%(x)] = pm
				self["timeline_now"] = Pixmap()
				self["key_red"] = Button(_("IMDb Search"))
				self["key_green"] = Button(_("Add Timer"))
				self["key_yellow"] = Button(_("EPG Search"))
				self["key_blue"] = Button(_("Add AutoTimer"))
				self["date"] = Label()
				self.services = service
				self.zapFunc = zapFunc
				if bouquetname != "":
					Screen.setTitle(self, bouquetname)
			else:
				self.type = EPG_TYPE_MULTI
				self.skinName = "EPGSelectionMulti"
				self["key_red"] = Button(_("IMDb Search"))
				self["key_green"] = Button(_("Add Timer"))
				self["key_yellow"] = Button(_("EPG Search"))
				self["key_blue"] = Button(_("Add AutoTimer"))
				self["now_button"] = Pixmap()
				self["next_button"] = Pixmap()
				self["more_button"] = Pixmap()
				self["now_button_sel"] = Pixmap()
				self["next_button_sel"] = Pixmap()
				self["more_button_sel"] = Pixmap()
				self["now_text"] = Label()
				self["next_text"] = Label()
				self["more_text"] = Label()
				self["date"] = Label()
				self.services = service
				self.zapFunc = zapFunc

		elif isinstance(service, eServiceReference) or isinstance(service, str):
			self["key_red"] = Button(_("IMDb Search"))
			self["key_yellow"] = Button(_("EPG Search"))
			self["key_blue"] = Button(_("Add AutoTimer"))
			self["key_green"] = Button(_("Add Timer"))
			self.type = EPG_TYPE_SINGLE
			self.currentService=ServiceReference(service)
			self.zapFunc = None
		else:
			if self.InfobarEPG:
				self.type = EPG_TYPE_INFOBAR
				self.skin = self.QuickEPG
				self.skinName = "QuickEPG"
			else:
				self.type = EPG_TYPE_ENHANCED
			self["key_red"] = Button(_("IMDb Search"))
			self["key_yellow"] = Button(_("EPG Search"))
			self["key_blue"] = Button(_("Add AutoTimer"))
			self["key_green"] = Button(_("Add Timer"))
			self.list = []
			self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()
			self.currentService=self.session.nav.getCurrentlyPlayingServiceReference()
			self.zapFunc = None

		self.key_green_choice = self.ADD_TIMER
		self.key_red_choice = self.EMPTY
		self["list"] = EPGList(type = self.type, selChangedCB = self.onSelectionChanged, timer = session.nav.RecordTimer, time_epoch = config.GraphEPG.prev_time_period.value, overjump_empty = config.GraphEPG.overjump.value)

		if self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
			if self.type == EPG_TYPE_ENHANCED:
				self["actions"] = ActionMap(["OkCancelActions", "InfobarInstantRecord", "EPGSelectActions", "ChannelSelectBaseActions", "ColorActions", "DirectionActions", "HelpActions"], 
				{
					"ok": self.ZapTo, 
					"cancel": self.closing,
					"nextBouquet": self.nextBouquet,
					"prevBouquet": self.prevBouquet,
					"nextService": self.nextService,
					"prevService": self.prevService,
		#			"prevBouquet": self.openServiceList,
					"red": self.redButtonPressed,
					"timerAdd": self.timerAdd,
					"yellow": self.yellowButtonPressed,
					"blue": self.blueButtonPressed,
					"Info": self.infoKeyPressed,
					"ShortRecord": self.doRecordTimer,
					"LongRecord": self.doZapTimer,
					"Menu": self.createSetup,
					},-2)
				self["actions2"] = NumberActionMap(["NumberActions"],
				{
					"1": self.keyNumberGlobal,
					"2": self.keyNumberGlobal,
					"3": self.keyNumberGlobal,
					"4": self.keyNumberGlobal,
					"5": self.keyNumberGlobal,
					"6": self.keyNumberGlobal,
					"7": self.keyNumberGlobal,
					"8": self.keyNumberGlobal,
					"9": self.keyNumberGlobal,
				}, -1)
			elif self.type == EPG_TYPE_INFOBAR:
				self["actions"] = ActionMap(["OkCancelActions", "InfobarInstantRecord", "EPGSelectActions", "ChannelSelectBaseActions", "ColorActions", "DirectionActions", "HelpActions"], 
				{
					"ok": self.ZapTo, 
					"cancel": self.closing,
					"right": self.nextService,
					"left": self.prevService,
					"nextBouquet": self.nextBouquet,
					"prevBouquet": self.prevBouquet,
					"nextService": self.nextPage,
					"prevService": self.prevPage,
		#			"prevBouquet": self.openServiceList,
					"red": self.redButtonPressed,
					"timerAdd": self.timerAdd,
					"yellow": self.yellowButtonPressed,
					"blue": self.blueButtonPressed,
					"Info": self.infoKeyPressed,
					"ShortRecord": self.doRecordTimer,
					"LongRecord": self.doZapTimer,
					"Menu": self.createSetup,
					},-2)
				self["actions2"] = NumberActionMap(["NumberActions"],
				{
					"1": self.keyNumberGlobal,
					"2": self.keyNumberGlobal,
					"3": self.keyNumberGlobal,
					"4": self.keyNumberGlobal,
					"5": self.keyNumberGlobal,
					"6": self.keyNumberGlobal,
					"7": self.keyNumberGlobal,
					"8": self.keyNumberGlobal,
					"9": self.keyNumberGlobal,
				}, -1)
			self.onLayoutFinish.append(self.onCreate)
			self.servicelist = service
			self.servicelist_orig_zap = self.servicelist.zap 
			self.servicelist.zap = self.servicelist_overwrite_zap
			self.servicelist["actions"] = ActionMap(["OkCancelActions"],
				{
					"cancel": self.cancelChannelSelection,
					"ok": self.servicelist.channelSelected,
				})
			# temp. vars, needed when pressing cancel in ChannelSelection
			self.curSelectedRef = None
			self.curSelectedBouquet = None
			# needed, because if we won't zap, we have to go back to the current bouquet and service
			self.curRef = ServiceReference(self.servicelist.getCurrentSelection())
			self.curBouquet = self.servicelist.getRoot()
			self.startRef = ServiceReference(self.servicelist.getCurrentSelection())
			self.onClose.append(self.__onClose)
		elif self.type == EPG_TYPE_GRAPH:
			self["actions"] = ActionMap(["OkCancelActions", "InfobarInstantRecord", "EPGSelectActions", "ChannelSelectBaseActions", "ColorActions", "DirectionActions", "HelpActions"],
				{
					"cancel": self.closing,
					"displayHelp": self.myhelp,
					"nextBouquet": self.nextService,
					"prevBouquet": self.prevService,
					"prevService": self.prevBouquet,
					"nextService": self.nextBouquet,
					"input_date_time": self.enterDateTime,
					"red": self.redButtonPressed,
					"timerAdd": self.timerAdd,
					"yellow": self.yellowButtonPressed,
					"blue": self.blueButtonPressed,
					"OK": self.OK,
					"OKLong": self.OKLong,
					"Info": self.Info,
					"InfoLong": self.InfoLong,
					"ShortRecord": self.doRecordTimer,
					"LongRecord": self.doZapTimer,
					"Menu": self.createSetup,
				},-1)

			self["input_actions"] = ActionMap(["InputActions"],
				{
					"left": self.leftPressed,
					"right": self.rightPressed,
					"1": self.key1,
					"2": self.key2,
					"3": self.key3,
					"4": self.key4,
					"5": self.key5,
					"6": self.key6,
					"7": self.key7,
					"8": self.key8,
					"9": self.key9,
					"0": self.key0,
				},-1)
			self.curBouquet = bouquetChangeCB
			self.updateTimelineTimer = eTimer()
			self.updateTimelineTimer.callback.append(self.moveTimeLines)
			self.updateTimelineTimer.start(60*1000)
			self.activityTimer = eTimer()
			self.activityTimer.timeout.get().append(self.onStartup)
			self.updateList()
		elif self.type == EPG_TYPE_MULTI:
			self["actions"] = ActionMap(["EPGSelectActions", "OkCancelActions", "ColorActions"],
			{
				"ok": self.ZapTo,
				"cancel": self.closing,
				"red": self.redButtonPressed,
				"timerAdd": self.timerAdd,
				"yellow": self.yellowButtonPressed,
				"blue": self.blueButtonPressed,
				"Info": self.infoKeyPressed,
				"input_date_time": self.enterDateTime,
				"nextBouquet": self.nextBouquet,
				"prevBouquet": self.prevBouquet,
				"nextService": self.nextPage,
				"prevService": self.prevPage,
			})
			self["MenuActions"] = HelpableActionMap(self, "MenuActions",
				{
					"menu": (self.createSetup, _("Open Context Menu"))
				}
			)
			self["input_actions"] = ActionMap(["InputActions"],
				{
					"left": self.leftPressed,
					"right": self.rightPressed,
				},-1)
			self.onLayoutFinish.append(self.onStartup)
		else:
			self["actions"] = ActionMap(["EPGSelectActions", "InfobarInstantRecord", "OkCancelActions", "ColorActions"],
			{
				"ok": self.ZapTo,
				"cancel": self.closing,
				"red": self.redButtonPressed,
				"timerAdd": self.timerAdd,
				"yellow": self.yellowButtonPressed,
				"blue": self.blueButtonPressed,
				"Info": self.infoKeyPressed,
				"input_date_time": self.enterDateTime,
				"nextBouquet": self.nextBouquet,
				"prevBouquet": self.prevBouquet,
				"nextService": self.nextPage,
				"prevService": self.prevPage,
				"ShortRecord": self.doRecordTimer,
				"LongRecord": self.doZapTimer,
			})
			self["MenuActions"] = HelpableActionMap(self, "MenuActions",
				{
					"menu": (self.createSetup, _("Open Context Menu"))
				}
			)
			self.onLayoutFinish.append(self.onStartup)

	def createSetup(self):
		self.session.openWithCallback(self.onSetupClose, EPGSelectionSetup, self.type)

	def onSetupClose(self):
		if self.type == EPG_TYPE_GRAPH:
			l = self["list"]
			l.setItemsPerPage()
			l.setEventFontsize()
			l.setServiceFontsize()
			l.setEpoch(config.GraphEPG.prev_time_period.value)
			l.setOverjump_Empty(config.GraphEPG.overjump.value)
			self.moveTimeLines()
		else:
			if config.misc.EPGSort.value == "Time":
				self.sort_type = 0
			else:
				self.sort_type = 1
			l = self["list"]
			l.sortSingleEPG(self.sort_type)

	def updateList(self):
		scanning = _('Wait please while gathering data...')
		self['lab1'].setText(scanning)
		self.activityTimer.start(750)

	def onStartup(self):
		if self.type == EPG_TYPE_GRAPH:
			self.activityTimer.stop()
			self["list"].curr_refcool = self.session.nav.getCurrentlyPlayingServiceReference()
			self["list"].fillGraphEPG(self.services, self.ask_time)
			self["list"].moveToService(self.session.nav.getCurrentlyPlayingServiceReference())
			self.startRef = self["list"].getCurrent()[1]
			self.moveTimeLines()
			if config.GraphEPG.channel1.value:
				self["list"].instance.moveSelectionTo(0)
			self['lab1'].hide()
		else:
			l = self["list"]
			l.recalcEntrySize()
			if self.type == EPG_TYPE_MULTI or self.type == EPG_TYPE_GRAPH:
				l.fillMultiEPG(self.services, self.ask_time)
				l.moveToService(self.session.nav.getCurrentlyPlayingServiceReference())
			elif self.type == EPG_TYPE_SINGLE:
				service = self.currentService
				self["Service"].newService(service.ref)
				if self.saved_title is None:
					self.saved_title = self.instance.getTitle()
				title = self.saved_title + ' - ' + service.getServiceName()
				self.instance.setTitle(title)
				l.fillSingleEPG(service)
			elif self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
				service = ServiceReference(self.servicelist.getCurrentSelection())
				self["Service"].newService(service.ref)
				if self.saved_title is None:
					self.saved_title = self.instance.getTitle()
				title = self.saved_title + ' - ' + service.getServiceName()
				self.instance.setTitle(title)
				l.fillSingleEPG(service)
			else:
				l.fillSimilarList(self.currentService, self.eventid)
			if self.type == EPG_TYPE_SINGLE or self.type == EPG_TYPE_ENHANCED:
				if config.misc.EPGSort.value == "Time":
					self.sort_type = 0
				else:
					self.sort_type = 1
				l.sortSingleEPG(self.sort_type)
			self.startRef = self["list"].getCurrent()[1]

	def onCreate(self):
		if self.type == EPG_TYPE_GRAPH:
			self.activityTimer.stop()
			self["list"].curr_refcool = self.session.nav.getCurrentlyPlayingServiceReference()
			self["list"].fillGraphEPG(self.services, self.ask_time)
			self["list"].moveToService(self.session.nav.getCurrentlyPlayingServiceReference())
			self.moveTimeLines()
			if config.GraphEPG.channel1.value:
				self["list"].instance.moveSelectionTo(0)
			self['lab1'].hide()
		else:
			l = self["list"]
			l.recalcEntrySize()
			if self.type == EPG_TYPE_MULTI or self.type == EPG_TYPE_GRAPH:
				l.fillMultiEPG(self.services, self.ask_time)
				l.moveToService(self.session.nav.getCurrentlyPlayingServiceReference())
			elif self.type == EPG_TYPE_SINGLE:
				service = self.currentService
				self["Service"].newService(service.ref)
				if self.saved_title is None:
					self.saved_title = self.instance.getTitle()
				title = self.saved_title + ' - ' + service.getServiceName()
				self.instance.setTitle(title)
				l.fillSingleEPG(service)
			elif self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
				service = ServiceReference(self.servicelist.getCurrentSelection())
				self["Service"].newService(service.ref)
				if self.saved_title is None:
					self.saved_title = self.instance.getTitle()
				title = self.saved_title + ' - ' + service.getServiceName()
				self.instance.setTitle(title)
				l.fillSingleEPG(service)
			else:
				l.fillSimilarList(self.currentService, self.eventid)
			if self.type == EPG_TYPE_SINGLE or self.type == EPG_TYPE_ENHANCED:
				if config.misc.EPGSort.value == "Time":
					self.sort_type = 0
				else:
					self.sort_type = 1
				l.sortSingleEPG(self.sort_type)

	def nextPage(self):
		self["list"].instance.moveSelection(self["list"].instance.pageUp)

	def prevPage(self):
		self["list"].instance.moveSelection(self["list"].instance.pageDown)

	def leftPressed(self):
		if self.type == EPG_TYPE_MULTI:
			self["list"].updateMultiEPG(-1)
		else:
			self.updEvent(-1)

	def rightPressed(self):
		if self.type == EPG_TYPE_MULTI:
			self["list"].updateMultiEPG(1)
		else:
			self.updEvent(+1)
		
	def nextBouquet(self):
		if (self.type != EPG_TYPE_ENHANCED or self.type == EPG_TYPE_GRAPH) and self.bouquetChangeCB:
			self.bouquetChangeCB(1, self)
		elif self.type == EPG_TYPE_ENHANCED and config.usage.multibouquet.value:
			self.servicelist.nextBouquet()
			self.onCreate()

	def prevBouquet(self):
		if (self.type != EPG_TYPE_ENHANCED or self.type == EPG_TYPE_GRAPH) and self.bouquetChangeCB:
			self.bouquetChangeCB(-1, self)
		elif self.type == EPG_TYPE_ENHANCED and config.usage.multibouquet.value:
			self.servicelist.prevBouquet()
			self.onCreate()

	def Bouquetlist(self):
		if self.bouquetChangeCB:
			self.bouquetChangeCB(0, self)

	def nextService(self):
		if self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
			self["list"].instance.moveSelectionTo(0)
			if self.servicelist.inBouquet():
				prev = self.servicelist.getCurrentSelection()
				if prev:
					prev = prev.toString()
					while True:
						if config.usage.quickzap_bouquet_change.value and self.servicelist.atEnd():
							self.servicelist.nextBouquet()
						else:
							self.servicelist.moveDown()
						cur = self.servicelist.getCurrentSelection()
						if not cur or (not (cur.flags & 64)) or cur.toString() == prev:
							break
			else:
				self.servicelist.moveDown()
			if self.isPlayable():
				self.onCreate()
			else:
				self.nextService()
		elif self.type == EPG_TYPE_GRAPH:
			coolhilf = config.GraphEPG.prev_time_period.value	
			if coolhilf == 60:
				for i in range(24):
					self.updEvent(+2)
			if coolhilf == 120:
				for i in range(12):
					self.updEvent(+2)
			if coolhilf == 180:
				for i in range(8):
					self.updEvent(+2)
			if coolhilf == 240:
				for i in range(6):
					self.updEvent(+2)
			if coolhilf == 300:
				for i in range(4):
					self.updEvent(+2)
		else:
			if self.serviceChangeCB:
				self.serviceChangeCB(1, self)

	def prevService(self):
		if self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
			self["list"].instance.moveSelectionTo(0)
			if self.servicelist.inBouquet():
				prev = self.servicelist.getCurrentSelection()
				if prev:
					prev = prev.toString()
					while True:
						if config.usage.quickzap_bouquet_change.value:
							if self.servicelist.atBegin():
								self.servicelist.prevBouquet()
						self.servicelist.moveUp()
						cur = self.servicelist.getCurrentSelection()
						if not cur or (not (cur.flags & 64)) or cur.toString() == prev:
							break
			else:
				self.servicelist.moveUp()
			if self.isPlayable():
				self.onCreate()
			else:
				self.prevService()
		elif self.type == EPG_TYPE_GRAPH:
			coolhilf = config.GraphEPG.prev_time_period.value
			if coolhilf == 60:
				for i in range(24):
					self.updEvent(-2)
			if coolhilf == 120:
				for i in range(12):
					self.updEvent(-2)
			if coolhilf == 180:
				for i in range(8):
					self.updEvent(-2)
			if coolhilf == 240:
				for i in range(6):
					self.updEvent(-2)
			if coolhilf == 300:
				for i in range(4):
					self.updEvent(-2)
		else:
			if self.serviceChangeCB:
				self.serviceChangeCB(-1, self)

	def enterDateTime(self):
		if self.type == EPG_TYPE_MULTI:
			global mepg_config_initialized
			if not mepg_config_initialized:
				config.misc.prev_mepg_time=ConfigClock(default = time())
				mepg_config_initialized = True
			self.session.openWithCallback(self.onDateTimeInputClosed, TimeDateInput, config.misc.prev_mepg_time )
		elif self.type == EPG_TYPE_GRAPH:
			self.session.openWithCallback(self.onDateTimeInputClosed, TimeDateInput, config.GraphEPG.prev_time)

	def onDateTimeInputClosed(self, ret):
		if self.type == EPG_TYPE_MULTI:
			if len(ret) > 1:
				if ret[0]:
					self.ask_time=ret[1]
					self["list"].fillMultiEPG(self.services, ret[1])
		elif self.type == EPG_TYPE_GRAPH:
			if len(ret) > 1:
				if ret[0]:
					self.ask_time=ret[1]
					l = self["list"]
					l.resetOffset()
					l.fillGraphEPG(self.services, ret[1])
					self.moveTimeLines(True)

	def closing(self):
		if self.type != EPG_TYPE_GRAPH and self.type != EPG_TYPE_MULTI:
			try:
				if self.oldService:
					self.session.nav.playService(self.oldService)
				self.setServicelistSelection(self.curBouquet, self.curRef.ref)
			except:
				pass
		else:
			try:
				self.zapFunc(self.startRef.ref, self.StartBouquet)
			except:
				pass
		self.close(self.closeRecursive)

	def GraphEPGClose(self):
		self.closeRecursive = True
		ref = self["list"].getCurrent()[1]
		if ref:
			self.closeScreen()		

	def closeScreen(self):
		if self.type == EPG_TYPE_GRAPH:
			config.GraphEPG.save()
		self.close(self.closeRecursive)

	def infoKeyPressed(self):
		cur = self["list"].getCurrent()
		event = cur[0]
		service = cur[1]
		if event is not None:
			if self.type != EPG_TYPE_SIMILAR:
				self.session.open(EventViewSimple, event, service, self.eventViewCallback, self.openSimilarList)
			else:
				self.session.open(EventViewSimple, event, service, self.eventViewCallback)

	def openSimilarList(self, eventid, refstr):
		self.session.open(EPGSelection, refstr, None, eventid)

	def setServices(self, services):
		self.services = services
		self.onCreate()

	def setService(self, service):
		self.currentService = service
		self.onCreate()

	def eventViewCallback(self, setEvent, setService, val):
		l = self["list"]
		old = l.getCurrent()
		if self.type == EPG_TYPE_GRAPH:
			self.updEvent(val, False)
		else:
			if val == -1:
				self.moveUp()
			elif val == +1:
				self.moveDown()
		cur = l.getCurrent()
		if (self.type == EPG_TYPE_MULTI or self.type == EPG_TYPE_GRAPH) and cur[0] is None and cur[1].ref != old[1].ref:
			self.eventViewCallback(setEvent, setService, val)
		else:
			setService(cur[1])
			setEvent(cur[0])

	def eventSelected(self):
		self.infoKeyPressed()

	def setSortDescription(self):
		if config.misc.EPGSort.value == "Time":
			self.sort_type = 1
		else:
			self.sort_type = 0
		print 'SORT',config.misc.EPGSort.value
		self["list"].sortSingleEPG(self.sort_type)

	def OpenSingleEPG(self):
		cur = self["list"].getCurrent()
		event = cur[0]
		serviceref = cur[1]
		refstr = serviceref.ref.toString()
		if event is not None:
			self.session.open(SingleEPG, refstr)		

	def redButtonPressed(self):
		try:
			from Plugins.Extensions.IMDb.plugin import IMDB, IMDBEPGSelection
			try:
				cur = self["list"].getCurrent()
				event = cur[0]
				name = event.getEventName()
			except:
				name = ''
			self.session.open(IMDB, name, False)
		except ImportError:
			self.session.open(MessageBox, _("The IMDb plugin is not installed!\nPlease install it."), type = MessageBox.TYPE_INFO,timeout = 10 )

	def yellowButtonPressed(self):
		try:
			from Plugins.Extensions.EPGSearch.EPGSearch import EPGSearch
			try:
				cur = self["list"].getCurrent()
				event = cur[0]
				name = event.getEventName()
			except:
				name = ''
			self.session.open(EPGSearch, name, False)
		except ImportError:
			self.session.open(MessageBox, _("The EPGSearch plugin is not installed!\nPlease install it."), type = MessageBox.TYPE_INFO,timeout = 10 )

	def blueButtonPressed(self):
		try:
			from Plugins.Extensions.AutoTimer.AutoTimerEditor import addAutotimerFromEvent
			cur = self["list"].getCurrent()
			event = cur[0]
			if not event: return
			serviceref = cur[1]
			addAutotimerFromEvent(self.session, evt = event, service = serviceref)
		except ImportError:
			self.session.open(MessageBox, _("The AutoTimer plugin is not installed!\nPlease install it."), type = MessageBox.TYPE_INFO,timeout = 10 )

	def removeTimer(self, timer):
		timer.afterEvent = AFTEREVENT.NONE
		self.session.nav.RecordTimer.removeEntry(timer)
		self["key_green"].setText(_("Add Timer"))
		self.key_green_choice = self.ADD_TIMER

	def timerAdd(self):
		cur = self["list"].getCurrent()
		event = cur[0]
		serviceref = cur[1]
		if event is None:
			return
		eventid = event.getEventId()
		refstr = serviceref.ref.toString()
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and timer.service_ref.ref.toString() == refstr:
				cb_func = lambda ret : not ret or self.removeTimer(timer)
				self.session.openWithCallback(cb_func, MessageBox, _("Do you really want to delete %s?") % event.getEventName())
				break
		else:
			newEntry = RecordTimerEntry(serviceref, checkOldTimers = True, dirname = preferredTimerPath(), *parseEvent(event))
			self.session.openWithCallback(self.finishedAdd, TimerEntry, newEntry)

	def finishedAdd(self, answer):
		print "finished add"
		if answer[0]:
			entry = answer[1]
			simulTimerList = self.session.nav.RecordTimer.record(entry)
			if simulTimerList is not None:
				for x in simulTimerList:
					if x.setAutoincreaseEnd(entry):
						self.session.nav.RecordTimer.timeChanged(x)
				simulTimerList = self.session.nav.RecordTimer.record(entry)
				if simulTimerList is not None:
					self.session.openWithCallback(self.finishSanityCorrection, TimerSanityConflict, simulTimerList)
			self["key_green"].setText(_("Remove timer"))
			self.key_green_choice = self.REMOVE_TIMER
		else:
			self["key_green"].setText(_("Add Timer"))
			self.key_green_choice = self.ADD_TIMER
			print "Timeredit aborted"
	
	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def doRecordTimer(self):
		zap = False
		cur = self["list"].getCurrent()
		event = cur[0]
		serviceref = cur[1]
		if event is None:
			return
		eventid = event.getEventId()
		refstr = serviceref.ref.toString()
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and timer.service_ref.ref.toString() == refstr:
				cb_func = lambda ret : not ret or self.removeTimer(timer)
				self.session.openWithCallback(cb_func, MessageBox, _("Do you really want to delete %s?") % event.getEventName())
				break
		else:
			newEntry = RecordTimerEntry(serviceref, checkOldTimers = True, *parseEvent(event))
			self.session.openWithCallback(self.finishedAdd, RecordSetup, newEntry, zap)

	def doZapTimer(self):
		zap = True
		cur = self["list"].getCurrent()
		event = cur[0]
		serviceref = cur[1]
		if event is None:
			return
		eventid = event.getEventId()
		refstr = serviceref.ref.toString()
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and timer.service_ref.ref.toString() == refstr:
				cb_func = lambda ret : not ret or self.removeTimer(timer)
				self.session.openWithCallback(cb_func, MessageBox, _("Do you really want to delete %s?") % event.getEventName())
				break
		else:
			newEntry = RecordTimerEntry(serviceref, checkOldTimers = True, *parseEvent(event))
			self.session.openWithCallback(self.finishedAdd, RecordSetup, newEntry, zap)

	def moveUp(self):
		self["list"].moveUp()

	def moveDown(self):
		self["list"].moveDown()
	
	def updEvent(self, dir, visible=True):
		ret = self["list"].selEntry(dir, visible)
		if ret:
			self.moveTimeLines(True)		

	def myhelp(self):
		self.session.open(GraphEPGHelp, "/usr/share/enigma2/skin_default/GraphEPG/help.jpg")

	def key1(self):
		hilf = config.GraphEPG.prev_time_period.value	
		if hilf > 60:
			hilf = hilf - 60
			self["list"].setEpoch(hilf)
			config.GraphEPG.prev_time_period.value = hilf
			self.moveTimeLines()

	def key2(self):
		self["list"].instance.moveSelection(self["list"].instance.pageUp)

	def key3(self):
		hilf = config.GraphEPG.prev_time_period.value	
		if hilf < 300:
			hilf = hilf + 60
			self["list"].setEpoch(hilf)
			config.GraphEPG.prev_time_period.value = hilf
			self.moveTimeLines()

	def key4(self):
		self.updEvent(-2)

	def key5(self):
		self["list"].instance.moveSelectionTo(0)
		now = time()
		tmp = now % 900
		cooltime = now - tmp
		self["list"].resetOffset()
		self["list"].fillGraphEPG(self.services, cooltime)
		self.moveTimeLines(True)

	def key6(self):
		self.updEvent(+2)

	def key7(self):
		EPGheight = getDesktop(0).size().height()
		GraphEPGman = (config.GraphEPG.item_hight.value / config.GraphEPG.items_per_page.value)
		if self["list"].coolheight == config.GraphEPG.item_hight16.value:
			self["list"].coolheight = GraphEPGman
		else:
			self["list"].coolheight = config.GraphEPG.item_hight16.value
		self["list"].l.setItemHeight(int(self["list"].coolheight))
		self["list"].fillGraphEPG(None)
		self.moveTimeLines()

	def key8(self):
		self["list"].instance.moveSelection(self["list"].instance.pageDown)

	def key9(self):
		cooltime = localtime(self["list"].getTimeBase())
		hilf = (cooltime[0], cooltime[1], cooltime[2], config.GraphEPG.Primetime1.value, config.GraphEPG.Primetime2.value,0, cooltime[6], cooltime[7], cooltime[8])
		cooltime = mktime(hilf)
		self["list"].resetOffset()
		self["list"].fillGraphEPG(self.services, cooltime)
		self.moveTimeLines(True)		

	def key0(self):
		self["list"].setEpoch2(180)
		config.GraphEPG.prev_time_period.value = 180
		self["list"].instance.moveSelectionTo(0)	
		now = time()
		tmp = now % 900
		cooltime = now - tmp
		self["list"].resetOffset()
		self["list"].fillGraphEPG(self.services, cooltime)
		self.moveTimeLines(True)

	def OK(self):
		if config.GraphEPG.OK.value == "Zap":
			self.ZapTo()
		if config.GraphEPG.OK.value == "Zap + Exit":
			self.zap()

	def OKLong(self):
		if config.GraphEPG.OKLong.value == "Zap":
			self.ZapTo()
		if config.GraphEPG.OKLong.value == "Zap + Exit":
			self.zap()

	def Info(self):
		if config.GraphEPG.Info.value == "Channel Info":
			self.infoKeyPressed()
		if config.GraphEPG.Info.value == "Single EPG":
			self.OpenSingleEPG()

	def InfoLong(self):
		if config.GraphEPG.InfoLong.value == "Channel Info":
			self.infoKeyPressed()
		if config.GraphEPG.InfoLong.value == "Single EPG":
			self.OpenSingleEPG()

	def applyButtonState(self, state):
		if state == 0:
			self["now_button"].hide()
			self["now_button_sel"].hide()
			self["next_button"].hide()
			self["next_button_sel"].hide()
			self["more_button"].hide()
			self["more_button_sel"].hide()
			self["now_text"].hide()
			self["next_text"].hide()
			self["more_text"].hide()
			self["key_red"].setText("")
		else:
			if state == 1:
				self["now_button_sel"].show()
				self["now_button"].hide()
			else:
				self["now_button"].show()
				self["now_button_sel"].hide()

			if state == 2:
				self["next_button_sel"].show()
				self["next_button"].hide()
			else:
				self["next_button"].show()
				self["next_button_sel"].hide()

			if state == 3:
				self["more_button_sel"].show()
				self["more_button"].hide()
			else:
				self["more_button"].show()
				self["more_button_sel"].hide()

	def onSelectionChanged(self):
		cur = self["list"].getCurrent()
		if cur is None:
			if self.key_green_choice != self.EMPTY:
				self["key_green"].setText("")
				self.key_green_choice = self.EMPTY
			if self.key_red_choice != self.EMPTY:
				self["key_red"].setText("")
				self.key_red_choice = self.EMPTY
			return
		event = cur[0]
		self["Event"].newEvent(event)
		if self.type == EPG_TYPE_MULTI or self.type == EPG_TYPE_GRAPH:
			count = self["list"].getCurrentChangeCount()
			if self.type == EPG_TYPE_MULTI:
				if self.ask_time != -1:
					self.applyButtonState(0)
				elif count > 1:
					self.applyButtonState(3)
				elif count > 0:
					self.applyButtonState(2)
				else:
					self.applyButtonState(1)
			days = [ _("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun") ]
			datestr = ""
			if event is not None:
				now = time()
				beg = event.getBeginTime()
				nowTime = localtime(now)
				begTime = localtime(beg)
				if nowTime[2] != begTime[2]:
					if self.type != EPG_TYPE_GRAPH:
						datestr = '%s %d.%d.'%(days[begTime[6]], begTime[2], begTime[1])
					else:
						datestr = '%s'%(days[begTime[6]])

				else:
					if self.type != EPG_TYPE_GRAPH:
						datestr = '%s %d.%d.'%(_("Today"), begTime[2], begTime[1])
					else:
						datestr = '%s'%(_("Today"))

			self["date"].setText(datestr)
			if self.type != EPG_TYPE_GRAPH:
				if cur[1] is None:
					self["Service"].newService(None)
				else:
					self["Service"].newService(cur[1].ref)

		if cur[1] is None or cur[1].getServiceName() == "":
			if self.key_green_choice != self.EMPTY:
				self["key_green"].setText("")
				self.key_green_choice = self.EMPTY
			if self.key_red_choice != self.EMPTY:
				self["key_red"].setText("")
				self.key_red_choice = self.EMPTY
			return

		if event is None:
			if self.key_green_choice != self.EMPTY:
				self["key_green"].setText("")
				self.key_green_choice = self.EMPTY
			return

		serviceref = cur[1]
		eventid = event.getEventId()
		refstr = serviceref.ref.toString()
		isRecordEvent = False
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and timer.service_ref.ref.toString() == refstr:
				isRecordEvent = True
				break
		if isRecordEvent and self.key_green_choice != self.REMOVE_TIMER:
			self["key_green"].setText(_("Remove timer"))
			self.key_green_choice = self.REMOVE_TIMER
		elif not isRecordEvent and self.key_green_choice != self.ADD_TIMER:
			self["key_green"].setText(_("Add Timer"))
			self.key_green_choice = self.ADD_TIMER

	def moveTimeLines(self, force=False):
		self.updateTimelineTimer.start((60-(int(time())%60))*1000)	#keep syncronised
		l = self["list"]
		event_rect = l.getEventRect()
		time_epoch = l.getTimeEpoch()
		time_base = l.getTimeBase()
		if event_rect is None or time_epoch is None or time_base is None:
			return
		time_steps = time_epoch > 180 and 60 or 30
		
		num_lines = time_epoch/time_steps
		incWidth=event_rect.width()/num_lines
		pos=event_rect.left()
		timeline_entries = [ ]
		x = 0
		changecount = 0

		for line in self.time_lines:
			old_pos = line.position
			new_pos = (x == num_lines and event_rect.left()+event_rect.width() or pos, old_pos[1])
			if not x or x >= num_lines:
				line.visible = False
			else:
				if old_pos != new_pos:
					line.setPosition(new_pos[0], new_pos[1])
					changecount += 1
				line.visible = True
			if not x or line.visible:
				timeline_entries.append((time_base + x * time_steps * 60, new_pos[0]))
			x += 1
			pos += incWidth

		if changecount or force:
			self["timeline_text"].setEntries(timeline_entries)

		now=time()
		timeline_now = self["timeline_now"]
		if now >= time_base and now < (time_base + time_epoch * 60):
			xpos = int((((now - time_base) * event_rect.width()) / (time_epoch * 60))-(timeline_now.instance.size().width()/2))
			old_pos = timeline_now.position
			new_pos = (xpos+event_rect.left(), old_pos[1])
			if old_pos != new_pos:
				timeline_now.setPosition(new_pos[0], new_pos[1])
			timeline_now.visible = True
		else:
			timeline_now.visible = False

		l.l.invalidate()

	def isPlayable(self):
		# check if service is playable
		current = ServiceReference(self.servicelist.getCurrentSelection())
		return not (current.ref.flags & (eServiceReference.isMarker|eServiceReference.isDirectory))

	def setServicelistSelection(self, bouquet, service):
		# we need to select the old service with bouquet
		if self.servicelist.getRoot() != bouquet: #already in correct bouquet?
			self.servicelist.clearPath()
			self.servicelist.enterPath(self.servicelist.bouquet_root)
			self.servicelist.enterPath(bouquet)
		self.servicelist.setCurrentSelection(service) #select the service in servicelist

	def zap(self):
		if self.zapFunc :
			self.closeRecursive = True
			ref = self["list"].getCurrent()[1]
			if ref:
				self.zapFunc(ref.ref)
				self.closeScreen()

	def ZapTo(self):
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_MULTI:
			if self.zapFunc:
				currch = self.session.nav.getCurrentlyPlayingServiceReference()
				currch = currch.toString()
				ref = self["list"].getCurrent()[1]
				if self.type == EPG_TYPE_GRAPH:
					self["list"].curr_refcool = ref.ref
					self["list"].fillGraphEPG(None)
				switchto = ServiceReference(ref.ref)
				switchto = str(switchto)
				if not switchto == currch:
					if ref and switchto.find('alternatives') != -1:
						self.zapFunc(ref.ref)
						self.close(True)
					else:
						self.zapFunc(ref.ref)
				else:
					self.close(True)
		else:
			try:
				currch = self.session.nav.getCurrentlyPlayingServiceReference()
				currch = currch.toString()
				switchto = ServiceReference(self.servicelist.getCurrentSelection())
				switchto = str(switchto)
				if not switchto == currch:
					self.servicelist_orig_zap()
				else:
					self.close()
			except:
				self.close()

	def keyNumberGlobal(self, number):
		from Screens.InfoBarGenerics import NumberZap
		self.session.openWithCallback(self.numberEntered, NumberZap, number)

	def numberEntered(self, retval):
		if retval > 0:
			self.zapToNumber(retval)

	def searchNumberHelper(self, serviceHandler, num, bouquet):
		servicelist = serviceHandler.list(bouquet)
		if not servicelist is None:
			while num:
				serviceIterator = servicelist.getNext()
				if not serviceIterator.valid(): #check end of list
					break
				playable = not (serviceIterator.flags & (eServiceReference.isMarker|eServiceReference.isDirectory))
				if playable:
					num -= 1;
			if not num: #found service with searched number ?
				return serviceIterator, 0
		return None, num

	def zapToNumber(self, number):
		bouquet = self.servicelist.bouquet_root
		service = None
		serviceHandler = eServiceCenter.getInstance()
		bouquetlist = serviceHandler.list(bouquet)
		if not bouquetlist is None:
			while number:
				bouquet = bouquetlist.getNext()
				if not bouquet.valid(): #check end of list
					break
				if bouquet.flags & eServiceReference.isDirectory:
					service, number = self.searchNumberHelper(serviceHandler, number, bouquet)
		if not service is None:
			self.setServicelistSelection(bouquet, service)
		self.onCreate()

	# ChannelSelection Support
	def prepareChannelSelectionDisplay(self):
		# save current ref and bouquet ( for cancel )
		self.curSelectedRef = eServiceReference(self.servicelist.getCurrentSelection().toString())
		self.curSelectedBouquet = self.servicelist.getRoot()

	def cancelChannelSelection(self):
		# select service and bouquet selected before started ChannelSelection
		if self.servicelist.revertMode is None:
			ref = self.curSelectedRef
			bouquet = self.curSelectedBouquet
			if ref.valid() and bouquet.valid():
				# select bouquet and ref in servicelist
				self.setServicelistSelection(bouquet, ref)
		# close ChannelSelection
		self.servicelist.revertMode = None
		self.servicelist.asciiOff()
		self.servicelist.close(None)

		# clean up
		self.curSelectedRef = None
		self.curSelectedBouquet = None
		# display VZ data
		self.servicelist_overwrite_zap()

	#def switchChannelDown(self):
		#self.prepareChannelSelectionDisplay()
		#self.servicelist.moveDown()
		## show ChannelSelection
		#self.session.execDialog(self.servicelist)

	#def switchChannelUp(self):
		#self.prepareChannelSelectionDisplay()
		#self.servicelist.moveUp()
		## show ChannelSelection
		#self.session.execDialog(self.servicelist)

	def showFavourites(self):
		self.prepareChannelSelectionDisplay()
		self.servicelist.showFavourites()
		# show ChannelSelection
		self.session.execDialog(self.servicelist)

	def openServiceList(self):
		self.prepareChannelSelectionDisplay()
		# show ChannelSelection
		self.session.execDialog(self.servicelist)

	def servicelist_overwrite_zap(self):
		# we do not really want to zap to the service, just display data for VZ
		self.currentPiP = ""
		if self.isPlayable():
			self.onCreate()

	def __onClose(self):
		# reverse changes of ChannelSelection 
		self.servicelist.zap = self.servicelist_orig_zap
		self.servicelist["actions"] = ActionMap(["OkCancelActions", "TvRadioActions"],
			{
				"cancel": self.servicelist.cancel,
				"ok": self.servicelist.channelSelected,
				"keyRadio": self.servicelist.setModeRadio,
				"keyTV": self.servicelist.setModeTv,
			})

class RecordSetup(TimerEntry):
	def __init__(self, session, timer, zap):
		Screen.__init__(self, session)
		self.timer = timer
		self.timer.justplay = zap
		self.entryDate = None
		self.entryService = None
		self.keyGo()

	def keyGo(self, result = None):
		if self.timer.justplay:
			self.timer.end = self.timer.begin
		self.timer.resetRepeated()
		self.saveTimer()
		self.close((True, self.timer))

	def saveTimer(self):
		self.session.nav.RecordTimer.saveTimer()
				
class TimelineText(HTMLComponent, GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setSelectionClip(eRect(0,0,0,0))
		self.l.setItemHeight(25);
		self.l.setFont(0, gFont("Regular", config.GraphEPG.Timeline.value))

	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)

	def setEntries(self, entries):
		res = [ None ] # no private data needed
		hilfheute = localtime()
		hilfentry = localtime(entries[0][0])
#		if hilfheute[0] == hilfentry[0] and hilfheute[1] == hilfentry[1] and hilfheute[2] == hilfentry[2]:
#			hilf3 = ""
#		else:
#			hilf = hilfentry[6]
#			hilf3 = (_("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun"))[hilf]
#		
#		res.append((eListboxPythonMultiContent.TYPE_TEXT, 30, 0, 60, 25, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, hilf3))

		for x in entries:
			tm = x[0]
			xpos = x[1]
			str = strftime("%H:%M", localtime(tm))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, xpos-30, 0, 60, 25, 0, RT_HALIGN_CENTER|RT_VALIGN_CENTER, str))
		self.l.setList([res])

class SingleEPG(EPGSelection):
	def __init__(self, session, service, zapFunc=None, bouquetChangeCB=None, serviceChangeCB=None):
		EPGSelection.__init__(self, session, service, zapFunc, bouquetChangeCB, serviceChangeCB)
		self.skinName = "EPGSelection"

class EPGSelectionSetup(Screen, ConfigListScreen):
	skin = """
		<screen name="EPGSelectionSetup" position="center,center" size="680,480" title="EPG Setup">
			<ePixmap pixmap="skin_default/buttons/red.png" position="20,5" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="185,5" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="350,5" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="515,5" size="140,40" alphatest="on" />
			<widget name="key_red" position="20,5" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="key_green" position="185,5" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<eLabel text="press ( left OK right ) to change your Buttons !!!" position="15,455" size="650,60" font="Regular;20" foregroundColor="#9f1313" backgroundColor="#000000" shadowColor="#000000" halign="center" transparent="1" />
			<widget name="config" position="20,60" size="640,370" />
		</screen>"""

	def __init__(self, session, type):
		Screen.__init__(self, session)
		self.skinName = "EPGSelectionSetup"
		self.type=type
		self.skinName = "EPGSelectionSetup"
		Screen.setTitle(self, _("EPG Setup"))
		self.onChangedEntry = [ ]
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		self.createSetup()
		
		if self.type == 5:
			self["actions"] = ActionMap(["SetupActions", 'ColorActions', "HelpActions"],
			{
				"ok": self.keySave,
				"save": self.keySave,
				"cancel": self.keyCancel,
				"red": self.keyCancel,
				"green": self.keySave,
				"displayHelp": self.myhelp,
			}, -1)
		else:
			self["actions"] = ActionMap(["SetupActions", 'ColorActions'],
			{
				"ok": self.keySave,
				"save": self.keySave,
				"cancel": self.keyCancel,
				"red": self.keyCancel,
				"green": self.keySave,
			}, -1)

		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))

	def myhelp(self):
		self.session.open(GraphEPGHelp, "/usr/share/enigma2/skin_default/GraphEPG/help.jpg")

	def createSetup(self):
		self.editListEntry = None
		self.list = [ ]
		if self.type == 5:
			self.list.append(getConfigListEntry(_("Show bouquet on launch"), config.GraphEPG.ShowBouquet))
			self.list.append(getConfigListEntry(_("Picture In Graphics (close EPG)"), config.GraphEPG.PIG))
			self.list.append(getConfigListEntry(_("Enable Picon"), config.GraphEPG.UsePicon))
			self.list.append(getConfigListEntry(_("Info Button"), config.GraphEPG.Info))
			self.list.append(getConfigListEntry(_("Long Info Button"), config.GraphEPG.InfoLong))
			self.list.append(getConfigListEntry(_("OK Button"), config.GraphEPG.OK))
			self.list.append(getConfigListEntry(_("LongOK Button"), config.GraphEPG.OKLong))
			self.list.append(getConfigListEntry(_("Primetime hour"), config.GraphEPG.Primetime1))
			self.list.append(getConfigListEntry(_("Primetime minute"), config.GraphEPG.Primetime2))
			self.list.append(getConfigListEntry(_("Channel 1 at Start"), config.GraphEPG.channel1))
			self.list.append(getConfigListEntry(_("Start-Items 7-8 , 14-16"), config.GraphEPG.coolswitch))
			self.list.append(getConfigListEntry(_("Items per Page"), config.GraphEPG.items_per_page))
			self.list.append(getConfigListEntry(_("Event Fontsize"), config.GraphEPG.Fontsize))
			self.list.append(getConfigListEntry(_("Left Fontsize"), config.GraphEPG.Left_Fontsize))
			self.list.append(getConfigListEntry(_("Timeline Fontsize (restart plugin)"), config.GraphEPG.Timeline))
			self.list.append(getConfigListEntry(_("Left width Picon"), config.GraphEPG.left8))
			self.list.append(getConfigListEntry(_("Left width Text"), config.GraphEPG.left16))
			self.list.append(getConfigListEntry(_("Time Scale"), config.GraphEPG.prev_time_period))
			self.list.append(getConfigListEntry(_("Skip Empty Services (restart plugin)"), config.GraphEPG.overjump))
		else:
			self.list.append(getConfigListEntry(_("Sort List by"), config.misc.EPGSort))
		self["config"].list = self.list
		self["config"].l.setList(self.list)
	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def saveAll(self):
		for x in self["config"].list:
			x[1].save()

	# keySave and keyCancel are just provided in case you need them.
	# you have to call them by yourself.
	def keySave(self):
		self.saveAll()
		self.close()
		config.plisettings.save()
		config.save()
	
	def cancelConfirm(self, result):
		if not result:
			return

		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close()

class GraphEPGHelp(Screen):
	if (getDesktop(0).size().width()) == 720:
		skin="""
			<screen flags="wfNoBorder" position="0,0" size="720,576" title="..Help.." backgroundColor="#ffffffff">
				<widget name="Picture" position="0,0" size="720,576" zPosition="1"/>
			</screen>"""	
	elif (getDesktop(0).size().width()) == 1024:
		skin="""
			<screen flags="wfNoBorder" position="0,0" size="1024,576" title="..Help.." backgroundColor="#ffffffff">
				<widget name="Picture" position="0,0" size="1024,576" zPosition="1"/>
			</screen>"""
	else:
		skin="""
			<screen flags="wfNoBorder" position="0,0" size="1280,720" title="..Help.." backgroundColor="#ffffffff">
				<widget name="Picture" position="0,0" size="1280,720" zPosition="1"/>
			</screen>"""

	def __init__(self, session, whatPic = None):
		self.skin = GraphEPGHelp.skin
		Screen.__init__(self, session)
		self.whatPic = whatPic
		self.EXscale = (AVSwitch().getFramebufferScale())
		self.EXpicload = ePicLoad()
		self["Picture"] = Pixmap()
		self["actions"] = ActionMap(["WizardActions", "ColorActions"],
		{
			"ok": self.close,
			"back": self.close,
			"red": self.close,
			"green": self.close
		}, -1)

		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))
		self.EXpicload.PictureData.get().append(self.DecodeAction)
		self.onLayoutFinish.append(self.Help_Picture)

	def Help_Picture(self):
		if self.whatPic is not None:
			self.EXpicload.setPara([self["Picture"].instance.size().width(), self["Picture"].instance.size().height(), self.EXscale[0], self.EXscale[1], 0, 1, "#121214"])
			self.EXpicload.startDecode(self.whatPic)

	def DecodeAction(self, pictureInfo=" "):
		if self.whatPic is not None:
			ptr = self.EXpicload.getData()
			self["Picture"].instance.setPixmap(ptr)
