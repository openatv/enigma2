from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import NumberActionMap
from Components.Input import Input
from Components.Pixmap import Pixmap
from Components.FileList import FileList
from Screens.ChoiceBox import ChoiceBox
from Plugins.Plugin import PluginDescriptor

class Test(Screen):
	skin = """
		<screen position="100,100" size="550,400" title="Test" >
			<!--widget name="text" position="0,0" size="550,25" font="Regular;20" /-->
			<widget name="list" position="10,0" size="190,250" scrollbarMode="showOnDemand" />
			<widget name="pixmap" position="200,0" size="190,250" />
		</screen>"""
	def __init__(self, session, args = None):
		self.skin = Test.skin
		Screen.__init__(self, session)

		self["list"] = FileList("/", matchingPattern = "^.*\.(png|avi|mp3|mpeg|ts)")
		self["pixmap"] = Pixmap()
		
		#self["text"] = Input("1234", maxSize=True, type=Input.NUMBER)
				
		self["actions"] = NumberActionMap(["WizardActions", "InputActions"],
		{
			"ok": self.openTest,
			"back": self.close,
#			"left": self.keyLeft,
#			"right": self.keyRight,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal
		}, -1)
		
		#self.onShown.append(self.openTest)

	def openTest(self):
		self.session.openWithCallback(self.mycallback, MessageBox, _("Test-Messagebox?"))

#		self.session.open(InputBox)
	
	def mycallback(self, answer):
		print "answer:", answer
		if answer:
			raise Exception("test-crash")
		self.close()
	
	def keyLeft(self):
		self["text"].left()
	
	def keyRight(self):
		self["text"].right()
	
	def ok(self):
		selection = self["list"].getSelection()
		if selection[1] == True: # isDir
			self["list"].changeDir(selection[0])
		else:
			self["pixmap"].instance.setPixmapFromFile(selection[0])
	
	def keyNumberGlobal(self, number):
		print "pressed", number
		self["text"].number(number)

def main(session, **kwargs):
	session.open(Test)
	#session.openWithCallback(test, MessageBox, _("Test-Messagebox?"), timeout = 10)
	#session.openWithCallback(test, ChoiceBox, title="Delete everything on this Dreambox?", list=[(_("yes"), "yes"), (_("no"), "no"), (_("perhaps"), "perhaps"), (_("ask me tomorrow"), "ask me tomorrow"), (_("leave me alone with this!"), "yes")])
	
def test(returnValue):
	print "You entered", returnValue

def Plugins(**kwargs):
	return PluginDescriptor(name="Test", description="plugin to test some capabilities", where = PluginDescriptor.WHERE_PLUGINMENU, needsRestart = False, fnc=main)
