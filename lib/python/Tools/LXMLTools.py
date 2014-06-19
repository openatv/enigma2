
def elementsWithTag(el, tag):

	"""filters all elements of childNode with the specified function
	example: nodes = elementsWithTag(childNodes, lambda x: x == "bla")"""

	# fiiixme! (works but isn't nice)
	if isinstance(tag, str):
		s = tag
		tag = lambda x: x == s

	for x in el:
		if not x.tag:
			continue
		if tag(x.tag):
			yield x

def mergeText(nodelist):
	rc = ""
	for node in nodelist:
		if node.text:
			rc = rc + node.text
	return rc

def stringToXML(text):
	return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace("'", '&apos;').replace('"', '&quot;')
