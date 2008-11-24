from Screens.Satconfig import NimSelection
from Screens.Screen import Screen

from Plugins.Plugin import PluginDescriptor

from Components.ActionMap import NumberActionMap
from Components.NimManager import nimmanager
from Components.ResourceManager import resourcemanager
from Components.Sources.FrontendStatus import FrontendStatus
from Components.TuneTest import TuneTest
from Components.Sources.Progress import Progress
from Components.Sources.StaticText import StaticText

class DiseqcTester(Screen, TuneTest):
	skin = """
		<screen position="90,100" size="520,400" title="DiSEqC Tester" >
			<ePixmap pixmap="skin_default/icons/dish_scan.png" position="5,25" zPosition="0" size="119,110" transparent="1" alphatest="on" />
		<widget source="Frontend" render="Label" position="190,10" zPosition="2" size="260,20" font="Regular;19" halign="center" valign="center" transparent="1">
			<convert type="FrontendInfo">SNRdB</convert>
		</widget>
		<eLabel name="snr" text="SNR:" position="120,35" size="60,22" font="Regular;21" halign="right" transparent="1" />
		<widget source="Frontend" render="Progress" position="190,35" size="260,20" pixmap="skin_default/bar_snr.png" borderWidth="2" borderColor="#cccccc">
			<convert type="FrontendInfo">SNR</convert>
		</widget>
		<widget source="Frontend" render="Label" position="460,35" size="60,22" font="Regular;21">
			<convert type="FrontendInfo">SNR</convert>
		</widget>
		<eLabel name="agc" text="AGC:" position="120,60" size="60,22" font="Regular;21" halign="right" transparent="1" />
		<widget source="Frontend" render="Progress" position="190,60" size="260,20" pixmap="skin_default/bar_snr.png" borderWidth="2" borderColor="#cccccc">
			<convert type="FrontendInfo">AGC</convert>
		</widget>
		<widget source="Frontend" render="Label" position="460,60" size="60,22" font="Regular;21">
			<convert type="FrontendInfo">AGC</convert>
		</widget>
		<eLabel name="ber" text="BER:" position="120,85" size="60,22" font="Regular;21" halign="right" transparent="1" />
		<widget source="Frontend" render="Progress" position="190,85" size="260,20" pixmap="skin_default/bar_ber.png" borderWidth="2" borderColor="#cccccc">
			<convert type="FrontendInfo">BER</convert>
		</widget>
		<widget source="Frontend" render="Label" position="460,85" size="60,22" font="Regular;21">
			<convert type="FrontendInfo">BER</convert>
		</widget>
		<eLabel name="lock" text="Lock:" position="120,115" size="60,22" font="Regular;21" halign="right" />
		<widget source="Frontend" render="Pixmap" pixmap="skin_default/icons/lock_on.png" position="190,110" zPosition="1" size="38,31" alphatest="on">
			<convert type="FrontendInfo">LOCK</convert>
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="Frontend" render="Pixmap" pixmap="skin_default/icons/lock_off.png" position="190,110" zPosition="1" size="38,31" alphatest="on">
			<convert type="FrontendInfo">LOCK</convert>
			<convert type="ConditionalShowHide">Invert</convert>
		</widget>
		<eLabel name="overall_progress" text="Overall progress:" position="20,162" size="480,22" font="Regular;21" halign="center" transparent="1" />
		<widget source="overall_progress" render="Progress" position="20,192" size="480,20" borderWidth="2" backgroundColor="#254f7497" />
		<eLabel name="overall_progress" text="Progress:" position="20,222" size="480,22" font="Regular;21" halign="center" transparent="1" />
		<widget source="sub_progress" render="Progress" position="20,252" size="480,20" borderWidth="2" backgroundColor="#254f7497" />
		
		<eLabel name="" text="Failed:" position="20,282" size="140,22" font="Regular;21" halign="left" transparent="1" />
		<widget source="failed_counter" render="Label" position="160,282" size="480,20" font="Regular;21" />
		
		<eLabel name="" text="Succeeded:" position="20,312" size="140,22" font="Regular;21" halign="left" transparent="1" />
		<widget source="succeeded_counter" render="Label" position="160,312" size="480,20" font="Regular;21" />
		</screen>"""
		
	TEST_TYPE_QUICK = 0
	TEST_TYPE_RANDOM = 1
	TEST_TYPE_COMPLETE = 2
	def __init__(self, session, feid, test_type = TEST_TYPE_QUICK):
		Screen.__init__(self, session)
		self.feid = feid
		self.test_type = test_type
		
		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"ok": self.keyGo,
			"cancel": self.keyCancel,
		}, -2)
		
		TuneTest.__init__(self, feid, stopOnSuccess = True)
		self["Frontend"] = FrontendStatus(frontend_source = lambda : self.frontend, update_interval = 100)
		self["overall_progress"] = Progress()
		self["sub_progress"] = Progress()
		self["failed_counter"] = StaticText("10")
		self["succeeded_counter"] = StaticText("10")
				
		self.indexlist = {}
		self.readTransponderList()

	def readTransponderList(self):
		for sat in nimmanager.getSatListForNim(self.feid):
			for transponder in nimmanager.getTransponders(sat[0]):
				#print transponder
				mytransponder = (transponder[1] / 1000, transponder[2] / 1000, transponder[3], transponder[4], transponder[5], sat[0], None, None, transponder[10], transponder[11])
				self.analyseTransponder(mytransponder)

	def getIndexForTransponder(self, transponder):
		if transponder[0] < 11700:
			band = 1 # low
		else:
			band = 0 # high
			
		polarisation = transponder[2]
		
		sat = transponder[5]
		
		index = (band, polarisation, sat)
		return index

	# sort the transponder into self.transponderlist
	def analyseTransponder(self, transponder):
		index = self.getIndexForTransponder(transponder)
		if index not in self.indexlist:
			self.indexlist[index] = []
		self.indexlist[index].append(transponder)
		#print "self.indexlist:", self.indexlist
	
	# returns a string for the user representing a human readable output for index 
	def getTextualIndexRepresentation(self, index):
		print "getTextualIndexRepresentation:", index
		text = ""
		
		# TODO better sat representation
		text += "%s, " % index[2] 
		
		if index[0] == 1:
			text += "Low Band, "
		else:
			text += "High Band, "
			
		if index[1] == 0:
			text += "H"
		else:
			text += "V"
		return text
	
	def fillTransponderList(self):
		self.clearTransponder()
		print "----------- fillTransponderList"
		print "index:", self.currentlyTestedIndex
		keys = self.indexlist.keys()
		if self.getContinueScanning():
			print "index:", self.getTextualIndexRepresentation(self.currentlyTestedIndex)
			for transponder in self.indexlist[self.currentlyTestedIndex]:
				self.addTransponder(transponder)
			print "transponderList:", self.transponderlist
			return True
		else:
			return False
		
	def progressCallback(self, progress):
		if progress[0] != self["sub_progress"].getRange():
			self["sub_progress"].setRange(progress[0])
		self["sub_progress"].setValue(progress[1])

	# logic for scanning order of transponders
	# on go getFirstIndex is called
	def getFirstIndex(self):
		# TODO use other function to scan more randomly
		if self.test_type == self.TEST_TYPE_QUICK:
			self.myindex = 0
			keys = self.indexlist.keys()
			self["overall_progress"].setRange(len(keys))
			self["overall_progress"].setValue(self.myindex)
			return keys[0]
		
	# after each index is finished, getNextIndex is called to get the next index to scan 
	def getNextIndex(self):
		# TODO use other function to scan more randomly
		if self.test_type == self.TEST_TYPE_QUICK:
			self.myindex += 1
			keys = self.indexlist.keys()
			
			self["overall_progress"].setValue(self.myindex)
			if self.myindex < len(keys):
				return keys[self.myindex]
			else:
				return None
	
	# after each index is finished and the next index is returned by getNextIndex
	# the algorithm checks, if we should continue scanning
	def getContinueScanning(self):
		if self.test_type == self.TEST_TYPE_QUICK:
			return (self.myindex < len(self.indexlist.keys()))
	
	def finishedChecking(self):
		print "finishedChecking"
		TuneTest.finishedChecking(self)
		self.currentlyTestedIndex = self.getNextIndex()
		if self.fillTransponderList():
			self.run(checkPIDs = True)

	def keyGo(self):
		self.currentlyTestedIndex = self.getFirstIndex()
		if self.fillTransponderList():
			self.run(True)

	def keyCancel(self):
		self.close()

