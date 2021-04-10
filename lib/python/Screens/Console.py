from enigma import eConsoleAppContainer
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Components.Label import Label

class Console(Screen):

	# cmdlist mat be a mixed list or tuple of strings
	# or lists/tuples.
	# Strings are executed by sh -c strng
	# lists/tuples are executed by execvp(lst[0], lst)

	def __init__(self, session, title=_("Console"), cmdlist=None, finishedCallback=None, closeOnSuccess=False):
		Screen.__init__(self, session)

		self.finishedCallback = finishedCallback
		self.closeOnSuccess = closeOnSuccess
		self.errorOcurred = False

		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("hide"))

		self["text"] = ScrollLabel("")
		self["summary_description"] = StaticText("")
		self["actions"] = ActionMap(["WizardActions", "DirectionActions", "ColorActions"],
		{
			"ok": self.cancel,
			"back": self.cancel,
			"up": self.key_up,
			"down": self.key_down,
			"green": self.key_green,
			"red": self.key_red
		}, -1)

		self.cmdlist = cmdlist
		self.newtitle = title

		self.screen_hide = False
		self.cancel_msg = None
		self.output_file = ''

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
			self.toggleScreenHide(True)
		self.run += 1
		if self.run != len(self.cmdlist):
			if self.doExec(self.cmdlist[self.run]): #start of container application failed...
				self.runFinished(-1) # so we must call runFinished manual
		else:
			self["key_red"].setText(_("Close"))
			self["key_green"].setText(_("Save"))
			self.toggleScreenHide(True)
			if self.cancel_msg:
				self.cancel_msg.close()
			lastpage = self["text"].isAtLastPage()
			self["text"].appendText('\n' + _("Execution finished!!"))
			self["summary_description"].setText('\n' + _("Execution finished!!"))
			if self.finishedCallback is not None:
				self.finishedCallback()
			if not self.errorOcurred and self.closeOnSuccess:
				self.output_file = 'end'
				self.cancel()

	def key_up(self):
		if self.screen_hide:
			self.toggleScreenHide()
			return
		self["text"].pageUp()

	def key_down(self):
		if self.screen_hide:
			self.toggleScreenHide()
			return
		self["text"].pageDown()

	def key_green(self):
		if self.screen_hide:
			self.toggleScreenHide()
			return
		if self.output_file == 'end':
			pass
		elif self.output_file.startswith('/tmp/'):
			self["text"].setText(self.readFile(self.output_file))
			self["key_green"].setText(_(" "))
			self.output_file = 'end'
		elif self.run == len(self.cmdlist):
			self.saveOutputText()
		else:
			self.toggleScreenHide()

	def key_red(self):
		if self.screen_hide:
			self.toggleScreenHide()
			return
		if self.run == len(self.cmdlist):
			self.cancel()
		else:
			self.cancel_msg = self.session.openWithCallback(self.cancelCB, MessageBox, _("Cancel execution?"), type=MessageBox.TYPE_YESNO, default=False)

	def cancelCB(self, ret=None):
		self.cancel_msg = None
		if ret:
			self.cancel(True)

	def saveOutputText(self):
		from time import time, localtime
		lt = localtime(time())
		self.output_file = '/tmp/%02d%02d%02d_console.txt' %(lt[3],lt[4],lt[5])
		self.session.openWithCallback(self.saveOutputTextCB, MessageBox, _("Save the commands and the output to a file?\n('%s')") %self.output_file, type=MessageBox.TYPE_YESNO, default=True)

	def formatCmdList(self, source):
		if isinstance(source, (list, tuple)):
			for x in source:
				for y in self.formatCmdList(x):
					yield y
		else:
			yield source

	def saveOutputTextCB(self, ret=None):
		if ret:
			from os import path
			failtext = _("Path to save not exist: '/tmp/'")
			if path.exists('/tmp/'):
				text = 'commands ...\n\n'
				try:
					cmdlist = list(self.formatCmdList(self.cmdlist))
					text += 'command line: %s\n\n' %cmdlist[0]
					script = ''
					for cmd in cmdlist[0].split():
						if '.' in cmd:
							if cmd[-3:] in ('.py', '.sh'):
								script = cmd
							break
					if script and path.isfile(script):
						text += 'script listing: %s\n\n%s\n\n' %(script, self.readFile(script))
					if len(cmdlist) > 1:
						text += 'next commands:\n\n' + '\n'.join(cmdlist[1:]) + '\n\n'
				except:
					text += 'error read commands!!!\n\n'
				text += '-'*50 + '\n\noutputs ...\n\n%s' %self["text"].getText()
				try:
					f = open(self.output_file, 'w')
					f.write(text)
					f.close()
					self["key_green"].setText(_("Load"))
					return
				except:
					failtext = _("File write error: '%s'") %self.output_file
			self.output_file = 'end'
			self["key_green"].setText(_(" "))
			self.session.open(MessageBox, failtext, type=MessageBox.TYPE_ERROR)
		else:
			self.output_file = ''

	def toggleScreenHide(self, setshow=False):
		if self.screen_hide or setshow:
			self.show()
		else:
			self.hide()
		self.screen_hide = not (self.screen_hide or setshow)

	def readFile(self, file):
		try:
			with open(file, 'r') as rdfile:
				rd = rdfile.read()
			rdfile.close()
		except:
			if file == self.output_file:
				rd = self["text"].getText()
			else:
				rd = "File read error: '%s'\n" %file
		return rd

	def cancel(self, force=False):
		if self.screen_hide:
			self.toggleScreenHide()
			return
		if force or self.run == len(self.cmdlist):
			self.close()
			self.container.appClosed.remove(self.runFinished)
			self.container.dataAvail.remove(self.dataAvail)
			if self.run != len(self.cmdlist):
				self.container.kill()

	def dataAvail(self, str):
		self["text"].appendText(str)
