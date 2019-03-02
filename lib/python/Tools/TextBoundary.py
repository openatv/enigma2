from enigma import eLabel

# Calls onto the static function in eLabel. This avoids causing an invalidate
# on the parent container which is detrimental to UI performance, 
# particularly in a complex screen like the graph EPG
def getTextBoundarySize(instance, font, targetSize, text):
	return eLabel.calculateTextSize(font, text, targetSize)
