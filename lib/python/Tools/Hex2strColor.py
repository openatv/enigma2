# Converts hex colors to formatted strings,
# suitable for embedding in python code.


def Hex2strColor(rgb):
	return "\c%08x" % rgb
