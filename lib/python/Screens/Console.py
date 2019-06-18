from enigma import eConsoleAppContainer, eActionMap
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from sys import maxint
from keyids import KEYIDS

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
		self["key_red"] = StaticText(_("Stop"))
		self["key_green"] = StaticText(_("Hide"))
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"], {
			"ok": self.cancel,
			"cancel": self.cancel,
			"up": self["text"].pageUp,
			"down": self["text"].pageDown,
			"left": self["text"].pageUp,
			"right": self["text"].pageDown,
			"chplus": self.firstPage,
			"chminus": self.lastPage,
			"red": self.key_red,
			"green": self.key_green,
		}, -1)

		self.run = -1
		self.stop_msg = None
		self.hidden = False

		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.runFinished)
		self.container.dataAvail.append(self.dataAvail)
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
		if retval == "stop":
			self.run = len(self.cmdlist) - 1
		elif retval:
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
			self["text"].appendText(end + (retval == "stop" and _("Execution stopped!") or _("Execution finished!")))
			self["key_red"].text = _("Close")
			self["key_green"].text = ""
			if self.stop_msg:
				self.stop_msg.close()
			self.unhide()
			self.hidden = None
			if self.finishedCallback is not None:
				self.finishedCallback()
			if not self.errorOccurred and self.closeOnSuccess:
				self.cancel()

	def key_green(self):
		if self.hidden is False:
			self.hidden = True
			self.hide()
			eActionMap.getInstance().bindAction("", -maxint - 1, self.key_any)

	def key_any(self, key, flag):
		if key not in (KEYIDS["KEY_MUTE"], KEYIDS["KEY_VOLUMEUP"], KEYIDS["KEY_VOLUMEDOWN"]):
			if flag == 1:	# break
				self.unhide()
			return 1

	def unhide(self):
		if self.hidden:
			self.hidden = False
			self.show()
			eActionMap.getInstance().unbindAction("", self.key_any)

	def key_red(self):
		if self.run == len(self.cmdlist):
			self.cancel()
		else:
			self.stop_msg = self.session.openWithCallback(self.cancelCB, MessageBox, _("Stop execution?"), type=MessageBox.TYPE_YESNO, default=False)

	def cancelCB(self, ret=None):
		self.stop_msg = None
		if ret:
			self.cancel()

	def cancel(self):
		if self.run == len(self.cmdlist):
			self.close()
			self.container.appClosed.remove(self.runFinished)
			self.container.dataAvail.remove(self.dataAvail)
		else:
			self.container.kill()
			self.runFinished("stop")

	def dataAvail(self, str):
		self["text"].appendText(str)
