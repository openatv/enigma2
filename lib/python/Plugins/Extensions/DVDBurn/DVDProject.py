from Tools.Directories import resolveFilename, fileExists, SCOPE_FONTS, SCOPE_PLUGINS, SCOPE_SKIN
class DVDProject:
	def __init__(self):
		self.titles = [ ]
		self.target = None
		self.name = _("Dreambox DVD record")
		self.vmgm = resolveFilename(SCOPE_PLUGINS,"Extensions/DVDBurn/dreamvmgm.mpg")
		self.menuaudio = resolveFilename(SCOPE_PLUGINS,"Extensions/DVDBurn/silence.mp2")
		self.menubg = resolveFilename(SCOPE_SKIN, "dreamdvd_02.jpg")
		# tuples with R, G, B values
		self.color_button	= ( 0x08, 0x00, 0x00 )
		self.color_highlight	= ( 0x00, 0xC0, 0xC0 )
		self.color_headline	= ( 0x00, 0x00, 0x80 )
		self.font_face = resolveFilename(SCOPE_FONTS, "nmsbd.ttf")
		# tuple with three pixel values ( headline, title, subtitle )
		self.font_size = ( 48, 28, 16 )
		# please supply even numbers for all dimensions
		self.space_left = 30
		self.space_top = 120
		self.space_rows = 36

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
		list.append('\t<config')
		list.append(' name="' + self.name + '"')
		list.append(' vmgm="' + self.vmgm + '"')
		list.append(' />\n')
		list.append('\t<menu')
		list.append(' bg="' + self.menubg + '"')
		list.append(' audio="' + self.menuaudio + '"')
		list.append(' color_button="' + str(self.color_button) + '"')
		list.append(' color_highlight="' + str(self.color_highlight) + '"')
		list.append(' color_headline="' + str(self.color_headline) + '"')
		list.append(' font_face="' + self.font_face + '"')
		list.append(' font_size="' + str(self.font_size) + '"')
		list.append(' space_left="' + str(self.space_left) + '"')
		list.append(' space_top="' + str(self.space_top) + '"')
		list.append(' space_rows="' + str(self.space_rows) + '"')
		list.append(' />\n')
		list.append('\t<titles>\n')
		for title in self.titles:
			list.append('\t\t<path>')
			list.append(stringToXML(title.source.getPath()))
			list.append('</path>\n')
		list.append('\t</titles>\n')
		list.append('</DreamDVDBurnerProject>\n')

		i = 0
		filename = path + "/" + self.name + ".ddvdp.xml"
		while fileExists(filename):
			i = i+1
			filename = path + "/" + self.name + str(i).zfill(3) + ".ddvdp.xml"
				
		file = open(filename, "w")
		for x in list:
			file.write(x)
		file.close()