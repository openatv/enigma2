from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent

from enigma import eEPGCache, eListbox, eListboxPythonMultiContent, gFont, \
	RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER

from Tools.LoadPixmap import LoadPixmap

from time import localtime, time
from ServiceReference import ServiceReference
from Tools.Directories import resolveFilename, SCOPE_SKIN_IMAGE

EPG_TYPE_SINGLE = 0
EPG_TYPE_MULTI = 1
EPG_TYPE_SIMILAR = 2

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
	def __init__(self, type=EPG_TYPE_SINGLE, selChangedCB=None, timer = None):
		self.days = [ _("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun") ]
		self.timer = timer
		self.onSelChanged = [ ]
		if selChangedCB is not None:
			self.onSelChanged.append(selChangedCB)
		GUIComponent.__init__(self)
		self.type=type
		self.l = eListboxPythonMultiContent()
		if type == EPG_TYPE_SINGLE:
			self.l.setBuildFunc(self.buildSingleEntry)
		elif type == EPG_TYPE_MULTI:
			self.l.setBuildFunc(self.buildMultiEntry)
		else:
			assert(type == EPG_TYPE_SIMILAR)
			self.l.setBuildFunc(self.buildSimilarEntry)
		self.epgcache = eEPGCache.getInstance()
		self.clock_pixmap = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, 'epgclock-fs8.png'))

	def getEventFromId(self, service, eventid):
		event = None
		if self.epgcache is not None and eventid is not None:
			event = self.epgcache.lookupEventId(service.ref, eventid)
		return event

	def getCurrentChangeCount(self):
		if self.type == EPG_TYPE_MULTI:
			return self.l.getCurrentSelection()[0]
		return 0

	def getCurrent(self):
		idx=0
		if self.type == EPG_TYPE_MULTI:
			idx += 1
		tmp = self.l.getCurrentSelection()
		if tmp is None:
			return ( None, None )
		eventid = tmp[idx+1]
		service = ServiceReference(tmp[idx])
		event = self.getEventFromId(service, eventid)
		return ( event, service )

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
				except: # FIXME!!!
					print "FIXME in EPGList.selectionChanged"
					pass

	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setWrapAround(True)
		instance.selectionChanged.get().append(self.selectionChanged)
		instance.setContent(self.l)

	def preWidgetRemove(self, instance):
		instance.selectionChanged.get().remove(self.selectionChanged)
		instance.setContent(None)

	def recalcEntrySize(self):
		esize = self.l.getItemSize()
		self.l.setFont(0, gFont("Regular", 22))
		self.l.setFont(1, gFont("Regular", 16))
		width = esize.width()
		height = esize.height()
		if self.type == EPG_TYPE_SINGLE:
			self.weekday_rect = Rect(0, 0, width/20*2-10, height)
			self.datetime_rect = Rect(width/20*2, 0, width/20*5-15, height)
			self.descr_rect = Rect(width/20*7, 0, width/20*13, height)
		elif self.type == EPG_TYPE_MULTI:
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
		else: # EPG_TYPE_SIMILAR
			self.weekday_rect = Rect(0, 0, width/20*2-10, height)
			self.datetime_rect = Rect(width/20*2, 0, width/20*5-15, height)
			self.service_rect = Rect(width/20*7, 0, width/20*13, height)

	def buildSingleEntry(self, service, eventId, beginTime, duration, EventName):
		rec=beginTime and (self.timer.isInTimer(eventId, beginTime, duration, service) > ((duration/10)*8)) 
		r1=self.weekday_rect
		r2=self.datetime_rect
		r3=self.descr_rect
		res = [ None ]  # no private data needed
		t = localtime(beginTime)
		res.append((eListboxPythonMultiContent.TYPE_TEXT, r1.left(), r1.top(), r1.width(), r1.height(), 0, RT_HALIGN_RIGHT, self.days[t[6]]))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, r2.left(), r2.top(), r2.width(), r1.height(), 0, RT_HALIGN_RIGHT, "%02d.%02d, %02d:%02d"%(t[2],t[1],t[3],t[4])))
		if rec:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, r3.left(), r3.top(), 21, 21, self.clock_pixmap))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.left() + 25, r3.top(), r3.width(), r3.height(), 0, RT_HALIGN_LEFT, EventName))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.left(), r3.top(), r3.width(), r3.height(), 0, RT_HALIGN_LEFT, EventName))
		return res

	def buildSimilarEntry(self, service, eventId, beginTime, service_name, duration):
		rec=beginTime and (self.timer.isInTimer(eventId, beginTime, duration, service) > ((duration/10)*8)) 
		r1=self.weekday_rect
		r2=self.datetime_rect
		r3=self.service_rect
		res = [ None ]  # no private data needed
		t = localtime(beginTime)
		res.append((eListboxPythonMultiContent.TYPE_TEXT, r1.left(), r1.top(), r1.width(), r1.height(), 0, RT_HALIGN_RIGHT, self.days[t[6]]))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, r2.left(), r2.top(), r2.width(), r1.height(), 0, RT_HALIGN_RIGHT, "%02d.%02d, %02d:%02d"%(t[2],t[1],t[3],t[4])))
		if rec:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, r3.left(), r3.top(), 21, 21, self.clock_pixmap))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.left() + 25, r3.top(), r3.width(), r3.height(), 0, RT_HALIGN_LEFT, service_name))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.left(), r3.top(), r3.width(), r3.height(), 0, RT_HALIGN_LEFT, service_name))
		return res

	def buildMultiEntry(self, changecount, service, eventId, begTime, duration, EventName, nowTime, service_name):
		rec=begTime and (self.timer.isInTimer(eventId, begTime, duration, service) > ((duration/10)*8))
		r1=self.service_rect
		r2=self.progress_rect
		r3=self.descr_rect
		r4=self.start_end_rect
		res = [ None ] # no private data needed
		if rec:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r1.left(), r1.top(), r1.width()-21, r1.height(), 0, RT_HALIGN_LEFT, service_name))
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, r1.left()+r1.width()-16, r1.top(), 21, 21, self.clock_pixmap))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r1.left(), r1.top(), r1.width(), r1.height(), 0, RT_HALIGN_LEFT, service_name))
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

	def fillMultiEPG(self, services, stime=-1):
		t = time()
		test = [ (service.ref.toString(), 0, stime) for service in services ]
		test.insert(0, 'X0RIBDTCn')
		self.list = self.queryEPG(test)
		self.l.setList(self.list)
		print time() - t
		self.selectionChanged()

	def updateMultiEPG(self, direction):
		t = time()
		test = [ x[3] and (x[1], direction, x[3]) or (x[1], direction, 0) for x in self.list ]
		test.insert(0, 'XRIBDTCn')
		tmp = self.queryEPG(test)
		cnt=0
		for x in tmp:
			changecount = self.list[cnt][0] + direction
			if changecount >= 0:
				if x[2] is not None:
					self.list[cnt]=(changecount, x[0], x[1], x[2], x[3], x[4], x[5], x[6])
			cnt+=1
		self.l.setList(self.list)
		print time() - t
		self.selectionChanged()

	def fillSingleEPG(self, service):
		t = time()
		test = [ 'RIBDT', (service.ref.toString(), 0, -1, -1) ]
		self.list = self.queryEPG(test)
		self.l.setList(self.list)
		print time() - t
		self.selectionChanged()

	def sortSingleEPG(self, type):
		if len(self.list):
			if type == 1:
				event_id = self.getSelectedEventId()
				self.list.sort(key=lambda x: (x[4] and x[4].lower(), x[2]))
				self.l.setList(self.list)
				self.moveToEventId(event_id)
			else:
				assert(type == 0)
				event_id = self.getSelectedEventId()
				self.list.sort(key=lambda x: x[2])
				self.l.setList(self.list)
				self.moveToEventId(event_id)

	def getSelectedEventId(self):
		x = self.l.getCurrentSelection()
		return x and x[1]

	def moveToEventId(self, eventId):
		index = 0
		for x in self.list:
			if x[1] == eventId:
				self.instance.moveSelectionTo(index)
				break
			index += 1

	def fillSimilarList(self, refstr, event_id):
		t = time()
	 # search similar broadcastings
		if event_id is None:
			return
		l = self.epgcache.search(('RIBND', 1024, eEPGCache.SIMILAR_BROADCASTINGS_SEARCH, refstr, event_id))
		if l and len(l):
			l.sort(key=lambda x: x[2])
		self.l.setList(l)
		self.selectionChanged()
		print time() - t
