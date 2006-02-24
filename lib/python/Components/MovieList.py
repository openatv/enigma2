from HTMLComponent import *
from GUIComponent import *
from Tools.FuzzyDate import FuzzyTime
from ServiceReference import ServiceReference
from Components.MultiContent import MultiContentEntryText, RT_HALIGN_LEFT, RT_HALIGN_RIGHT

from enigma import eListboxPythonMultiContent, eListbox, gFont, iServiceInformation

from enigma import eServiceReference, eServiceCenter, \
	eServiceCenterPtr, iListableServicePtr, \
	iStaticServiceInformationPtr

#
# | name of movie              |
#
def MovieListEntry(serviceref, serviceHandler):
	if serviceref.flags & eServiceReference.mustDescent:
		return None

	info = serviceHandler.info(serviceref)
	
	if info is None:
		# ignore service which refuse to info
		return None
	
	len = info.getLength(serviceref)
	if len > 0:
		len = "%d:%02d" % (len / 60, len % 60)
	else:
		len = "?:??"
	
	begin = info.getInfo(serviceref, iServiceInformation.sTimeCreate)
	res = [ (serviceref, begin) ]

	res.append(MultiContentEntryText(pos=(0, 0), size=(560, 30), font = 0, flags = RT_HALIGN_LEFT, text = info.getName(serviceref)))
	
	description = info.getInfoString(serviceref, iServiceInformation.sDescription)

	begin_string = ""
	if begin > 0:
		t = FuzzyTime(begin)
		begin_string = t[0] + ", " + t[1]
	
	res.append(MultiContentEntryText(pos=(0, 30), size=(560, 20), font=1, flags=RT_HALIGN_LEFT, text=description))
	res.append(MultiContentEntryText(pos=(0, 50), size=(270, 20), font=1, flags=RT_HALIGN_LEFT, text=begin_string))
	res.append(MultiContentEntryText(pos=(290, 50), size=(270, 20), font=1, flags=RT_HALIGN_RIGHT, text=len))
	
	return res

class MovieList(HTMLComponent, GUIComponent):
	def __init__(self, root):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		if root is not None:
			self.reload(root)
		self.l.setFont(0, gFont("Regular", 30))
		self.l.setFont(1, gFont("Regular", 18))
		
	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	def getCurrent(self):
		return self.l.getCurrentSelection()[0]
	
	def GUIcreate(self, parent):
		self.instance = eListbox(parent)
		self.instance.setContent(self.l)
		self.instance.setItemHeight(75)
	
	def GUIdelete(self):
		self.instance.setContent(None)
		self.instance = None

	def reload(self, root = None):
		if root is not None:
			self.load(root)
		else:
			self.load(self.root)
		self.l.setList(self.list)

	def removeService(self, service):
		for l in self.list[:]:
			if l[0][0] == service:
				self.list.remove(l)
		self.l.setList(self.list)

	def load(self, root):
		# this lists our root service, then building a 
		# nice list
		
		self.list = [ ]
		self.root = root
		
		serviceHandler = eServiceCenter.getInstance()
		list = serviceHandler.list(root)
		
		if list is None:
			raise "listing of movies failed"

		movieList = [ ]
		while 1:
			s = list.getNext()
			if not s.valid():
				del list
				break
			movieList.append(s)
		
		# now process them...
		for ref in movieList:
			a = MovieListEntry(ref, serviceHandler)
			if a is not None:
				self.list.append(a)
		
		self.list.sort(key=lambda x: -x[0][1])

	def moveTo(self, serviceref):
		found = 0
		count = 0
		for x in self.list:
			if str(ServiceReference(x[0][0])) == str(ServiceReference(serviceref)):
				found = count
			count += 1
		self.instance.moveSelectionTo(found)

	def moveDown(self):
		self.instance.moveSelection(self.instance.moveDown)
