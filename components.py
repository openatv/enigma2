from enigma import *
import time

# some helper classes first:
class HTMLComponent:
	def produceHTML(self):
		return ""
		
class HTMLSkin:
	order = ()

	def __init__(self, order):
		self.order = order

	def produceHTML(self):
		res = "<html>\n"
		for name in self.order:
			res += self[name].produceHTML()
		res += "</html>\n";
		return res

class GUISkin:
	data = { }
	def createGUIScreen(self, parent):
		for (name, val) in self.items():
			self.data[name] = { }
			val.GUIcreate(self.data[name], parent, None)

class GUIComponent:
	""" GUI component """

	def __init__(self):
		self.notifier = [ ]
	
	def GUIcreate(self, priv, parent, skindata):
		i = self.GUIcreateInstance(self, parent, skindata)
		priv["instance"] = i
		self.notifier.append(i)
		if self.notifierAdded:
			self.notifierAdded(i)

class VariableText:
	"""VariableText can be used for components which have a variable text, based on any widget with setText call"""
	
	def __init__(self):
		self.message = ""
	
	def notifierAdded(self, notifier):
		notifier.setText(self.message)

	def setText(self, text):
		if self.message != text:
			self.message = text
			for x in self.notifier:
				x.setText(self.message)

	def getText(self):
		return self.message

class VariableValue:
	"""VariableValue can be used for components which have a variable value (like eSlider), based on any widget with setValue call"""
	
	def __init__(self):
		self.value = 0
	
	def notifierAdded(self, notifier):
		notifier.setValue(self.value)

	def setValue(self, value):
		if self.value != value:
			self.value = value
			for x in self.notifier:
				x.setValue(self.value)

	def getValue(self):
		return self.value

# now some "real" components:

class Clock(HTMLComponent, GUIComponent, VariableText):
	def __init__(self):
		VariableText.__init__(self)
		GUIComponent.__init__(self)
		self.doClock()
		
		self.clockTimer = eTimer()
		self.clockTimer.timeout.get().append(self.doClock)
		self.clockTimer.start(1000)

# "funktionalitaet"	
	def doClock(self):
		self.setText("clock: " + time.asctime())

# realisierung als GUI
	def GUIcreateInstance(self, priv, parent, skindata):
		g = eLabel(parent)
		return g

# ...und als HTML:
	def produceHTML(self):
		return self.getText()

class Button(HTMLComponent, GUIComponent, VariableText):
	def __init__(self, text=""):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.setText(text)
		self.onClick = [ ]
	
	def clicked(self):
		for x in self.onClick:
			x()
		return 0

	def GUIcreate(self, priv, parent, skindata):
		GUIComponent.GUIcreate(self, priv,parent, skindata)
		priv["instance"].selected.get().append(self.clicked)
	
	def click(self):
		for x in self.onClick:
			x()

# html:	
	def produceHTML(self):
		return "<input type=\"submit\" text=\"" + self.getText() + "\">\n"

# GUI:
	def GUIcreateInstance(self, priv, parent, skindata):
		g = eButton(parent)
#		g.clicked = [ self.click ]
		return g

class Header(HTMLComponent, GUIComponent, VariableText):

	def __init__(self, message):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.setText(message)
	
	def produceHTML(self):
		return "<h2>" + self.getText() + "</h2>\n"

	def GUIcreateInstance(self, priv, parent, skindata):
		g = eLabel(parent)
		g.setText(self.message)
		return g

class VolumeBar(HTMLComponent, GUIComponent, VariableValue):
	
	def __init__(self):
		GUIComponent.__init__(self)
		VariableValue.__init__(self)

	def GUIcreateInstance(self, priv, parent, skindata):
		g = eSlider(parent)
		g.setRange(0, 100)
		return g

