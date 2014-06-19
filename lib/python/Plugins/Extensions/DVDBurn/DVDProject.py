from Tools.Directories import fileExists
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigText, ConfigSelection, getConfigListEntry, ConfigSequence, ConfigSubList
import DVDTitle
import xml.dom.minidom
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_FONTS

class ConfigColor(ConfigSequence):
	def __init__(self, default = [128,128,128]):
		ConfigSequence.__init__(self, seperator = "#", limits = [(0,255),(0,255),(0,255)], default = default)

class ConfigFilename(ConfigText):
	def __init__(self):
		ConfigText.__init__(self, default = "", fixed_size = True, visible_width = False)

	def getMulti(self, selected):
		if self.text == "":
			return ("mtext"[1-selected:], "", 0)
		cut_len = min(len(self.text),40)
		filename = (self.text.rstrip("/").rsplit("/",1))[1].encode("utf-8")[:cut_len] + " "
		if self.allmarked:
			mark = range(0, len(filename))
		else:
			mark = [filename]
		return ("mtext"[1-selected:], filename, mark)

class DVDProject:
	MAX_SL = 4480
	MAX_DL = 8150
	def __init__(self):
		self.titles = [ ]
		self.target = None
		self.settings = ConfigSubsection()
		self.settings.name = ConfigText(fixed_size = False, visible_width = 40)
		self.settings.authormode = ConfigSelection(choices = [("menu_linked", _("Linked titles with a DVD menu")), ("just_linked", _("Direct playback of linked titles without menu")), ("menu_seperate", _("Separate titles with a main menu")), ("data_ts", _("special format data DVD (HDTV compatible)"))])
		self.settings.titlesetmode = ConfigSelection(choices = [("single", _("Simple titleset (compatibility for legacy players)")), ("multi", _("Complex (allows mixing audio tracks and aspects)"))], default="multi")
		self.settings.output = ConfigSelection(choices = [("iso", _("Create DVD-ISO")), ("dvd", _("Burn DVD"))])
		self.settings.isopath = ConfigText(fixed_size = False, visible_width = 40)
		self.settings.dataformat = ConfigSelection(choices = [("iso9660_1", ("ISO9660 Level 1")), ("iso9660_4", ("ISO9660 version 2")), ("udf", ("UDF"))])
		self.settings.menutemplate = ConfigFilename()
		self.settings.vmgm = ConfigFilename()
		self.filekeys = ["vmgm", "isopath", "menutemplate"]
		self.menutemplate = MenuTemplate()
		self.error = ""
		self.session = None

	def addService(self, service):
		title = DVDTitle.DVDTitle(self)
		title.addService(service)
		self.titles.append(title)
		return title

	def saveProject(self, path):
		from Tools.XMLTools import stringToXML
		list = []
		list.append('<?xml version="1.0" encoding="utf-8" ?>\n')
		list.append('<DreamDVDBurnerProject>\n')
		list.append('\t<settings ')
		for key, val in self.settings.dict().iteritems():
			list.append( key + '="' + str(val.getValue()) + '" ' )
		list.append('/>\n')
		list.append('\t<titles>\n')
		for title in self.titles:
			list.append('\t\t<title>\n')
			list.append('\t\t\t<path>')
			list.append(stringToXML(title.source.getPath()))
			list.append('</path>\n')
			list.append('\t\t\t<properties ')
			audiotracks = []
			for key, val in title.properties.dict().iteritems():
				if type(val) is ConfigSubList:
					audiotracks.append('\t\t\t<audiotracks>\n')
					for audiotrack in val:
						audiotracks.append('\t\t\t\t<audiotrack ')
						for subkey, subval in audiotrack.dict().iteritems():
							audiotracks.append( subkey + '="' + str(subval.getValue()) + '" ' )
						audiotracks.append(' />\n')
					audiotracks.append('\t\t\t</audiotracks>\n')
				else:
					list.append( key + '="' + str(val.getValue()) + '" ' )
			list.append('/>\n')
			for line in audiotracks:
				list.append(line)
			list.append('\t\t</title>\n')
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

	def load(self, filename):
		ret = self.loadProject(filename)
		if ret:
			ret = self.menutemplate.loadTemplate(self.settings.menutemplate.getValue())
			self.error += self.menutemplate.error
		return ret

	def loadProject(self, filename):
		#try:
			if not fileExists(filename):
				self.error = "xml file not found!"
				#raise AttributeError
			file = open(filename, "r")
			data = file.read().decode("utf-8").replace('&',"&amp;").encode("ascii",'xmlcharrefreplace')
			file.close()
			projectfiledom = xml.dom.minidom.parseString(data)
			for node in projectfiledom.childNodes[0].childNodes:
			  print "node:", node
			  if node.nodeType == xml.dom.minidom.Element.nodeType:
			    if node.tagName == 'settings':
				self.xmlAttributesToConfig(node, self.settings)
			    elif node.tagName == 'titles':
				self.xmlGetTitleNodeRecursive(node)

			for key in self.filekeys:
				val = self.settings.dict()[key].getValue()
				if not fileExists(val):
					if val[0] != "/":
						if key.find("font") == 0:
							val = resolveFilename(SCOPE_FONTS)+val
						else:
							val = resolveFilename(SCOPE_PLUGINS)+"Extensions/DVDBurn/"+val
						if fileExists(val):
							self.settings.dict()[key].setValue(val)
							continue
					self.error += "\n%s '%s' not found" % (key, val)
		#except AttributeError:
		  	#print "loadProject AttributeError", self.error
			#self.error += (" in project '%s'") % (filename)
			#return False
			return True

	def xmlAttributesToConfig(self, node, config):
		try:
			i = 0
			#if node.attributes.length < len(config.dict())-1:
				#self.error = "project attributes missing"
				#raise AttributeError
			while i < node.attributes.length:
				item = node.attributes.item(i)
				key = item.name.encode("utf-8")
				try:
					val = eval(item.nodeValue)
				except (NameError, SyntaxError):
					val = item.nodeValue.encode("utf-8")
				try:
					print "config[%s].setValue(%s)" % (key, val)
					config.dict()[key].setValue(val)
				except (KeyError):
					self.error = "unknown attribute '%s'" % (key)
					print "KeyError", self.error
					raise AttributeError
				i += 1
		except AttributeError:
			self.error += (" XML attribute error '%s'") % node.toxml()
			return False

	def xmlGetTitleNodeRecursive(self, node, title_idx = -1):
		print "[xmlGetTitleNodeRecursive]", title_idx, node
		print node.childNodes
		for subnode in node.childNodes:
		  print "xmlGetTitleNodeRecursive subnode:", subnode
		  if subnode.nodeType == xml.dom.minidom.Element.nodeType:
		    if subnode.tagName == 'title':
			title_idx += 1
			title = DVDTitle.DVDTitle(self)
			self.titles.append(title)
			self.xmlGetTitleNodeRecursive(subnode, title_idx)
		    if subnode.tagName == 'path':
			print "path:", subnode.firstChild.data
			filename = subnode.firstChild.data
			self.titles[title_idx].addFile(filename.encode("utf-8"))
		    if subnode.tagName == 'properties':
			self.xmlAttributesToConfig(node, self.titles[title_idx].properties)
		    if subnode.tagName == 'audiotracks':
			self.xmlGetTitleNodeRecursive(subnode, title_idx)
		    if subnode.tagName == 'audiotrack':
			print "audiotrack...", subnode.toxml()

	def getSize(self):
		totalsize = 0
		for title in self.titles:
			totalsize += title.estimatedDiskspace
		return totalsize

	size = property(getSize)

