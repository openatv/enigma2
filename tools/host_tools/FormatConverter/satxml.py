import os
from datasource import datasource
from xml.dom import minidom
from xml.dom.minidom import Document
from input import inputText


class satxml(datasource):
	def __init__(self, filename="satellites.xml"):
		self.filename = filename
		datasource.__init__(self)

		if not os.path.isfile(filename):
			print "File %s doesn't exist. Creating it." % filename

	def getStatus(self):
		text = datasource.getStatus(self)
		return text

	def getCapabilities(self):
		return [("set filename", self.setFilename), ("read file", self.read), ("write file", self.write), ("print all", self.printAll)]

	def getName(self):
		return "satellites.xml"

	def setFilename(self):
		print "Please give a filename <satellites.xml>:"
		filename = inputText()
		if filename == "":
			self.filename = "satellites.xml"
		else:
			self.filename = filename
		print "Filename set to %s" % self.filename

	def read(self):
		basicsatxml = minidom.parse(self.filename)

		for sat in basicsatxml.firstChild.childNodes:
			if sat.nodeType == sat.ELEMENT_NODE and sat.localName == "sat":
				print sat.localName
				satname = str(sat.getAttribute("name"))
				satpos = str(sat.getAttribute("position"))
				self.addSat(satname, satpos)
				for transponder in sat.childNodes:
					if transponder.nodeType == transponder.ELEMENT_NODE and transponder.localName == "transponder":
						parameters = {}
						paramlist = ["frequency", "symbol_rate", "polarization", "fec", "system", "modulation", "tsid", "onid"]
						for param in paramlist:
							entry = str(transponder.getAttribute(param))
							if entry != "":
								parameters[param] = entry
						if len(parameters.keys()) > 1:
							self.addTransponder(satpos, parameters)
		print self.transponderlist

	def write(self):
		satxml = Document()
		satellites = satxml.createElement("satellites")
		satxml.appendChild(satellites)
		satlist = self.transponderlist.keys()
		print self.transponderlist
		satlist.sort()

		for sat in satlist:
			xmlsat = satxml.createElement("sat")
			xmlsat.setAttribute("name", self.satnames[sat])
			xmlsat.setAttribute("flags", "1")
			xmlsat.setAttribute("position", sat)
			satellites.appendChild(xmlsat)
			transponders = self.transponderlist[sat]
			transponders.sort(key=lambda a: a["frequency"])

			for transponder in transponders:
				xmltransponder = satxml.createElement("transponder")
				paramlist = ["frequency", "symbol_rate", "polarization", "fec", "system", "modulation", "tsid", "onid"]
				for param in paramlist:
					if param in transponder:
						xmltransponder.setAttribute(param, transponder[param])
				xmlsat.appendChild(xmltransponder)
		prettyxml = satxml.toprettyxml()
		print prettyxml
		file = open(self.filename, "w")
		file.write(prettyxml)
		file.close()
