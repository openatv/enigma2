from Tools.Directories import fileExists

class DVDProject:
	def __init__(self):
		self.titles = [ ]
		self.target = None

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
		list.append('\t<project')
		list.append(' name="' + self.name + '"')
		list.append(' vmgm="' + self.vmgm + '"')
		list.append(' />\n')
		list.append('\t<menu')
		list.append('\tuse="' + str(self.menu) + '"\n')
		list.append('\tbg="' + self.menubg + '"\n')
		list.append('\t\taudio="' + self.menuaudio + '"\n')
		list.append('\t\tcolor_button="' + str(self.color_button) + '"\n')
		list.append('\t\tcolor_highlight="' + str(self.color_highlight) + '"\n')
		list.append('\t\tcolor_headline="' + str(self.color_headline) + '"\n')
		list.append('\t\tfont_face="' + self.font_face + '"\n')
		list.append('\t\tfont_size="' + str(self.font_size) + '"\n')
		list.append('\t\tspace_left="' + str(self.space_left) + '"\n')
		list.append('\t\tspace_top="' + str(self.space_top) + '"\n')
		list.append('\t\tspace_rows="' + str(self.space_rows) + '"')
		list.append(' />\n')
		list.append('\t<titles')
		list.append(' link="' + str(self.linktitles) + '"')
		list.append(' />\n')
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

	def loadProject(self, filename):
		import xml.dom.minidom
		print "[loadProject]", filename
		try:
		  if not fileExists(filename):
			self.error = "file not found!"
			raise AttributeError
		  else:
			self.error = ""
		  file = open(filename, "r")
		  data = file.read().decode("utf-8").replace('&',"&amp;").encode("ascii",'xmlcharrefreplace')
		  file.close()
		  projectfiledom = xml.dom.minidom.parseString(data)
		  for project in projectfiledom.childNodes[0].childNodes:
		    if project.nodeType == xml.dom.minidom.Element.nodeType:
		      if project.tagName == 'project':
			self.name = project.getAttribute("name").encode("utf-8")
			self.vmgm = project.getAttribute("vmgm").encode("utf-8")
		      if project.tagName == 'menu':
			self.menu = eval(project.getAttribute("use"))
			self.menubg = project.getAttribute("bg").encode("utf-8")
			self.menuaudio = project.getAttribute("audio").encode("utf-8")	
			# tuples with R, G, B values
			self.color_button = eval(project.getAttribute("color_button"))
			self.color_highlight = eval(project.getAttribute("color_highlight"))
			self.color_headline = eval(project.getAttribute("color_headline"))
			self.font_face = project.getAttribute("font_face").encode("utf-8")
			# tuple with three pixel sizes ( headline, title, subtitle )
			self.font_size = eval(project.getAttribute("font_size"))
			# please supply even numbers for all dimensions
			self.space_left = int(project.getAttribute("space_left"))
			self.space_top = int(project.getAttribute("space_top"))
			self.space_rows = int(project.getAttribute("space_rows"))
		      if project.tagName == 'titles':
			self.linktitles = eval(project.getAttribute("link"))
		  if not fileExists(self.vmgm):
			self.error += "\nvmgm '%s' not found" % self.vmgm
		  if not fileExists(self.menubg):
			self.error += "\nmenu background '%s' not found" % self.menubg
		  if not fileExists(self.menuaudio):
			self.error += "\nmenu audio '%s' not found" % self.menuaudio
		  if not fileExists(self.font_face):
			self.error += "\nmenu font '%s' not found" % self.font_face
		  print "len(self.error):", len(self.error)
		  if len(self.error):
		  	raise AttributeError
		except:
			print "len(self.error):, error", len(self.error), len(self.error)
			self.error = ("error parsing project xml file '%s'" % filename) + self.error
			return False
		return True