class DiseqcTesterNimSelection(NimSelection):
	skin = """
		<screen position="160,123" size="400,330" title="Choose Tuner">
		<widget source="nimlist" render="Listbox" position="0,0" size="380,300" scrollbarMode="showOnDemand">
			<convert type="TemplatedMultiContent">
				{"template": [
						MultiContentEntryText(pos = (10, 5), size = (360, 30), flags = RT_HALIGN_LEFT, text = 1), # index 1 is the nim name,
						MultiContentEntryText(pos = (50, 30), size = (320, 30), font = 1, flags = RT_HALIGN_LEFT, text = 2), # index 2 is a description of the nim settings,
					],
				 "fonts": [gFont("Regular", 20), gFont("Regular", 15)],
				 "itemHeight": 70
				}
			</convert>
		</widget>
	</screen>"""
		
	def __init__(self, session, args = None):
		NimSelection.__init__(self, session)

	def setResultClass(self):
		self.resultclass = DiseqcTester
		
	def showNim(self, nim):
		nimConfig = nimmanager.getNimConfig(nim.slot)
		if nim.isCompatible("DVB-S"):
			if nimConfig.configMode.value in ["loopthrough", "equal", "satposdepends", "nothing"]:
				return False
			if nimConfig.configMode.value == "simple":
				if nimConfig.diseqcMode.value == "positioner":
					return False
			return True
		return False

def DiseqcTesterMain(session, **kwargs):
	session.open(DiseqcTesterNimSelection)
	
def autostart(reason, **kwargs):
	resourcemanager.addResource("DiseqcTester", DiseqcTesterMain)

def Plugins(**kwargs):
	return [ PluginDescriptor(name="DiSEqC Tester", description=_("Test DiSEqC settings"), where = PluginDescriptor.WHERE_PLUGINMENU, fnc=DiseqcTesterMain),
			PluginDescriptor(where = PluginDescriptor.WHERE_AUTOSTART, fnc = autostart)]