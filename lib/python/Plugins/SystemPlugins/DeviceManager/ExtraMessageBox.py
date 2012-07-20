from enigma import *
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Tools.Directories import resolveFilename, SCOPE_CURRENT_PLUGIN
from Tools.LoadPixmap import LoadPixmap
from Components.Label import Label

def MessageBoxEntry(name, picture):
	pixmap = LoadPixmap(cached = True, path = resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/DeviceManager/icons/" + picture));
	if not pixmap:
		pixmap = LoadPixmap(cached = True, path = resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/DeviceManager/icons/empty.png"));

	return (pixmap, name)

class ExtraMessageBox(Screen):
	skin = """
	<screen name="ExtraMessageBox" position="center,center" size="460,430" title=" ">
		<widget name="message" position="10,10" size="440,25" font="Regular;20" />
		<widget source="menu" render="Listbox" position="20,90" size="420,360" scrollbarMode="showOnDemand">
			<convert type="TemplatedMultiContent">
				{"template": [
					MultiContentEntryPixmapAlphaTest(pos = (5, 0), size = (48, 48), png = 0),
					MultiContentEntryText(pos = (65, 10), size = (425, 38), font=0, flags = RT_HALIGN_LEFT|RT_VALIGN_TOP, text = 1),
					],
					"fonts": [gFont("Regular", 22)],
					"itemHeight": 48
				}
			</convert>
		</widget>
		<applet type="onLayoutFinish">
# this should be factored out into some helper code, but currently demonstrates applets.
from enigma import eSize, ePoint

orgwidth = self.instance.size().width()
orgheight = self.instance.size().height()
orgpos = self.instance.position()
textsize = self[&quot;message&quot;].getSize()

# y size still must be fixed in font stuff...
if self[&quot;message&quot;].getText() != &quot;&quot;:
	textsize = (textsize[0] + 80, textsize[1] + 60)
else:
	textsize = (textsize[0] + 80, textsize[1] + 4)

count = len(self.list)
if count &gt; 7:
	count = 7
offset = 48 * count
wsizex = textsize[0] + 80
wsizey = textsize[1] + offset + 20

if (460 &gt; wsizex):
	wsizex = 460
wsize = (wsizex, wsizey)

# resize
self.instance.resize(eSize(*wsize))

# resize label
self[&quot;message&quot;].instance.resize(eSize(*textsize))

# move list
listsize = (wsizex - 20, 48 * count)
self[&quot;menu&quot;].downstream_elements.downstream_elements.instance.move(ePoint(10, textsize[1] + 10))
self[&quot;menu&quot;].downstream_elements.downstream_elements.instance.resize(eSize(*listsize))

# center window
newwidth = wsize[0]
newheight = wsize[1]
self.instance.move(ePoint(orgpos.x() + (orgwidth - newwidth)/2, orgpos.y()  + (orgheight - newheight)/2))
		</applet>
	</screen>"""

	def __init__(self, session, message = "", title = "", menulist = [], type = 0, exitid = -1, default = 0, timeout = 0):
		# type exist for compability... will be ignored
		Screen.__init__(self, session)
		self.session = session
		self.ctitle = title
		self.exitid = exitid
		self.default = default
		self.timeout = timeout
		self.elapsed = 0

		self.list = []
		for item in menulist:
			self.list.append(MessageBoxEntry(item[0], item[1]))

		self['menu'] = List(self.list)
		self["menu"].onSelectionChanged.append(self.selectionChanged)

		self["message"] = Label(message)
		self["actions"] = ActionMap(["SetupActions"],
		{
			"ok": self.ok,
			"cancel": self.cancel
		}, -2)

		self.onLayoutFinish.append(self.layoutFinished)

		self.timer = eTimer()
		self.timer.callback.append(self.timeoutStep)
		if self.timeout > 0:
			self.timer.start(1000, 1)

	def selectionChanged(self):
		self.timer.stop()
		self.setTitle(self.ctitle)

	def timeoutStep(self):
		self.elapsed += 1
		if self.elapsed == self.timeout:
			self.ok()
		else:
			self.setTitle("%s - %d" % (self.ctitle, self.timeout - self.elapsed))
			self.timer.start(1000, 1)

	def layoutFinished(self):
		if self.timeout > 0:
			self.setTitle("%s - %d" % (self.ctitle, self.timeout))
		else:
			self.setTitle(self.ctitle)
		self['menu'].setCurrentIndex(self.default)

	def ok(self):
		index = self['menu'].getIndex()
		self.close(index)

	def cancel(self):
		if self.exitid > -1:
			self.close(self.exitid)
