from Screen import Screen
from Components.ActionMap import ActionMap
from Components.config import config				#global config instance
from Components.config import configEntry
from Components.config import configBoolean
from Components.ConfigList import ConfigList
from Components.Label import Label

import xml.dom.minidom
from xml.dom import EMPTY_NAMESPACE
from skin import elementsWithTag

from Tools import XMLTools

setupdom = xml.dom.minidom.parseString(
	"""
	<setupxml>
		<setup key="rc" title="RC Menu">
			<item text="Repeat Rate">config.inputDevices.repeat</item>
			<item text="Delay Rate">config.inputDevices.delay</item>
			<item text="Keymap">config.rc.map</item>
		</setup>
		<setup key="timezone" title="RC Menu">
			<item text="Timezone">config.timezone.val</item>
		</setup>
		<setup key="avsetup" title="A/V Settings">
			<item text="Color Format">config.av.colorformat</item>
			<item text="Aspect Ratio">config.av.aspectratio</item>
			<item text="TV System">config.av.tvsystem</item>
			<item text="WSS">config.av.wss</item>
			<item text="AC3 default">config.av.defaultac3</item>
			<item text="VCR Switch">config.av.vcrswitch</item>
		</setup>
		<setup key="rfmod" title="UHF Modulator">
			<item text="Modulator">config.rfmod.enable</item>
			<item text="Testmode">config.rfmod.test</item>
			<item text="Sound">config.rfmod.sound</item>
			<item text="Soundcarrier">config.rfmod.soundcarrier</item>
			<item text="Channel">config.rfmod.channel</item>
			<item text="Finetune">config.rfmod.finetune</item>
		</setup>
		<setup key="keyboard" title="Keyboard Setup">
			<item text="Keyboard Map">config.keyboard.keymap</item>
		</setup>
		<setup key="osd" title="OSD Settings">
			<item text="Alpha">config.osd.alpha</item>
			<item text="Brightness">config.osd.bright</item>
			<item text="Contrast">config.osd.contrast</item>
			<item text="Language">config.osd.language</item>
		</setup>
		<setup key="lcd" title="LCD Setup">
			<item text="Brightness">config.lcd.bright</item>
			<item text="Standby">config.lcd.standby</item>
			<item text="Invert">config.lcd.invert</item>
		</setup>
		<setup key="parental" title="Parental Control">
			<item text="Parental Lock">config.parental.lock</item>
			<item text="Setup Lock">config.parental.setuplock</item>
		</setup>
		<setup key="expert" title="Expert Setup">
			<item text="Record Splitsize">config.expert.splitsize</item>
			<item text="Show Satposition">config.expert.satpos</item>
			<item text="Fast zapping">config.expert.fastzap</item>
			<item text="Skip confirmations">config.expert.skipconfirm</item>
			<item text="Hide error windows">config.expert.hideerrors</item>
			<item text="Auto show inforbar">config.expert.autoinfo</item>
		</setup>
		<setup key="satconfig" title="Sat/Dish Setup">
			<item text="Tuner-A Control">config.sat.diseqcA</item>
			<item text="Tuner-A Position">config.sat.posA</item>
			<item text="Tuner-A Sat">config.sat.satA</item>
			<item text="Tuner-B Control">config.sat.diseqcB</item>
			<item text="Tuner-A Position">config.sat.posB</item>
			<item text="Tuner-B Sat">config.sat.satB</item>
		</setup>
	</setupxml>
	""")

def getValbyAttr(x, attr):
	for p in range(x.attributes.length):
		a = x.attributes.item(p)
		attrib = str(a.name)
		value = str(a.value)
		if attrib == attr:
			return value
	
	return ""

class Setup(Screen):

	def addItems(self, list, childNode):
		for x in childNode:
			if x.nodeType != xml.dom.minidom.Element.nodeType:
				continue
			elif x.tagName == 'item':
				ItemText = getValbyAttr(x, "text")
				b = eval(XMLTools.mergeText(x.childNodes));
				print "item " + ItemText + " " + b.configPath
				if b == "":
					continue
				#add to configlist
				item = b.controlType(b)
				
				# the first b is the item itself, ignored by the configList.
				# the second one is converted to string.
				list.append( (ItemText, item) )

	def keyOk(self):
		self["config"].handleKey(0)
	def keyLeft(self):
		self["config"].handleKey(1)
	def keyRight(self):
		self["config"].handleKey(2)

	def keySave(self):
		print "save requested"
		for x in self["config"]:
			selection =	self["config"].getCurrent()
			selection.save()

	def __init__(self, session, setup):
		Screen.__init__(self, session)

		print "request setup for " + setup
		
		xmldata = setupdom.childNodes[0]
		
		entries = xmldata.childNodes

		list = []
				
		for x in entries:             #walk through the actual nodelist
			if x.nodeType != xml.dom.minidom.Element.nodeType:
				continue
			elif x.tagName == 'setup':
				ItemText = getValbyAttr(x, "key")
				if ItemText != setup:
					continue
				self.addItems(list, x.childNodes);
		
		#check for list.entries > 0 else self.close
		
		self["config"] = ConfigList(list)

		self["ok"] = Label("OK")
		self["cancel"] = Label("Cancel")

		self["actions"] = ActionMap(["SetupActions"], 
			{
				"cancel": self.close,
				"ok": self.keyOk,
				"left": self.keyLeft,
				"right": self.keyRight,
				"save": self.keySave
			})
