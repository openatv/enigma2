from Screen import *
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.Header import Header
from Components.Button import Button
from Components.Label import Label

class CiMmi(Screen):
	def addEntry(self, list, entry):
		if entry[0] == "TEXT":		#handle every item (text / pin only?)
			pass
		pass

	def __init__(self, session, slotid, title, subtitle, bottom, entries):
		Screen.__init__(self, session)

		self.slotid = slotid
		self["title"] = Label(title)
		self["subtitle"] = Label(subtitle)
		self["bottom"] = Label(bottom)
				
		list = [ ]
		for entry in entries:
			self.addEntry(list, entry)
		self["entries"] = MenuList(list)	#menulist!?
		
		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				#"ok": self.okbuttonClick,
				"cancel": self.close
			})

#just for testing - we need an cimanager? (or not?)
class CiSelection(Screen):
	def okbuttonClick(self):
		#generate menu / list
		list = [ ]
		list.append( ("TEXT", "CA-Info") )
		list.append( ("TEXT", "Card Status") )
		#list.append( ("PIN", "Card Pin") )
		self.session.open(CiMmi, 0, "Wichtiges CI", "Mainmenu", "Footer", list)
		
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self.okbuttonClick,
				"cancel": self.close
			})
