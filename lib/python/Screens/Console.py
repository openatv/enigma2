from enigma import eConsoleAppContainer
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.ScrollLabel import ScrollLabel

class Console(Screen):

	# cmdlist may be a mixed list or tuple of strings
	# or lists/tuples.
	# Strings are executed by "sh -c string",
	# lists/tuples are executed by "execvp(lst[0], lst)".

	def __init__(self, session, title=_("Console"), cmdlist=None, finishedCallback=None, closeOnSuccess=False):
		Screen.__init__(self, session)

		self.cmdlist = cmdlist
		self.finishedCallback = finishedCallback
		self.closeOnSuccess = closeOnSuccess
		self.errorOccurred = False

		self.title = title
		self["text"] = ScrollLabel()
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], {
			"ok": self.cancel,
			"cancel": self.cancel,
			"up": self["text"].pageUp,
			"down": self["text"].pageDown,
			"left": self["text"].pageUp,
			"right": self["text"].pageDown,
			"chplus": self.firstPage,
			"chminus": self.lastPage,
		}, -1)

		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.runFinished)
		self.container.dataAvail.append(self.dataAvail)
		self.run = -1
		self.onLayoutFinish.append(self.startRun)	# don't start before gui is finished

	def firstPage(self):
		self["text"].setPos(0)
		self["text"].updateScrollbar()

	def lastPage(self):
		self["text"].lastPage()
		self["text"].updateScrollbar()

	def doExec(self, cmd):
		print "[Console] executing command %d/%d:" % (self.run+1, len(self.cmdlist)), cmd
		if isinstance(cmd, (list, tuple)):
			return self.container.execute(cmd[0], *cmd)
		else:
			return self.container.execute(cmd)

	def startRun(self):
		self["text"].setText(_("Execution progress:") + "\n\n")
		self.runFinished(0)

	def runFinished(self, retval):
		if retval:
			self.errorOccurred = True
		self.run += 1
		if self.run != len(self.cmdlist):
			if self.doExec(self.cmdlist[self.run]): 	# start of container application failed...
				self.runFinished(-1)					# so we must call runFinished manually
		else:
			end = self["text"].getText()[-4:].replace("\r", "")
			if end.endswith("\n\n"):
				end = ""    # already ends with a blank, no need for another one
			elif end.endswith("\n"):
				end = "\n"
			else:
				end = "\n\n"
			self["text"].appendText(end + _("Execution finished!"))
			if self.finishedCallback is not None:
				self.finishedCallback()
			if not self.errorOccurred and self.closeOnSuccess:
				self.cancel()

	def cancel(self):
		if self.run == len(self.cmdlist):
			self.close()
			self.container.appClosed.remove(self.runFinished)
			self.container.dataAvail.remove(self.dataAvail)

	def dataAvail(self, str):
		self["text"].appendText(str)
