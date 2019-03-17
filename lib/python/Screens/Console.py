from enigma import eConsoleAppContainer
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText

class Console(Screen):

	# cmdlist mat be a mixed list or tuple of strings
	# or lists/tuples.
	# Strings are executed by sh -c strng
	# lists/tuples are executed by execvp(lst[0], lst)

	def __init__(self, session, title = "Console", cmdlist = None, finishedCallback = None, closeOnSuccess = False):
		Screen.__init__(self, session)

		self.finishedCallback = finishedCallback
		self.closeOnSuccess = closeOnSuccess
		self.errorOcurred = False

		self["text"] = ScrollLabel("")
		self["summary_description"] = StaticText("")
		self["actions"] = ActionMap(["WizardActions", "DirectionActions"],
		{
			"ok": self.cancel,
			"back": self.cancel,
			"up": self["text"].pageUp,
			"down": self["text"].pageDown
		}, -1)

		self.cmdlist = cmdlist
		self.newtitle = title

		self.onShown.append(self.updateTitle)

		self.container = eConsoleAppContainer()
		self.run = 0
		self.container.appClosed.append(self.runFinished)
		self.container.dataAvail.append(self.dataAvail)
		self.onLayoutFinish.append(self.startRun) # dont start before gui is finished

	def updateTitle(self):
		self.setTitle(self.newtitle)

	def doExec(self, cmd):
		if isinstance(cmd, (list, tuple)):
			return self.container.execute(cmd[0], *cmd)
		else:
			return self.container.execute(cmd)

	def startRun(self):
		self["text"].setText(_("Execution progress:") + "\n\n")
		self["summary_description"].setText(_("Execution progress:"))
		print "[Console] executing in run", self.run, " the command:", self.cmdlist[self.run]
		if self.doExec(self.cmdlist[self.run]): #start of container application failed...
			self.runFinished(-1) # so we must call runFinished manual

	def runFinished(self, retval):
		if retval:
			self.errorOcurred = True
		self.run += 1
		if self.run != len(self.cmdlist):
			if self.doExec(self.cmdlist[self.run]): #start of container application failed...
				self.runFinished(-1) # so we must call runFinished manual
		else:
			lastpage = self["text"].isAtLastPage()
			self["text"].appendText(_("Execution finished!!"))
			self["summary_description"].setText(_("Execution finished!!"))
			if self.finishedCallback is not None:
				self.finishedCallback()
			if not self.errorOcurred and self.closeOnSuccess:
				self.cancel()

	def cancel(self):
		if self.run == len(self.cmdlist):
			self.close()
			self.container.appClosed.remove(self.runFinished)
			self.container.dataAvail.remove(self.dataAvail)

	def dataAvail(self, str):
		self["text"].appendText(str)
