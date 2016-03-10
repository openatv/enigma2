from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import NumberActionMap
from Components.config import config, ConfigSubsection, ConfigText
from Components.Label import Label
from Components.ChoiceList import ChoiceEntryComponent, ChoiceList
from Components.Sources.StaticText import StaticText
import enigma

config.misc.pluginlist = ConfigSubsection()
config.misc.pluginlist.eventinfo_order = ConfigText(default="")
config.misc.pluginlist.extension_order = ConfigText(default="")

class ChoiceBox(Screen):
	def __init__(self, session, title="", list=[], keys=None, selection=0, skin_name=[], reorderConfig="", windowTitle=None):
		Screen.__init__(self, session)

		if isinstance(skin_name, str):
			skin_name = [skin_name]
		self.skinName = skin_name + ["ChoiceBox"]

		self.reorderConfig = reorderConfig
		self["text"] = Label(title)
		self.list = []
		self.summarylist = []
		if keys is None:
			self.__keys = [ "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "red", "green", "yellow", "blue" ] + (len(list) - 14) * [""]
		else:
			self.__keys = keys + (len(list) - len(keys)) * [""]

		self.keymap = {}
		pos = 0
		if self.reorderConfig:
			self.config_type = eval("config.misc.pluginlist." + self.reorderConfig)
			if self.config_type.value:
				prev_list = zip(list, self.__keys)
				new_list = []
				for x in self.config_type.value.split(","):
					for entry in prev_list:
						if entry[0][0] == x:
							new_list.append(entry)
							prev_list.remove(entry)
				list = zip(*(new_list + prev_list))
				list, self.__keys = list[0], list[1]
				number = 1
				new_keys = []
				for x in self.__keys:
					if (not x or x.isdigit()) and number <= 10:
						new_keys.append(str(number % 10))
						number+=1
					else:
						new_keys.append(not x.isdigit() and x or "")
				self.__keys = new_keys
		for x in list:
			strpos = str(self.__keys[pos])
			self.list.append(ChoiceEntryComponent(key = strpos, text = x))
			if self.__keys[pos] != "":
				self.keymap[self.__keys[pos]] = list[pos]
			self.summarylist.append((self.__keys[pos],x[0]))
			pos += 1
		self["list"] = ChoiceList(list = self.list, selection = selection)
		self["summary_list"] = StaticText()
		self["summary_selection"] = StaticText()
		self.updateSummary(selection)

		self["actions"] = NumberActionMap(["WizardActions", "InputActions", "ColorActions", "DirectionActions", "MenuActions"],
		{
			"ok": self.go,
			"back": self.cancel,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal,
			"red": self.keyRed,
			"green": self.keyGreen,
			"yellow": self.keyYellow,
			"blue": self.keyBlue,
			"up": self.up,
			"down": self.down,
			"moveUp": self.additionalMoveUp,
			"moveDown": self.additionalMoveDown,
			"menu": self.setDefaultChoiceList
		}, -1)
		self.windowTitle = windowTitle
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		if self.windowTitle is None:
			self.windowTitle = _("Select")
		if not self.getSkinTitle():
			self.windowTitle = ""
		self.setTitle(self.windowTitle)

	def autoResize(self):
		orgwidth = self.instance.size().width()
		orgpos = self.instance.position()
		textsize = self["text"].getSize()
		count = len(self.list)
		if count > 10:
			count = 10
		offset = 25 * count
		wsizex = textsize[0] + 60
		wsizey = textsize[1] + offset
		if (520 > wsizex):
			wsizex = 520
		wsize = (wsizex, wsizey)
		# resize
		self.instance.resize(enigma.eSize(*wsize))
		# resize label
		self["text"].instance.resize(enigma.eSize(*textsize))
		# move list
		listsize = (wsizex, 25 * count)
		self["list"].instance.move(enigma.ePoint(0, textsize[1]))
		self["list"].instance.resize(enigma.eSize(*listsize))
		# center window
		newwidth = wsize[0]
		self.instance.move(enigma.ePoint((720-wsizex)/2, (576-wsizey)/(count > 7 and 2 or 3)))

	def keyLeft(self):
		pass

	def keyRight(self):
		pass

	def up(self):
		if len(self["list"].list) > 0:
			while 1:
				self["list"].instance.moveSelection(self["list"].instance.moveUp)
				self.updateSummary(self["list"].l.getCurrentSelectionIndex())
				if self["list"].l.getCurrentSelection()[0][0] != "--" or self["list"].l.getCurrentSelectionIndex() == 0:
					break

	def down(self):
		if len(self["list"].list) > 0:
			while 1:
				self["list"].instance.moveSelection(self["list"].instance.moveDown)
				self.updateSummary(self["list"].l.getCurrentSelectionIndex())
				if self["list"].l.getCurrentSelection()[0][0] != "--" or self["list"].l.getCurrentSelectionIndex() == len(self["list"].list) - 1:
					break

	# runs a number shortcut
	def keyNumberGlobal(self, number):
		self.goKey(str(number))

	# runs the current selected entry
	def go(self):
		cursel = self["list"].l.getCurrentSelection()
		if cursel:
			self.goEntry(cursel[0])
		else:
			self.cancel()

	# runs a specific entry
	def goEntry(self, entry):
		if len(entry) > 2 and isinstance(entry[1], str) and entry[1] == "CALLFUNC":
			# CALLFUNC wants to have the current selection as argument
			arg = self["list"].l.getCurrentSelection()[0]
			entry[2](arg)
		else:
			self.close(entry)

	# lookups a key in the keymap, then runs it
	def goKey(self, key):
		if self.keymap.has_key(key):
			entry = self.keymap[key]
			self.goEntry(entry)

	# runs a color shortcut
	def keyRed(self):
		self.goKey("red")

	def keyGreen(self):
		self.goKey("green")

	def keyYellow(self):
		self.goKey("yellow")

	def keyBlue(self):
		self.goKey("blue")

	def updateSummary(self, curpos=0):
		pos = 0
		summarytext = ""
		for entry in self.summarylist:
			if pos > curpos-2 and pos < curpos+5:
				if pos == curpos:
					summarytext += ">"
					self["summary_selection"].setText(entry[1])
				else:
					summarytext += entry[0]
				summarytext += ' ' + entry[1] + '\n'
			pos += 1
		self["summary_list"].setText(summarytext)

	def cancel(self):
		self.close(None)

	def setDefaultChoiceList(self):
		if self.reorderConfig:
			if len(self.list) > 0 and self.config_type.value != "":
				self.session.openWithCallback(self.setDefaultChoiceListCallback, MessageBox, _("Sort list to default and exit?"), MessageBox.TYPE_YESNO)
		elif self.keymap.has_key("menu"):
			self.goKey("menu")
		else:
			self.cancel()

	def setDefaultChoiceListCallback(self, answer):
		if answer:
			self.config_type.value = ""
			self.config_type.save()
			self.cancel()

	def additionalMoveUp(self):
		if self.reorderConfig:
			self.additionalMove(-1)

	def additionalMoveDown(self):
		if self.reorderConfig:
			self.additionalMove(1)

	def additionalMove(self, direction):
		if len(self.list) > 1:
			currentIndex = self["list"].getSelectionIndex()
			swapIndex = (currentIndex + direction) % len(self.list)
			if currentIndex == 0 and swapIndex != 1:
				self.list = self.list[1:] + [self.list[0]]
			elif swapIndex == 0 and currentIndex != 1:
				self.list = [self.list[-1]] + self.list[:-1]
			else:
				self.list[currentIndex], self.list[swapIndex] = self.list[swapIndex], self.list[currentIndex]
			self["list"].l.setList(self.list)
			if direction == 1:
				self["list"].down()
			else:
				self["list"].up()
			self.config_type.value = ",".join(x[0][0] for x in self.list)
			self.config_type.save()
