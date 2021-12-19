# Coded by Nikolasi
# v1.2
# code otimization (by Sirius)
# add ModuleSlot, rename NameSlot (by Sirius)
# add Module name upper (by Sirius)

from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached
from enigma import eDVBCI_UI, eDVBCIInterfaces


class ModuleControl(Poll, Converter, object):
	SLOT1 = 0
	SLOT2 = 1
	SLOT3 = 2
	SLOT4 = 3
	NAME1 = 4
	NAME2 = 5
	NAME3 = 6
	NAME4 = 7
	PICON1 = 8
	PICON2 = 9
	PICON3 = 10
	PICON4 = 11

	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		if type == "NameSlot1":
			self.type = self.SLOT1
		elif type == "NameSlot2":
			self.type = self.SLOT2
		elif type == "NameSlot3":
			self.type = self.SLOT3
		elif type == "NameSlot4":
			self.type = self.SLOT4
		elif type == "ModuleSlot1":
			self.type = self.NAME1
		elif type == "ModuleSlot2":
			self.type = self.NAME2
		elif type == "ModuleSlot3":
			self.type = self.NAME3
		elif type == "ModuleSlot4":
			self.type = self.NAME4
		elif type == "PiconSlot1":
			self.type = self.PICON1
		elif type == "PiconSlot2":
			self.type = self.PICON2
		elif type == "PiconSlot3":
			self.type = self.PICON3
		elif type == "PiconSlot4":
			self.type = self.PICON4
		self.poll_interval = 1000
		self.poll_enabled = True

	def getFilename(self, state, slot):
		name = ""
		if state == 0:
			name =  _("no module found")
		elif state == 1:
			name = _("init modules")
		elif state == 2:
			name = eDVBCI_UI.getInstance().getAppName(slot).upper()
		return name

	def getSlotname(self, state, slot):
		name = ""
		if state == 0:
			name = _("Slot %d") %(slot+1) + " - " + _("no module found")
		elif state == 1:
			name = _("Slot %d") %(slot+1) + " - " + _("init modules")
		elif state == 2:
			name = _("Slot %d") %(slot+1) + " - " + eDVBCI_UI.getInstance().getAppName(slot).upper()
		return name

	def getPiconname(self, state, slot):
		name = ""
		if state == 0:
			name = "NOMODULE_SLOT%d" %(slot)
		elif state == 1:
			name = "INITMODULE_SLOT%d" %(slot)
		elif state == 2:
			name = "READY_SLOT%d" %(slot)
		return name

	@cached
	def getText(self):
		name = ""
		service = self.source.service
		if service:
			NUM_CI=eDVBCIInterfaces.getInstance().getNumOfSlots()
			if NUM_CI > 0:
				self.control = True
			else:
				self.control = False
		else:
			self.control = False

		if self.type == self.NAME1:
			if self.control:
				state = eDVBCI_UI.getInstance().getState(0)
				if state != -1:
					name = self.getFilename(state, 0)
				else:
					name = _("no module found")
			else:
				name = _("no module found")
			return name
		elif self.type == self.NAME2:
			if self.control:
				state = eDVBCI_UI.getInstance().getState(1)
				if state != -1:
					name = self.getFilename(state, 1)
				else:
					name = _("no module found")
			else:
				name = _("no module found")
			return name
		elif self.type == self.NAME3:
			if self.control:
				state = eDVBCI_UI.getInstance().getState(2)
				if state != -1:
					name = self.getFilename(state, 2)
				else:
					name = _("no module found")
			else:
				name = _("no module found")
			return name
		elif self.type == self.NAME4:
			if self.control:
				state = eDVBCI_UI.getInstance().getState(3)
				if state != -1:
					name = self.getFilename(state, 3)
				else:
					name = _("no module found")
			else:
				name = _("no module found")
			return name

		elif self.type == self.SLOT1:
			if self.control:
				state = eDVBCI_UI.getInstance().getState(0)
				if state != -1:
					name = self.getSlotname(state, 0)
				else:
					name = _("Slot %d") %(1) + " - " + _("no module found")
			else:
				name = _("Slot %d") %(1) + " - " + _("no module found")
			return name
		elif self.type == self.SLOT2:
			if self.control:
				state = eDVBCI_UI.getInstance().getState(1)
				if state != -1:
					name = self.getSlotname(state, 1)
				else:
					name = _("Slot %d") %(2) + " - " + _("no module found")
			else:
				name = _("Slot %d") %(2) + " - " + _("no module found")
			return name
		elif self.type == self.SLOT3:
			if self.control:
				state = eDVBCI_UI.getInstance().getState(2)
				if state != -1:
					name = self.getSlotname(state, 2)
				else:
					name = _("Slot %d") %(3) + " - " + _("no module found")
			else:
				name = _("Slot %d") %(3) + " - " + _("no module found")
			return name
		elif self.type == self.SLOT4:
			if self.control:
				state = eDVBCI_UI.getInstance().getState(3)
				if state != -1:
					name = self.getSlotname(state, 3)
				else:
					name = _("Slot %d") %(4) + " - " + _("no module found")
			else:
				name = _("Slot %d") %(4) + " - " + _("no module found")
			return name

		elif self.type == self.PICON1:
			if self.control:
				state = eDVBCI_UI.getInstance().getState(0)
				if state != -1:
					name = self.getPiconname(state, 1)
				else:
					name = "NOMODULE_SLOT1"
			else:
				name = "NOMODULE_SLOT1"
			return name
		elif self.type == self.PICON2:
			if self.control:
				state = eDVBCI_UI.getInstance().getState(1)
				if state != -1:
					name = self.getPiconname(state, 2)
				else:
					name = "NOMODULE_SLOT2"
			else:
				name = "NOMODULE_SLOT2"
			return name
		elif self.type == self.PICON3:
			if self.control:
				state = eDVBCI_UI.getInstance().getState(2)
				if state != -1:
					name = self.getPiconname(state, 3)
				else:
					name = "NOMODULE_SLOT3"
			else:
				name = "NOMODULE_SLOT3"
			return name
		elif self.type == self.PICON4:
			if self.control:
				state = eDVBCI_UI.getInstance().getState(3)
				if state != -1:
					name = self.getPiconname(state, 4)
				else:
					name = "NOMODULE_SLOT4"
			else:
				name = "NOMODULE_SLOT4"
			return name
		return ""

	text = property(getText)

	def changed(self, what):
		Converter.changed(self, (self.CHANGED_POLL,))
