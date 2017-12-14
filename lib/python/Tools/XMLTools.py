import re

def elementsWithTag(el, tag):
	"""filters all elements of childNode with the specified function
	example: nodes = elementsWithTag(childNodes, lambda x: x == "bla")"""

	import xml.dom.minidom
	# fiiixme! (works but isn't nice)
	if isinstance(tag, str):
		s = tag
		tag = lambda x: x == s

	for x in el:
		if x.nodeType != xml.dom.minidom.Element.nodeType:
			continue
		if tag(x.tagName):
			yield x

def mergeText(nodelist):
	rc = ""
	for node in nodelist:
		if node.nodeType == node.TEXT_NODE:
			rc = rc + node.data
	return rc

def stringToXML(text):
	illegal_xml_chars_RE = re.compile(u'[\x00-\x08\x0b\x0c\x0e-\x1F\uD800-\uDFFF\uFFFE\uFFFF]')
	text = illegal_xml_chars_RE.sub('', text)
	return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace("'", '&apos;').replace('"', '&quot;')
