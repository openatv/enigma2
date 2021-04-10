# usage: genmetaindex.py <xml-files>  > index.xml
import sys
import os
from xml.etree.ElementTree import ElementTree, Element

root = Element("index")

for file in sys.argv[1:]:
	p = ElementTree()
	p.parse(file)

	package = Element("package")
	package.set("details", os.path.basename(file))

	# we need all prerequisites
	package.append(p.find("prerequisites"))

	info = None
	# we need some of the info, but not all
	for i in p.findall("info"):
		if not info:
			info = i
	assert info

	for i in info[:]:
		if i.tag not in ["name", "packagename", "packagetype", "shortdescription"]:
			info.remove(i)

	for i in info[:]:
		package.set(i.tag, i.text)

	root.append(package)

def indent(elem, level=0):
	i = "\n" + level*"\t"
	if len(elem):
		if not elem.text or not elem.text.strip():
			elem.text = i + "\t"
		if not elem.tail or not elem.tail.strip():
			elem.tail = i
		for elem in elem:
			indent(elem, level+1)
		if not elem.tail or not elem.tail.strip():
			elem.tail = i
	else:
		if level and (not elem.tail or not elem.tail.strip()):
			elem.tail = i

indent(root)

ElementTree(root).write(sys.stdout)
