from enigma import *
import time
import sys

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
	def __init__(self):
		self.data = { }
	
	def createGUIScreen(self, parent):
		for (name, val) in self.items():
			self.data[name] = { }
			if isinstance(val, GUIComponent):
				val.GUIcreate(self.data[name], parent, None)
	
	def deleteGUIScreen(self):
		for (name, val) in self.items():
			if isinstance(val, GUIComponent):
				w = self.data[name]["instance"]
				val.GUIdelete(self.data[name])
			try:
				val.fix()
			except:
				pass
			del self.data[name]
			
			# note: you'll probably run into this assert. if this happens, don't panic!
			# yes, it's evil. I told you that programming in python is just fun, and 
			# suddently, you have to care about things you don't even know.
			#
			# but calm down, the solution is easy, at least on paper:
			#
			# Each Component, which is a GUIComponent, owns references to each
			# instantiated eWidget (namely in screen.data[name]["instance"], in case
			# you care.)
			# on deleteGUIscreen, all eWidget *must* (!) be deleted (otherwise,
			# well, problems appear. I don't want to go into details too much,
			# but this would be a memory leak anyway.)
			# The assert beyond checks for that. It asserts that the corresponding
			# eWidget is about to be removed (i.e., that the refcount becomes 0 after
			# running deleteGUIscreen).
			# (You might wonder why the refcount is checked for 2 and not for 1 or 0 -
			# one reference is still hold by the local variable 'w', another one is
			# hold be the function argument to sys.getrefcount itself. So only if it's
			# 2 at this point, the object will be destroyed after leaving deleteGUIscreen.)
			#
			# Now, how to fix this problem? You're holding a reference somewhere. (References
			# can only be hold from Python, as eWidget itself isn't related to the c++
			# way of having refcounted objects. So it must be in python.)
			#
			# It could be possible that you're calling deleteGUIscreen trough a call of
			# a PSignal. For example, you could try to call screen.doClose() in response
			# to a Button::click. This will fail. (It wouldn't work anyway, as you would
			# remove a dialog while running it. It never worked - enigma1 just set a 
			# per-mainloop variable on eWidget::close() to leave the exec()...)
			# That's why Session supports delayed closes. Just call Session.close() and
			# it will work.
			#
			# Another reason is that you just stored the data["instance"] somewhere. or
			# added it into a notifier list and didn't removed it.
			#
			# If you can't help yourself, just ask me. I'll be glad to help you out.
			# Sorry for not keeping this code foolproof. I really wanted to archive
			# that, but here I failed miserably. All I could do was to add this assert.
			assert sys.getrefcount(w) == 2, "too many refs hold to " + str(w)
	
	def close(self):
		self.deleteGUIScreen()
		del self.data

# note: components can be used in multiple screens, so we have kind of
# two contexts: first the per-component one (self), then the per-screen (i.e.:
# per eWidget one), called "priv". In "priv", for example, the instance
# of the eWidget is stored.


# GUI components have a "notifier list" of associated eWidgets to one component
# (as said - one component instance can be used at multiple screens)
class GUIComponent:
	""" GUI component """

	def __init__(self):
		self.notifier = [ ]
	
	def GUIcreate(self, priv, parent, skindata):
		i = self.GUIcreateInstance(self, parent, skindata)
		priv["instance"] = i
		self.notifier.append(i)
		try:
			self.notifierAdded(i)
		except:
			pass
	
	# GUIdelete must delete *all* references to the current component!
	def GUIdelete(self, priv):
		g = priv["instance"]
		self.notifier.remove(g)
		self.GUIdeleteInstance(g)
		del priv["instance"]

	def GUIdeleteInstance(self, priv):
		pass

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
	def __init__(self, text="", onClick = [ ]):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.setText(text)
		self.onClick = onClick
	
	def push(self):
		for x in self.onClick:
			x()
		return 0
	
	def disable(self):
		pass
	
	def enable(self):
		pass

# html:
	def produceHTML(self):
		return "<input type=\"submit\" text=\"" + self.getText() + "\">\n"

# GUI:
	def GUIcreateInstance(self, priv, parent, skindata):
		g = eButton(parent)
		g.selected.get().append(self.push)
		return g
	
	def GUIdeleteInstance(self, g):
		g.selected.get().remove(self.push)

class Label(HTMLComponent, GUIComponent, VariableText):
	def __init__(self, text=""):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.setText(text)
	
# html:	
	def produceHTML(self):
		return self.getText()

# GUI:
	def GUIcreateInstance(self, priv, parent, skindata):
		g = eLabel(parent)
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

# a general purpose progress bar
class ProgressBar(HTMLComponent, GUIComponent, VariableValue):
	def __init__(self):
		GUIComponent.__init__(self)
		VariableValue.__init__(self)

	def GUIcreateInstance(self, priv, parent, skindata):
		g = eSlider(parent)
		g.setRange(0, 100)
		return g
	
class MenuList(HTMLComponent, GUIComponent):
	def __init__(self, list):
		GUIComponent.__init__(self)
		self.l = eListboxPythonStringContent()
		self.l.setList(list)
	
	def getCurrent(self):
		return self.l.getCurrentSelection()
	
	def GUIcreateInstance(self, priv, parent, skindata):
		g = eListbox(parent)
		g.setContent(self.l)
		return g
	
	def GUIdeleteInstance(self, g):
		g.setContent(None)

class ServiceList(HTMLComponent, GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxServiceContent()

	def GUIcreateInstance(self, priv, parent, skindata):
		g = eListbox(parent)
		g.setContent(self.l)
		return g
	
	def GUIdeleteInstance(self, g):
		g.setContent(None)

	def setRoot(self, root):
		self.l.setRoot(root)

class ServiceScan:
	
	Idle = 1
	Running = 2
	Done = 3
	Error = 4
		
	def scanStatusChanged(self):
		if self.state == self.Running:
			self.progressbar.setValue(self.scan.getProgress())
			if self.scan.isDone():
				self.state = self.Done
			else:
				self.text.setText("scan in progress - %d %% done!\n%d services found!" % (self.scan.getProgress(), self.scan.getNumServices()))
		
		if self.state == self.Done:
			self.text.setText("scan done!")
		
		if self.state == self.Error:
			self.text.setText("ERROR - failed to scan!")
	
	def __init__(self, progressbar, text):
		self.progressbar = progressbar
		self.text = text
		self.scan = eComponentScan()
		if self.scan.start():
			self.state = self.Error
		else:
			self.state = self.Running
		self.scan.statusChanged.get().append(self.scanStatusChanged)
		self.scanStatusChanged()

	def isDone(self):
		return self.state == self.Done

	def fix(self):
		self.scan.statusChanged.get().remove(self.scanStatusChanged)
	