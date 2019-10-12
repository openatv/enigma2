from enigma import eTimer, ePoint, eSize, getDesktop

from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap, MultiPixmap
from Components.Sources.StaticText import StaticText
from Screens.HelpMenu import HelpableScreen
from Screens.Screen import Screen


class MessageBox(Screen, HelpableScreen):
	TYPE_YESNO = 0
	TYPE_INFO = 1
	TYPE_WARNING = 2
	TYPE_ERROR = 3
	TYPE_MESSAGE = 4

	TYPE_PREFIX = {
		TYPE_YESNO: _("Question"),
		TYPE_INFO: _("Information"),
		TYPE_WARNING: _("Warning"),
		TYPE_ERROR: _("Error"),
		TYPE_MESSAGE: _("Message")
	}

	def __init__(self, session, text, type=TYPE_YESNO, timeout=0, close_on_any_key=False, default=True, enable_input=True, msgBoxID=None, picon=True, simple=False, wizard=False, list=None, skin_name=None, timeout_default=None, title=None, windowTitle=None, showYESNO=False):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		if text:
			self.text = _(text)
		else:
			self.text = text
		if type in range(self.TYPE_MESSAGE + 1):
			self.type = type
		else:
			self.type = self.TYPE_MESSAGE
		self.timeout = int(timeout)
		self.close_on_any_key = close_on_any_key
		if enable_input:
			self["actions"] = HelpableActionMap(self, ["MsgBoxActions", "DirectionActions"], {
				"cancel": (self.cancel, _("Cancel the selection")),
				"ok": (self.ok, _("Accept the current selection")),
				"alwaysOK": (self.alwaysOK, _("Always select OK")),
				"up": (self.up, _("Move up a line")),
				"down": (self.down, _("Move down a line")),
				"left": (self.left, _("Move up a page")),
				"right": (self.right, _("Move down a page"))
				# These actions are *ONLY* defined on OpenPLi!
				# I don't believe thay add any functionality even for OpenPLi.
				# "upRepeated": (self.up, _("Move up a line repeatedly")),
				# "downRepeated": (self.down, _("Move down a line repeatedly")),
				# "leftRepeated": (self.left, _("Move up a page repeatedly")),
				# "rightRepeated": (self.right, _("Move down a page repeatedly"))
			}, prio=-1, description=_("MessageBox Functions"))
		self.msgBoxID = msgBoxID
		# These six lines can go with new skins that only use self["icon"]...
		self["QuestionPixmap"] = Pixmap()
		self["QuestionPixmap"].hide()
		self["InfoPixmap"] = Pixmap()
		self["InfoPixmap"].hide()
		self["ErrorPixmap"] = Pixmap()
		self["ErrorPixmap"].hide()
		self["icon"] = MultiPixmap()
		self["icon"].hide()
		self.picon = picon
		if picon:
			# These five lines can go with new skins that only use self["icon"]...
			if self.type == self.TYPE_YESNO:
				self["QuestionPixmap"].show()
			elif self.type == self.TYPE_INFO or self.type == self.TYPE_WARNING:
				self["InfoPixmap"].show()
			elif self.type == self.TYPE_ERROR:
				self["ErrorPixmap"].show()
			self["icon"].show()
		self.skinName = ["MessageBox"]
		if simple:
			self.skinName = ["MessageBoxSimple"]
		if wizard:
			self["rc"] = MultiPixmap()
			self["rc"].setPixmapNum(config.misc.rcused.value)
			self.skinName = ["MessageBoxWizard"]
		if not skin_name:
			skin_name = []
		if isinstance(skin_name, str):
			self.skinName = [skin_name] + self.skinName
		if not list:
			list = []
		if type == self.TYPE_YESNO or showYESNO:
			if list:
				self.list = list
			elif default:
				self.list = [(_("Yes"), True), (_("No"), False)]
			else:
				self.list = [(_("No"), False), (_("Yes"), True)]
		else:
			self.list = []
		self.timeout_default = timeout_default
		self.baseTitle = title or windowTitle or self.TYPE_PREFIX.get(self.type, None)
		self.activeTitle = None
		# DEBUG: This is a temporary patch to stop the VuRemote and GigaBlueRemote plugins from crashing!
		# If this code is accepted then the offending lines from the plugins can safely be removed.
		self.timerRunning = None  # DEBG: See note above!
		self["text"] = Label(self.text)
		self["Text"] = StaticText(self.text)  # What is self["Text"] for?
		self["selectedChoice"] = StaticText()
		self["list"] = MenuList(self.list)
		if self.list:
			self["selectedChoice"].setText(self.list[0][0])
		else:
			self["list"].hide()
		self["key_help"] = StaticText(_("HELP"))
		self.timer = eTimer()
		self.timer.callback.append(self.processTimer)
		if self.layoutFinished not in self.onLayoutFinish:
			self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self["icon"].setPixmapNum(self.type)
		prefix = self.TYPE_PREFIX.get(self.type, _("Unknown"))
		if self.baseTitle is None:
			title = self.getTitle()
			if title:
				if "%s" in title:
					self.baseTitle = title % prefix
				else:
					self.baseTitle = title
			else:
				self.baseTitle = prefix
		elif "%s" in self.baseTitle:
			self.baseTitle = self.baseTitle % prefix
		self.setTitle(self.baseTitle)
		if self.timeout > 0:
			print "[MessageBox] Timeout set to %d seconds." % self.timeout
			self.timer.start(25)

	def processTimer(self):
		# Check if the title has been externally changed and if so make it the dominant title.
		if self.activeTitle is None:
			self.activeTitle = self.getTitle()
			if "%s" in self.activeTitle:
				self.activeTitle = self.activeTitle % self.TYPE_PREFIX.get(self.type, _("Unknown"))
		if self.baseTitle != self.activeTitle:
			self.baseTitle = self.activeTitle
		if self.timeout > 0:
			if self.baseTitle:
				self.setTitle("%s (%d)" % (self.baseTitle, self.timeout))
			self.timer.start(1000)
			self.timeout -= 1
		else:
			self.stopTimer("Timeout!")
			if self.timeout_default is not None:
				self.close(self.timeout_default)
			else:
				self.ok()

	def stopTimer(self, reason):
		print "[MessageBox] %s" % reason
		self.timer.stop()
		self.timeout = 0
		if self.baseTitle is not None:
			self.setTitle(self.baseTitle)

	def autoResize(self):
		count = len(self.list)
		if not self["text"].text:
			textsize = (520, 0)
			listsize = (520, 25 * count)
			if self.picon:
				self["list"].instance.move(ePoint(65, 0))
				wsizex = textsize[0] + 65
			else:
				self["list"].instance.move(ePoint(0, 0))
				wsizex = textsize[0]
			self["list"].instance.resize(eSize(*listsize))
		else:
			textsize = self["text"].getSize()
			if textsize[0] < textsize[1]:
				textsize = (textsize[1], textsize[0] + 10)
			if textsize[0] > 520:
				textsize = (textsize[0], textsize[1] + 25)
			else:
				textsize = (520, textsize[1] + 25)
			listsize = (textsize[0], 25 * count)

			self["text"].instance.resize(eSize(*textsize))
			if self.picon:
				self["text"].instance.move(ePoint(65, 0))
				self["list"].instance.move(ePoint(65, textsize[1]))
				wsizex = textsize[0] + 65
			else:
				self["text"].instance.move(ePoint(10, 10))
				self["list"].instance.move(ePoint(0, textsize[1]))
				wsizex = textsize[0]
			self["list"].instance.resize(eSize(*listsize))
		wsizey = textsize[1] + listsize[1]
		self.instance.resize(eSize(*(wsizex, wsizey)))
		self.instance.move(ePoint((getDesktop(0).size().width() - wsizex) / 2, (getDesktop(0).size().height() - wsizey) / 2))

	def cancel(self):
		if self["list"].list:
			for l in self["list"].list:
				# print "[MessageBox] DEBUG: (cancel) '%s' -> '%s'" % (str(l[0]), str(l[1]))
				# Should we be looking at the second element to get the boolean value rather than the word?
				if l[0].lower() == _('no') or l[0].lower() == _('false'):
					if len(l) > 2:
						l[2](None)
					else:
						self.close(False)
					break
		self.close(False)

	def ok(self):
		if self["list"].getCurrent():
			self.goEntry(self["list"].getCurrent())
		else:
			self.close(True)

	def goEntry(self, entry=None):
		if not entry:
			entry = []
		if entry and len(entry) > 3 and isinstance(entry[1], str) and entry[1] == "CALLFUNC":
			arg = entry[3]
			entry[2](arg)
		elif entry and len(entry) > 2 and isinstance(entry[1], str) and entry[1] == "CALLFUNC":
			entry[2](None)
		elif entry:
			self.close(entry[1])
		else:
			self.close(False)

	def alwaysOK(self):
		if self["list"].list:
			for l in self["list"].list:
				# print "[MessageBox] DEBUG: (cancel) '%s' -> '%s'" % (str(l[0]), str(l[1]))
				# Should we be looking at the second element to get the boolean value rather than the word?
				if l[0].lower() == _('yes') or l[0].lower() == _('true'):
					if len(l) > 2:
						self.goEntry(l)
					else:
						self.close(True)
					break
		else:
			self.close(True)

	def up(self):
		self.move(self["list"].instance.moveUp)

	def down(self):
		self.move(self["list"].instance.moveDown)

	def left(self):
		self.move(self["list"].instance.pageUp)

	def right(self):
		self.move(self["list"].instance.pageDown)

	def move(self, direction):
		if self.timeout > 0:
			self.stopTimer("Timeout stopped by user input!")
		if self.close_on_any_key:
			self.close(True)
		self["list"].instance.moveSelection(direction)
		if self.list:
			self["selectedChoice"].setText(self["list"].getCurrent()[0])

	def __repr__(self):
		return "%s(%s)" % (str(type(self)), self.text)