class MenuTemplate(DVDProject):
	def __init__(self):
		self.settings = ConfigSubsection()
		self.settings.titleformat = ConfigText(fixed_size = False, visible_width = 40)
		self.settings.subtitleformat = ConfigText(fixed_size = False, visible_width = 40)
		self.settings.menubg = ConfigFilename()
		self.settings.menuaudio = ConfigFilename()
		self.settings.dimensions = ConfigSequence(seperator = ',', default = [576,720], limits = [(352,720),(480,576)])
		self.settings.rows = ConfigInteger(default = 4, limits = (1, 10))
		self.settings.cols = ConfigInteger(default = 1, limits = (1, 4))
		self.settings.color_headline = ConfigColor()
		self.settings.color_headline = ConfigColor()
		self.settings.color_highlight = ConfigColor()
		self.settings.color_button = ConfigColor()
		self.settings.fontface_headline = ConfigFilename()
		self.settings.fontface_title = ConfigFilename()
		self.settings.fontface_subtitle = ConfigFilename()
		self.settings.fontsize_headline = ConfigInteger(default = 46, limits = (0, 199))
		self.settings.fontsize_title = ConfigInteger(default = 24, limits = (0, 199))
		self.settings.fontsize_subtitle = ConfigInteger(default = 14, limits = (0, 199))
		self.settings.margin_top = ConfigInteger(default = 120, limits = (0, 500))
		self.settings.margin_bottom = ConfigInteger(default = 40, limits = (0, 500))
		self.settings.margin_left = ConfigInteger(default = 56, limits = (0, 500))
		self.settings.margin_right = ConfigInteger(default = 56, limits = (0, 500))
		self.settings.space_rows = ConfigInteger(default = 32, limits = (0, 500))
		self.settings.space_cols = ConfigInteger(default = 24, limits = (0, 500))
		self.settings.prev_page_text = ConfigText(default = "<<<", fixed_size = False)
		self.settings.next_page_text = ConfigText(default = ">>>", fixed_size = False)
		self.settings.offset_headline = ConfigSequence(seperator = ',', default = [0,0], limits = [(-1,500),(-1,500)])
		self.settings.offset_title = ConfigSequence(seperator = ',', default = [0,0], limits = [(-1,500),(-1,500)])
		self.settings.offset_subtitle = ConfigSequence(seperator = ',', default = [20,0], limits = [(-1,500),(-1,500)])
		self.settings.offset_thumb = ConfigSequence(seperator = ',', default = [40,0], limits = [(-1,500),(-1,500)])
		self.settings.thumb_size = ConfigSequence(seperator = ',', default = [200,158], limits = [(0,576),(-1,720)])
		self.settings.thumb_border = ConfigInteger(default = 2, limits = (0, 20))
		self.filekeys = ["menubg", "menuaudio", "fontface_headline", "fontface_title", "fontface_subtitle"]
		from TitleProperties import languageChoices
		self.settings.menulang = ConfigSelection(choices = languageChoices.choices, default=languageChoices.choices[1][0])
		self.error = ""

	def loadTemplate(self, filename):
		ret = DVDProject.loadProject(self, filename)
		DVDProject.error = self.error
		return ret
