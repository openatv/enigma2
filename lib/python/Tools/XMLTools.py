import xml.dom.minidom

def elementsWithTag(el, tag):

	"""filters all elements of childNode with the specified function
	example: nodes = elementsWithTag(childNodes, lambda x: x == "bla")"""

	# fiiixme! (works but isn't nice)
	if isinstance(tag, str):
		s = tag
		tag = lambda x: x == s
		
	for x in el:
		if x.nodeType != xml.dom.minidom.Element.nodeType:
			continue
		if tag(x.tagName):
			yield x
