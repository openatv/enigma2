from HTMLComponent import *
from GUIComponent import *

from enigma import eListboxPythonMultiContent, eListbox, gFont

from enigma import eServiceReference, eServiceCenter, \
	eServiceCenterPtr, iListableServicePtr, \
	iStaticServiceInformationPtr

RT_HALIGN_LEFT = 0
RT_HALIGN_RIGHT = 1
RT_HALIGN_CENTER = 2
RT_HALIGN_BLOCK = 4

RT_VALIGN_TOP = 0
RT_VALIGN_CENTER = 8
RT_VALIGN_BOTTOM = 16

RT_WRAP = 32


#
# | name of movie              |
#
def MovieListEntry(serviceref, serviceHandler):
	res = [ serviceref ]

	info = serviceHandler.info(serviceref)
	
	if info is None:
		# ignore service which refuse to info
		return
	
	len = info.getLength(serviceref)
	if len:
		len = "%d:%02d" % (len / 60, len % 60)
	else:
		len = "?:??"
	
	res.append((0, 0, 400, 30, 0, RT_HALIGN_LEFT, info.getName(serviceref)))
	res.append((0, 30, 200, 20, 1, RT_HALIGN_LEFT, "Toller Film"))
	res.append((0, 50, 200, 20, 1, RT_HALIGN_LEFT, "Aufgenommen: irgendwann"))
	res.append((200, 50, 200, 20, 1, RT_HALIGN_RIGHT, len))
	
	return res

class MovieList(HTMLComponent, GUIComponent):
	def __init__(self, root):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.load(root)
		self.l.setList(self.list)
		self.l.setFont(0, gFont("Arial", 30))
		self.l.setFont(1, gFont("Arial", 18))
	
	def getCurrent(self):
		return self.l.getCurrentSelection()
	
	def GUIcreate(self, parent):
		self.instance = eListbox(parent)
		self.instance.setContent(self.l)
		self.instance.setItemHeight(75)
	
	def GUIdelete(self):
		self.instance.setContent(None)
		self.instance = None

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
			self.list.append(MovieListEntry(ref, serviceHandler))

	def reload(self):
		self.load(self.root)
		self.l.setList(self.list)
