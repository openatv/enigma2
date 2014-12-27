from enigma import eLabel

def getTextBoundarySize(instance, font, targetSize, text):
	dummy = eLabel(instance)
	dummy.setFont(font)
	dummy.resize(targetSize)
	dummy.setText(text)
	return dummy.calculateSize()