from HTMLComponent import *
from GUIComponent import *

from enigma import *
from re import *
from time import localtime, time
from ServiceReference import ServiceReference

EPG_TYPE_SINGLE = 0
EPG_TYPE_MULTI = 1

RT_HALIGN_LEFT = 0
RT_HALIGN_RIGHT = 1
RT_HALIGN_CENTER = 2
RT_HALIGN_BLOCK = 4

RT_VALIGN_TOP = 0
RT_VALIGN_CENTER = 8
RT_VALIGN_BOTTOM = 16

RT_WRAP = 32

SINGLE_CPP = 0

class Rect:
	def __init__(self, x, y, width, height):
		self.__left = x
		self.__top = y
		self.__width = width
		self.__height = height

	def left(self):
		return self.__left

	def top(self):
		return self.__top

	def height(self):
		return self.__height

	def width(self):
		return self.__width

class EPGList(HTMLComponent, GUIComponent):
	def __init__(self, type=EPG_TYPE_SINGLE, selChangedCB=None):
		self.onSelChanged = [ ]
		if selChangedCB is not None:
			self.onSelChanged.append(selChangedCB)
		GUIComponent.__init__(self)
		self.type=type
		if type == EPG_TYPE_SINGLE and SINGLE_CPP > 0:
			self.l = eListboxEPGContent()
		else:
			self.l = eListboxPythonMultiContent()
		self.epgcache = eEPGCache.getInstance()

	def getEventFromId(self, service, eventid):
		event = None
		if self.epgcache is not None and eventid is not None:
			event = self.epgcache.lookupEventId(service.ref, eventid)
		return event

	def getCurrentChangeCount(self):
		if self.type == EPG_TYPE_SINGLE:
			return 0
		return self.l.getCurrentSelection()[0][0]

	def getCurrent(self):
		if self.type == EPG_TYPE_SINGLE:
			if SINGLE_CPP > 0:
				evt = self.l.getCurrent()
			else:
				eventid = self.l.getCurrentSelection()[0]
				evt = self.getEventFromId(self.service, eventid)
		else:
			tmp = self.l.getCurrentSelection()[0]
			eventid = tmp[1]
			service = ServiceReference(tmp[2])
			event = self.getEventFromId(service, eventid)
			evt = ( event, service )
		return evt

	def moveUp(self):
		self.instance.moveSelection(self.instance.moveUp)

	def moveDown(self):
		self.instance.moveSelection(self.instance.moveDown)

	def connectSelectionChanged(func):
		if not self.onSelChanged.count(func):
			self.onSelChanged.append(func)

	def disconnectSelectionChanged(func):
		self.onSelChanged.remove(func)

	def selectionChanged(self):
		for x in self.onSelChanged:
			if x is not None:
				try:
					x()
				except:
					pass

	def GUIcreate(self, parent):
		self.instance = eListbox(parent)
		self.instance.setWrapAround(True)
		self.instance.selectionChanged.get().append(self.selectionChanged)
		self.instance.setContent(self.l)
		if SINGLE_CPP > 0:
			self.instance.setItemHeight(25)

	def GUIdelete(self):
		self.instance = None

	def recalcEntrySize(self):
		if SINGLE_CPP == 0:
			esize = self.l.getItemSize()
			self.l.setFont(0, gFont("Regular", 22))
			self.l.setFont(1, gFont("Regular", 16))
			width = esize.width()
			height = esize.height()
			if self.type == EPG_TYPE_SINGLE:
				w = width/20*5
				self.datetime_rect = Rect(0,0, w, height)
				self.descr_rect = Rect(w, 0, width/20*15, height)
			else:
				xpos = 0;
				w = width/10*3;
				self.service_rect = Rect(xpos, 0, w-10, height)
				xpos += w;
				w = width/10*2;
				self.start_end_rect = Rect(xpos, 0, w-10, height)
				self.progress_rect = Rect(xpos, 4, w-10, height-8)
				xpos += w
				w = width/10*5;
				self.descr_rect = Rect(xpos, 0, width, height)

	def buildSingleEntry(self, eventId, beginTime, duration, EventName):
		r1=self.datetime_rect
		r2=self.descr_rect
		res = [ eventId ]
		t = localtime(beginTime)
		res.append((eListboxPythonMultiContent.TYPE_TEXT, r1.left(), r1.top(), r1.width(), r1.height(), 0, RT_HALIGN_LEFT, "%02d.%02d, %02d:%02d"%(t[2],t[1],t[3],t[4])))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, r2.left(), r2.top(), r2.width(), r2.height(), 0, RT_HALIGN_LEFT, EventName))
		return res

	def buildMultiEntry(self, changecount, service, eventId, begTime, duration, EventName, nowTime, service_name):
		sname = service_name
		r1=self.service_rect
		r2=self.progress_rect
		r3=self.descr_rect
		r4=self.start_end_rect
		res = [ (changecount, eventId, service, begTime, duration) ]
		re = compile('\xc2\x86.*?\xc2\x87')
		list = re.findall(sname)
		if len(list):
			sname=''
			for substr in list:
				sname+=substr[2:len(substr)-2]
			if len(sname) == 0:
				sname = service_name;
		res.append((eListboxPythonMultiContent.TYPE_TEXT, r1.left(), r1.top(), r1.width(), r1.height(), 0, RT_HALIGN_LEFT, sname))
		if begTime is not None:
			if nowTime < begTime:
				begin = localtime(begTime)
				end = localtime(begTime+duration)
