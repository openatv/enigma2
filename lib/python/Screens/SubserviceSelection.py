from Screen import Screen
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from enigma import eServiceReferencePtr, eServiceReference, iSubserviceListPtr, eServiceEventPtrPtr

class SubserviceSelection(Screen):
	def KeyOk(self):
		selection = self["subservices"].getCurrent()
		self.close(selection[1])
	def Cancel(self):
		self.close(None)
	def __init__(self, session, subservices, parent=None):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"cancel": self.Cancel,
				"ok": self.KeyOk,
			})

		self.subservices = subservices

		print "subservices", subservices
		tlist = []
		if isinstance(subservices, iSubserviceListPtr):
			n = subservices.getNumberOfSubservices()
			for x in range(n):
				i = subservices.getSubservice(x)
				tlist.append((i.getName(), i))
		elif isinstance(subservices, eServiceEventPtrPtr):
			n = subservices.getNumOfLinkageServices()
			for x in range(n):
				i = subservices.getLinkageService(parent, x)
				tlist.append((i.getName(), i))
		else:
			print "unknown type of subservices"

		self["subservices"] = MenuList(tlist)
