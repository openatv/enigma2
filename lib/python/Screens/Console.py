from enigma import eConsoleAppContainer, eActionMap
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Tools.Directories import shellquote
from time import strftime
from sys import maxint
from keyids import KEYIDS

class Console(Screen):

	OUTPUT = "/home/root/logs/console.txt"

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
		self.green = "hide"
		try:
			self.output = open(self.OUTPUT, "w")
		except:
			self.output = None

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

		if self.output:
			if isinstance(cmd, (list, tuple)):
				def quoteifneeded(s):
					return any(c in s for c in " '!()$*?[]<>|&;\\\"") and shellquote(s) or s
				cmdline = " ".join(map(quoteifneeded, cmd))
			else:
				cmdline = cmd
			cmdline = "%d/%d: %s" % (self.run+1, len(self.cmdlist), cmdline)
			started = strftime(_("Started: %T"))
			separator = "-" * max(len(cmdline), len(started))
			print >>self.output, "%s\n%s\n%s\n%s\n" % (separator, cmdline, started, separator)

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
			if self.output and self.run:
				print >>self.output
				if not self["text"].getText().endswith("\n"):
					print >>self.output
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
			if self.output:
				finish = strftime(retval == "stop" and _("Stopped: %T") or _("Finished: %T"))
				print >>self.output, "%s%s\n%s" % (end, "-" * len(finish), finish)
				self.output.close()
				self.output = None
				self["key_green"].text = _("Details")
				self.green = "details"
			else:
				self["key_green"].text = ""
				self.green = None
			if self.stop_msg:
				self.stop_msg.close()
			self.unhide()
			if self.finishedCallback is not None:
				self.finishedCallback()
			if not self.errorOccurred and self.closeOnSuccess:
				self.cancel()

	def key_green(self):
		if self.green == "details":
			with open(self.OUTPUT) as f:
				self["text"].setText(f.read())
			self["key_green"].text = ""     # save/copy/move/rename?
			self.green = ""
		elif self.green == "hide":
			if not self.hidden:
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
		if self.output:
			self.output.write(str)
