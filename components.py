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
		pass
	
	def createGUIScreen(self, parent):
		for (name, val) in self.items():
			if isinstance(val, GUIComponent):
				val.GUIcreate(parent, None)
	
	def deleteGUIScreen(self):
		for (name, val) in self.items():
			if isinstance(val, GUIComponent):
				val.GUIdelete()
			try:
				val.fix()
			except:
				pass
			
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
#			assert sys.getrefcount(w) == 2, "too many refs hold to " + str(w)
	
	def close(self):
		self.deleteGUIScreen()

class GUIComponent:
	""" GUI component """

	def __init__(self):
		pass
		
	def execBegin(self):
		pass
	
	def execEnd(self):
		pass

class VariableText:
	"""VariableText can be used for components which have a variable text, based on any widget with setText call"""
	
	def __init__(self):
		self.message = ""
		self.instance = None
	
	def setText(self, text):
		self.message = text
		if self.instance:
			self.instance.setText(self.message)

	def getText(self):
		return self.message
	
	def GUIcreate(self, parent, skindata):
		self.instance = self.createWidget(parent, skindata)
		self.instance.setText(self.message)
	
	def GUIdelete(self):
		self.removeWidget(self.instance)
		del self.instance
	
	def removeWidget(self, instance):
		pass

class VariableValue:
	"""VariableValue can be used for components which have a variable value (like eSlider), based on any widget with setValue call"""
	
	def __init__(self):
		self.value = 0
		self.instance = None
	
	def setValue(self, value):
		self.value = value
		if self.instance:
			self.instance.setValue(self.value)

	def getValue(self):
		return self.value
		
	def GUIcreate(self, parent, skindata):
		self.instance = self.createWidget(parent, skindata)
		self.instance.setValue(self.value)
	
	def GUIdelete(self):
		self.removeWidget(self.instance)
		del self.instance
	
	def removeWidget(self, instance):
		pass

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
	def createWidget(self, parent, skindata):
		return eLabel(parent)

	def removeWidget(self, w):
		del self.clockTimer

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
#		self.instance.hide()
		pass
	
	def enable(self):
#		self.instance.show()
		pass

# html:
	def produceHTML(self):
		return "<input type=\"submit\" text=\"" + self.getText() + "\">\n"

# GUI:
	def createWidget(self, parent, skindata):
		g = eButton(parent)
		g.selected.get().append(self.push)
		return g

	def removeWidget(self, w):
		w.selected.get().remove(self.push)

class Label(HTMLComponent, GUIComponent, VariableText):
	def __init__(self, text=""):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.setText(text)
	
# html:	
	def produceHTML(self):
		return self.getText()

# GUI:
	def createWidget(self, parent, skindata):
		return eLabel(parent)
	
class Header(HTMLComponent, GUIComponent, VariableText):

	def __init__(self, message):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.setText(message)
	
	def produceHTML(self):
		return "<h2>" + self.getText() + "</h2>\n"

	def createWidget(self, parent, skindata):
		g = eLabel(parent)
		return g

class VolumeBar(HTMLComponent, GUIComponent, VariableValue):
	
	def __init__(self):
		GUIComponent.__init__(self)
		VariableValue.__init__(self)

	def createWidget(self, parent, skindata):
		g = eSlider(parent)
		g.setRange(0, 100)
		return g
		
# a general purpose progress bar
class ProgressBar(HTMLComponent, GUIComponent, VariableValue):
	def __init__(self):
		GUIComponent.__init__(self)
		VariableValue.__init__(self)

	def createWidget(self, parent, skindata):
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
	
	def GUIcreate(self, parent, skindata):
		self.instance = eListbox(parent)
		self.instance.setContent(self.l)
	
	def GUIdelete(self):
		self.instance.setContent(None)

class ServiceList(HTMLComponent, GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxServiceContent()
	
	def getCurrent(self):
		r = eServiceReference()
		self.l.getCurrent(r)
		return r

	def GUIcreate(self, parent, skindata):
		self.instance = eListbox(parent)
		self.instance.setContent(self.l)
	
	def GUIdelete(self):
		del self.instance

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
	
class ActionMap:
	def __init__(self, context, actions = { }, prio=0):
		self.actions = actions
		self.context = context
		self.prio = prio
		self.p = eActionMapPtr()
		eActionMap.getInstance(self.p)

	def execBegin(self):
		self.p.bindAction(self.context, self.prio, self.action)
	
	def execEnd(self):
		self.p.unbindAction(self.context, self.action)
	
	def action(self, context, action):
		try:
			self.actions[action]()
		except KeyError:
			print "unknown action %s/%s! typo in keymap?" % (context, action)

class PerServiceDisplay(GUIComponent, VariableText):
	"""Mixin for building components which display something which changes on navigation events, for example "service name" """
	
	def __init__(self, navcore, eventmap):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.eventmap = eventmap
		navcore.m_event.get().append(self.event)
		self.navcore = navcore

		# start with stopped state, so simulate that
		self.event(pNavigation.evStopService)

	def event(self, ev):
		# loop up if we need to handle this event
		if self.eventmap.has_key(ev):
			# call handler
			self.eventmap[ev]()
	
	def createWidget(self, parent, skindata):
		# by default, we use a label to display our data.
		g = eLabel(parent)
		return g

class EventInfo(PerServiceDisplay):
	Now = 0
	Next = 1
	def __init__(self, navcore, now_or_next):
		# listen to evUpdatedEventInfo and evStopService
		# note that evStopService will be called once to establish a known state
		PerServiceDisplay.__init__(self, navcore, 
			{ 
				pNavigation.evUpdatedEventInfo: self.ourEvent, 
				pNavigation.evStopService: self.stopEvent 
			})
		self.now_or_next = now_or_next

	def ourEvent(self):
		info = iServiceInformationPtr()
		service = iPlayableServicePtr()
		
		if not self.navcore.getCurrentService(service):
			if not service.info(info):
				print "got info !"
				ev = eServiceEventPtr()
				info.getEvent(ev, self.now_or_next)
				self.setText(ev.m_event_name)
		print "new event info in EventInfo! yeah!"

	def stopEvent(self):
			self.setText("waiting for event data...");

class ServiceName(PerServiceDisplay):
	def __init__(self, navcore):
		PerServiceDisplay.__init__(self, navcore,
			{
				pNavigation.evNewService: self.newService,
				pNavigation.evStopService: self.stopEvent
			})

	def newService(self):
		info = iServiceInformationPtr()
		service = iPlayableServicePtr()
		
		if not self.navcore.getCurrentService(service):
			if not service.info(info):
				self.setText("no name known, but it should be here :)")
	
	def stopEvent(self):
			self.setText("");
