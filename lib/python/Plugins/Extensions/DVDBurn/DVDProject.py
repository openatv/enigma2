
from Tools.Directories import fileExists
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigYesNo, ConfigText, ConfigSelection, getConfigListEntry, ConfigSequence

class ConfigColor(ConfigSequence):
	def __init__(self):
		ConfigSequence.__init__(self, seperator = "#", limits = [(0,255),(0,255),(0,255)])

class ConfigPixelvals(ConfigSequence):
	def __init__(self):
		ConfigSequence.__init__(self, seperator = ",", limits = [(0,200),(0,200),(0,200)])

class ConfigPixelvals(ConfigSequence):
	def __init__(self):
		ConfigSequence.__init__(self, seperator = ",", limits = [(0,200),(0,200),(0,200)])

class ConfigFilename(ConfigText):
	def __init__(self):
		ConfigText.__init__(self, default = "", fixed_size = True, visible_width = False)

	def getMulti(self, selected):
		filename = (self.text.rstrip("/").rsplit("/",1))[1].encode("utf-8")[:40] + " "
		print "ConfigFilename =", filename
		if self.allmarked:
			mark = range(0, len(filename))
		else:
			mark = [filename]
		return ("mtext"[1-selected:], filename, mark)
	
class DVDProject:
	def __init__(self):
		self.titles = [ ]
		self.target = None
		self.settings = ConfigSubsection()
		self.settings.name = ConfigText(fixed_size = False, visible_width = 40)
		self.settings.authormode = ConfigSelection(choices = [("menu_linked", _("Linked titles with a DVD menu")), ("just_linked", _("Direct playback of linked titles without menu")), ("menu_seperate", _("Seperate titles with a main menu")), ])
		self.settings.menubg = ConfigFilename()
		self.settings.menuaudio = ConfigFilename()
		self.settings.titleformat = ConfigText(fixed_size = False, visible_width = 40)
		self.settings.subtitleformat = ConfigText(fixed_size = False, visible_width = 40)
		self.settings.color_headline = ConfigColor()
		self.settings.color_highlight = ConfigColor()
		self.settings.color_button = ConfigColor()
		self.settings.font_face = ConfigFilename()
		self.settings.font_size = ConfigPixelvals()
		self.settings.space = ConfigPixelvals()
		self.settings.vmgm = ConfigFilename()
		self.settings.autochapter = ConfigInteger(default = 0, limits = (0, 99))
		self.filekeys = ["vmgm", "menubg", "menuaudio", "font_face"]

	def addService(self, service):
		import DVDTitle
		title = DVDTitle.DVDTitle()
		title.addService(service)
		self.titles.append(title)
		return title

	def saveProject(self, path):
		import xml.dom.minidom
		from Tools.XMLTools import elementsWithTag, mergeText, stringToXML
		list = []
		list.append('<?xml version="1.0" encoding="utf-8" ?>\n')
		list.append('<DreamDVDBurnerProject>\n')
		list.append('\t<settings ')
		for key, val in self.settings.dict().iteritems():
			list.append( key + '="' + str(val.getValue()) + '" ' )
		list.append(' />\n')		
		list.append('\t<titles>\n')
		for title in self.titles:
			list.append('\t\t<path>')
			list.append(stringToXML(title.source.getPath()))
			list.append('</path>\n')
		list.append('\t</titles>\n')
		list.append('</DreamDVDBurnerProject>\n')

		name = self.settings.name.getValue()
		i = 0
		filename = path + name + ".ddvdp.xml"
		while fileExists(filename):
			i = i+1
			filename = path + name + str(i).zfill(3) + ".ddvdp.xml"
		try:	
			file = open(filename, "w")
			for x in list:
				file.write(x)
			file.close()
		except:
			return False
		return filename

	def loadProject(self, filename):
		import xml.dom.minidom
		try:
			if not fileExists(filename):
				self.error = "xml file not found!"
				raise AttributeError
			else:
				self.error = ""
			file = open(filename, "r")
			data = file.read().decode("utf-8").replace('&',"&amp;").encode("ascii",'xmlcharrefreplace')
			file.close()
			projectfiledom = xml.dom.minidom.parseString(data)
			for project in projectfiledom.childNodes[0].childNodes:
			  if project.nodeType == xml.dom.minidom.Element.nodeType:
			    if project.tagName == 'settings':
				i = 0
				if project.attributes.length < 11:
					self.error = "project attributes missing"
					raise AttributeError			
				while i < project.attributes.length:
					item = project.attributes.item(i)
					key = item.name.encode("utf-8")
					try:
						val = eval(item.nodeValue)
					except (NameError, SyntaxError):
						val = item.nodeValue.encode("utf-8")
					try:
						self.settings.dict()[key].setValue(val)
					except (KeyError):
						self.error = "unknown attribute '%s'" % (key)
						raise AttributeError
					i += 1
			for key in self.filekeys:
				val = self.settings.dict()[key].getValue()
				if not fileExists(val):
					self.error += "\n%s '%s' not found" % (key, val)
			if len(self.error):
				raise AttributeError
		except AttributeError:
			self.error += (" in project '%s'") % (filename)
			return False
		return True