#				print "begin", begin
#				print "end", end
				res.append((eListboxPythonMultiContent.TYPE_TEXT, r4.left(), r4.top(), r4.width(), r4.height(), 1, RT_HALIGN_CENTER|RT_VALIGN_CENTER, "%02d.%02d - %02d.%02d"%(begin[3],begin[4],end[3],end[4])));
				res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.left(), r3.top(), r3.width(), r3.height(), 0, RT_HALIGN_LEFT, EventName))
			else:
				percent = (nowTime - begTime) * 100 / duration
				res.append((eListboxPythonMultiContent.TYPE_PROGRESS, r2.left(), r2.top(), r2.width(), r2.height(), percent));
				res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.left(), r3.top(), r3.width(), r3.height(), 0, RT_HALIGN_LEFT, EventName))
		return res

	def queryEPG(self, list, buildFunc=None):
		if self.epgcache is not None:
			if buildFunc is not None:
				return self.epgcache.lookupEvent(list, buildFunc)
			else:
				return self.epgcache.lookupEvent(list)
		return [ ]

	def fillMultiEPG(self, services):
		t = time()
		test = [ 'RIBDTCN' ]
		for service in services:
			tuple = ( service.ref.toString(), 0 )
			test.append( tuple )
#		self.list = self.queryEPG(test, self.buildMultiEntry)
		tmp = self.queryEPG(test)
		self.list = [ ]
		for x in tmp:
			self.list.append(self.buildMultiEntry(0, x[0], x[1], x[2], x[3], x[4], x[5], x[6]))
		self.l.setList(self.list)
		print time() - t
		self.selectionChanged()

	def updateMultiEPG(self, direction):
		t = time()
		test = [ 'RIBDTCN' ]
		for x in self.list:
			data = x[0]
			service = data[2]
			begTime = data[3]
			duration = data[4]
			if begTime is None:
				begTime = 0
			test.append((service, direction, begTime))
#		self.list = self.queryEPG(test, self.buildMultiEntry)
		tmp = self.queryEPG(test)
		cnt=0
		for x in tmp:
			changecount = self.list[cnt][0][0] + direction
			if changecount >= 0:
				if x[2] is not None:
					self.list[cnt]=self.buildMultiEntry(changecount, x[0], x[1], x[2], x[3], x[4], x[5], x[6])
			cnt+=1
		self.l.setList(self.list)
		print time() - t
		self.selectionChanged()

	def fillSingleEPG(self, service):
		t = time()
		if SINGLE_CPP > 0:
			self.l.setRoot(service.ref)
		else:
			self.service = service
			test = [ 'IBDT', (service.ref.toString(), 0, -1, -1) ]
#			self.list = self.queryEPG(test, self.buildSingleEntry)
			tmp = self.queryEPG(test)
			self.list = [ ]
			for x in tmp:
				self.list.append(self.buildSingleEntry(x[0], x[1], x[2], x[3]))
#				self.list.append(self.buildSingleEntry(refstr, x[0], x[1], x[2], x[3]))
			self.l.setList(self.list)
		print time() - t
		self.selectionChanged()
